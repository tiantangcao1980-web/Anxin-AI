# -*- coding: utf-8 -*-
"""
实体抽取器

两条路径：
1. **LLM 抽取**（``mode="llm"``）：调用注入的 ``llm_client`` 异步函数 ``llm_call(prompt) -> str``，
   解析 JSON 数组。Prompt 是法律领域专用的。
2. **关键词/正则 fallback**（``mode="mock"`` 或 LLM 不可用时）：使用 ``ontology`` 中的
   关键词与正则集合做轻量抽取，保证测试与离线场景可跑。

LLM 客户端解耦：调用方注入 ``llm_call`` callable（``async (prompt: str) -> str``），
KG 模块本身不直接依赖 :class:`LLMService`，避免循环引用 + 方便 mock。
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Awaitable, Callable, Iterable

from loguru import logger

from src.services.rag.kg.base import (
    Entity,
    EntityType,
    Modality,
    Segment,
    SegmentLikeProtocol,
)
from src.services.rag.kg.ontology import (
    AMOUNT_PATTERNS,
    ARTICLE_REGEX,
    DATE_PATTERNS,
    LEGAL_OBLIGATION_KEYWORDS,
    LEGAL_PARTY_KEYWORDS,
    LEGAL_REGULATION_PATTERNS,
    LEGAL_RIGHT_KEYWORDS,
    MODALITY_DEFAULT_TYPE,
    classify_entity,
)


LLMCall = Callable[[str], Awaitable[str]]


PROMPT_TEMPLATE = """你是法律文档实体抽取专家。请从下面的合同/法规文本中抽取实体，按 JSON 数组返回。

每个实体格式：
{{
  "name": "实体名（保持原文写法）",
  "type": "实体类型（必须是下列之一：legal_party/legal_term/obligation/right/regulation/amount/date/seal/signature/table_data/generic）",
  "aliases": ["别名1", "别名2"],
  "confidence": 0.0-1.0
}}

类型说明：
- legal_party: 合同当事人（甲方/乙方/公司名）
- legal_term: 法律术语（违约/解除/不可抗力）
- obligation: 义务条款（应当/必须/承担）
- right: 权利条款（有权/享有/可以）
- regulation: 法规引用（《民法典》第X条）
- amount: 金额（含币种）
- date: 日期
- generic: 兜底

只输出 JSON 数组，不要多余文字。

