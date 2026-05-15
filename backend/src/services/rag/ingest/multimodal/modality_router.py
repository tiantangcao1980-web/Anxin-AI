"""模态路由分流（P13-A）。

把 :class:`ParsedSegment` 列表按 ``modality`` 分流到不同的下游处理器：

- ``text`` → 现有 ``chunking_service`` 切块（本模块只做归类，不调用切块器）。
- ``image`` → P13-C VLM 描述生成（先归类，后由 query 侧异步处理）。
- ``table`` → :class:`TableExtractor` 校正 + markdown 回写。
- ``formula`` → :class:`FormulaRecognizer` 清洗 LaTeX。
- ``seal`` → :class:`SealDetector` 二次确认 + 元数据补全。

设计准则
========

路由器保持"无副作用 + 同步"语义：返回值是一个 ``dict[modality, list[seg]]``，
**不**就地修改输入 segment（避免与下游 KG 模块争用所有权）。

下游 KG / VLM Query 的衔接点
============================

- KG 节点候选 = ``segments``（每条 1 个节点），关系候选 = 同 ``parent_section``
  的 segment 之间。
- VLM Query 的 retrieve 关键字 = ``segments`` 的 ``content`` (text) 或
  ``metadata.parent_section``。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.services.rag.ingest.multimodal.base import Modality, ParsedSegment


@dataclass
class RouteBucket:
    """单个模态桶。"""

    modality: str
    segments: list[ParsedSegment] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def count(self) -> int:
        return len(self.segments)


class ModalityRouter:
    """按 modality 分流 segment。"""

    KNOWN_MODALITIES = frozenset(m.value for m in Modality)

    def route(self, segments: list[ParsedSegment]) -> dict[str, RouteBucket]:
        """分流。返回 ``{modality_name: RouteBucket}``，含未知模态桶。"""
        buckets: dict[str, RouteBucket] = {}
        for seg in segments:
            modality = seg.modality
            if modality not in self.KNOWN_MODALITIES:
                bucket = buckets.setdefault(
                    "unknown",
                    RouteBucket(modality="unknown", metadata={"strict": False}),
                )
            else:
                bucket = buckets.setdefault(modality, RouteBucket(modality=modality))
            bucket.segments.append(seg)
        return buckets

    def filter(
        self, segments: list[ParsedSegment], *, modalities: list[str]
    ) -> list[ParsedSegment]:
        """只保留指定 modality 的 segment（保序）。"""
        wanted = set(modalities)
        return [s for s in segments if s.modality in wanted]

    def stats(self, segments: list[ParsedSegment]) -> dict[str, int]:
        """统计各 modality segment 数。"""
        out: dict[str, int] = {}
        for seg in segments:
            out[seg.modality] = out.get(seg.modality, 0) + 1
        return out