文本：
{text}
"""


class EntityExtractor:
    """LLM-first + 关键词 fallback 的实体抽取器。"""

    def __init__(
        self,
        llm_call: LLMCall | None = None,
        *,
        mode: str = "auto",  # "llm" / "mock" / "auto"
        max_chars_per_call: int = 4000,
    ) -> None:
        self.llm_call = llm_call
        self.mode = mode
        self.max_chars_per_call = max_chars_per_call

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def extract(
        self,
        segments: Iterable[SegmentLikeProtocol],
    ) -> list[Entity]:
        """从一组 segments 中抽取实体（去重合并）。"""
        entities: dict[str, Entity] = {}

        for raw_seg in segments:
            seg = Segment.from_protocol(raw_seg)

            # 非文本模态走快速通道（直接基于 modality 生成 SEAL/SIGNATURE/TABLE_DATA 等节点）
            if seg.modality and seg.modality != Modality.TEXT.value:
                ent = self._segment_as_entity(seg)
                if ent:
                    self._upsert(entities, ent)
                # 同时尝试在 content 上跑文本抽取（很多多模态切片自带 OCR 文本）
                if not seg.content:
                    continue

            # 文本抽取
            extracted: list[Entity]
            if self._should_use_llm():
                try:
                    extracted = await self._extract_via_llm(seg)
                except Exception as exc:  # pragma: no cover - 网络错误降级路径
                    logger.warning(f"LLM 抽取失败，降级到关键词模式：{exc}")
                    extracted = self._extract_via_keywords(seg)
            else:
                extracted = self._extract_via_keywords(seg)

            for ent in extracted:
                self._upsert(entities, ent)

        return list(entities.values())

    # ------------------------------------------------------------------
    # LLM 路径
    # ------------------------------------------------------------------

    def _should_use_llm(self) -> bool:
        if self.mode == "mock":
            return False
        if self.mode == "llm":
            return True
        # auto：仅当注入了 llm_call 时启用
        return self.llm_call is not None

    async def _extract_via_llm(self, seg: Segment) -> list[Entity]:
        if self.llm_call is None:
            return []

        text = (seg.content or "")[: self.max_chars_per_call]
        if not text.strip():
            return []

        prompt = PROMPT_TEMPLATE.format(text=text)
        raw = await self.llm_call(prompt)

        return self._parse_llm_json(raw, seg)

    @staticmethod
    def _parse_llm_json(raw: str, seg: Segment) -> list[Entity]:
        """解析 LLM 返回的 JSON 数组，宽容 markdown 代码块。"""
        if not raw:
            return []
        # 去掉 ```json ... ``` fence
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # 兜底：尝试截取首个 JSON 数组
            match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if not match:
                logger.warning("LLM 输出无法解析为 JSON")
                return []
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []

        if not isinstance(data, list):
            return []

        entities: list[Entity] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = (item.get("name") or "").strip()
            if not name:
                continue
            type_str = (item.get("type") or "generic").strip().lower()
            try:
                etype = EntityType(type_str)
            except ValueError:
                etype = EntityType.GENERIC
            aliases = item.get("aliases") or []
            if not isinstance(aliases, list):
                aliases = []
            confidence = float(item.get("confidence") or 0.8)

            offset = (seg.content or "").find(name)
            entities.append(
                Entity(
                    entity_id=_make_entity_id(name, etype),
                    type=etype,
                    name=name,
                    aliases=[str(a) for a in aliases if a],
                    mentions=[
                        {
                            "segment_id": seg.segment_id,
                            "char_offset": offset if offset >= 0 else 0,
                            "modality": seg.modality,
                        }
                    ],
                    properties={"source": "llm"},
                    confidence=max(0.0, min(1.0, confidence)),
                )
            )
        return entities

    # ------------------------------------------------------------------
    # 关键词 fallback
    # ------------------------------------------------------------------

    def _extract_via_keywords(self, seg: Segment) -> list[Entity]:
        text = seg.content or ""
        if not text:
            return []

        found: list[Entity] = []

        # 1. 当事人
        for kw in LEGAL_PARTY_KEYWORDS:
            for m in re.finditer(re.escape(kw), text):
                found.append(
                    self._make_entity(
                        kw,
                        EntityType.LEGAL_PARTY,
                        seg,
                        offset=m.start(),
                        confidence=0.9,
                    )
                )

        # 2. 法规引用（《XX法》）
        for pat in LEGAL_REGULATION_PATTERNS:
            for m in pat.finditer(text):
                found.append(
                    self._make_entity(
                        m.group(0),
                        EntityType.REGULATION,
                        seg,
                        offset=m.start(),
                        confidence=0.95,
                    )
                )

        # 3. 第 N 条 / 第 N 章
        for m in ARTICLE_REGEX.finditer(text):
            found.append(
                self._make_entity(
                    m.group(0),
                    EntityType.REGULATION,
                    seg,
                    offset=m.start(),
                    confidence=0.85,
                )
            )

        # 4. 金额
        for pat in AMOUNT_PATTERNS:
            for m in pat.finditer(text):
                found.append(
                    self._make_entity(
                        m.group(0),
                        EntityType.AMOUNT,
                        seg,
                        offset=m.start(),
                        confidence=0.9,
                    )
                )

        # 5. 日期
        for pat in DATE_PATTERNS:
            for m in pat.finditer(text):
                found.append(
                    self._make_entity(
                        m.group(0),
                        EntityType.DATE,
                        seg,
                        offset=m.start(),
                        confidence=0.9,
                    )
                )

        # 6. 义务/权利触发词（取所在的小句）
        for kw in LEGAL_OBLIGATION_KEYWORDS:
            for m in re.finditer(re.escape(kw), text):
                clause = _extract_clause(text, m.start(), m.end())
                if clause:
                    found.append(
                        self._make_entity(
                            clause,
                            EntityType.OBLIGATION,
                            seg,
                            offset=m.start(),
                            confidence=0.7,
                        )
                    )

        for kw in LEGAL_RIGHT_KEYWORDS:
            for m in re.finditer(re.escape(kw), text):
                clause = _extract_clause(text, m.start(), m.end())
                if clause:
                    found.append(
                        self._make_entity(
                            clause,
                            EntityType.RIGHT,
                            seg,
                            offset=m.start(),
                            confidence=0.7,
                        )
                    )

        return found

    # ------------------------------------------------------------------
    # 辅助
    # ------------------------------------------------------------------

    def _make_entity(
        self,
        name: str,
        etype: EntityType,
        seg: Segment,
        *,
        offset: int = 0,
        confidence: float = 0.8,
    ) -> Entity:
        return Entity(
            entity_id=_make_entity_id(name, etype),
            type=etype,
            name=name,
            aliases=[],
            mentions=[
                {
                    "segment_id": seg.segment_id,
                    "char_offset": offset,
                    "modality": seg.modality,
                }
            ],
            properties={"source": "keyword"},
            confidence=confidence,
        )

    def _segment_as_entity(self, seg: Segment) -> Entity | None:
        """对 image / table / seal / signature 段直接产出占位实体。"""
        etype = MODALITY_DEFAULT_TYPE.get(seg.modality)
        if etype is None:
            return None
        # 对图章/签字优先使用 metadata['party'] 名（如果 P13-A 已识别），否则用 segment_id
        name = (
            seg.metadata.get("name")
            or seg.metadata.get("party")
            or seg.metadata.get("caption")
            or f"{seg.modality}:{seg.segment_id}"
        )
        ent = Entity(
            entity_id=_make_entity_id(name, etype),
            type=etype,
            name=str(name),
            aliases=[],
            mentions=[
                {
                    "segment_id": seg.segment_id,
                    "char_offset": 0,
                    "modality": seg.modality,
                }
            ],
            properties={
                "source": "modality",
                "modality": seg.modality,
                **{k: v for k, v in seg.metadata.items() if k != "name"},
            },
            confidence=0.95,
        )
        # 进一步用 ontology 校正——例如 OCR 出"中华人民共和国民法典"应归 REGULATION
        if seg.modality == Modality.TEXT.value:
            ent.type = classify_entity(ent.name, seg.modality)
        return ent

    @staticmethod
    def _upsert(bucket: dict[str, Entity], ent: Entity) -> None:
        existing = bucket.get(ent.entity_id)
        if existing is None:
            bucket[ent.entity_id] = ent
        else:
            existing.merge(ent)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------


def _make_entity_id(name: str, etype: EntityType) -> str:
    """稳定 entity_id：md5(name + type) 取前 16 位。"""
    digest = hashlib.md5(f"{etype.value}::{name}".encode("utf-8")).hexdigest()
    return f"ent_{digest[:16]}"


def _extract_clause(text: str, start: int, end: int, window: int = 30) -> str:
    """以触发词为中心截取一个小句（句号/分号/换行为边界）。"""
    left = max(0, start - window)
    right = min(len(text), end + window)
    snippet = text[left:right]
    # 截到最近的句末
    for sep in ["。", "；", "\n", ";"]:
        idx = snippet.rfind(sep, 0, start - left)
        if idx >= 0:
            snippet = snippet[idx + 1 :]
            break
    for sep in ["。", "；", "\n", ";"]:
        idx = snippet.find(sep)
        if idx >= 0:
            snippet = snippet[: idx + 1]
            break
    return snippet.strip()


__all__ = ["EntityExtractor", "LLMCall"]
