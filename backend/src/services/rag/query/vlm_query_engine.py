"""VLM 增强查询引擎。

把 :class:`MultimodalRetriever` 的命中段附带的图（image / seal）
转 base64 后，与文本上下文一起喂给 VLM（GPT-4o vision / 通义 VL / Hunyuan-VL 等），
解析返回 → 拼装 :class:`VLMQueryResponse`。

关键策略：

- 模型不支持 vision → 自动降级纯文本
- ``enable_vlm=False`` → 同样降级
- VLM 返回中 ``mentioned_segment_ids`` 用来标记 *visual_grounding*
- 兜底：如果 VLM 失败，抛错由路由层兜底为纯文本
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from typing import Any

from loguru import logger

from src.services.rag.query.base import (
    Modality,
    MultimodalQueryRequest,
    RetrievedSegment,
    VLMClient,
    VLMQueryResponse,
)
from src.services.rag.query.citation_aggregator import CitationAggregator
from src.services.rag.query.multimodal_retriever import MultimodalRetriever

# 默认系统提示
DEFAULT_VLM_SYSTEM_PROMPT = """你是一位严谨的法律 / 财税 / 合同领域多模态助手。
你将收到：
- 用户问题
- 文本上下文（可能包含合同条款、财务表格、法条等）
- 一组附图（每张图标注了 segment_id 与模态：image=照片、seal=公章、table=表格截图）

回答规则：
1. 严格基于「文本上下文」与「附图」作答；缺乏依据时直白说明"资料不足"。
2. 如果答案用到某张图，必须用 `[seg:<segment_id>]` 引用它。
3. 如果引用文本，使用 `[doc:<document_id>#<segment_id>]` 标注出处。
4. 公章 / 印鉴只允许识别"是否盖章 / 大致内容 / 是否清晰"，不做真伪鉴定结论。
5. 输出为简体中文，结构化、给出依据 + 结论。
"""


@dataclass
class VLMQueryEngine:
    """端到端：检索 → VLM 联合作答 → 引文聚合。"""

    retriever: MultimodalRetriever
    vlm_client: VLMClient | None
    citation_aggregator: CitationAggregator | None = None

    # 喂给 VLM 的图数量上限（控成本）
    max_images: int = 4
    # 单图字节上限（超过则跳过该图，避免 token 爆炸）
    max_image_bytes: int = 4 * 1024 * 1024  # 4 MB
    system_prompt: str = DEFAULT_VLM_SYSTEM_PROMPT

    def __post_init__(self) -> None:
        if self.citation_aggregator is None:
            self.citation_aggregator = CitationAggregator()

    # ---- 主入口 ----

    async def query(
        self,
        request: MultimodalQueryRequest,
    ) -> VLMQueryResponse:
        """执行完整 VLM 增强 query。

        失败时返回 ``VLMQueryResponse(answer=<降级文本>, vlm_used=False, ...)``。
        """
        t0 = time.perf_counter()
        segments = await self.retriever.retrieve(request)

        if not segments:
            return VLMQueryResponse(
                answer="未在知识库中检索到与该问题相关的内容，建议补充关键词或上传相关文档。",
                citations=[],
                visual_grounding=[],
                confidence=0.0,
                duration_ms=int((time.perf_counter() - t0) * 1000),
                vlm_used=False,
            )

        # 是否走 VLM
        use_vlm = (
            request.enable_vlm
            and self.vlm_client is not None
            and bool(getattr(self.vlm_client, "supports_vision", False))
            and any(s.is_visual() for s in segments)
        )

        if use_vlm:
            try:
                response = await self._run_vlm(request, segments)
                response.duration_ms = int((time.perf_counter() - t0) * 1000)
                return response
            except Exception as exc:
                logger.exception("VLM 调用失败，降级纯文本: {}", exc)

        # 纯文本降级
        response = self._run_text_only(request, segments)
        response.duration_ms = int((time.perf_counter() - t0) * 1000)
        return response

    # ---- VLM 路径 ----

    async def _run_vlm(
        self,
        request: MultimodalQueryRequest,
        segments: list[RetrievedSegment],
    ) -> VLMQueryResponse:
        text_segments = [s for s in segments if not s.is_visual()]
        visual_segments = [s for s in segments if s.is_visual()][: self.max_images]

        text_context = self._format_text_context(text_segments)
        images = self._build_image_payload(visual_segments)

        logger.debug(
            "VLMQueryEngine: vlm call text_segs={} imgs={}",
            len(text_segments),
            len(images),
        )

        result: dict[str, Any] = await self.vlm_client.chat_with_vision(  # type: ignore[union-attr]
            system_prompt=self.system_prompt,
            user_text=self._format_user_prompt(request.query, text_context),
            images=images,
            language=request.language,
        )

        answer = str(result.get("answer", "")).strip()
        mentioned_ids: list[str] = list(result.get("mentioned_segment_ids", []) or [])
        vlm_confidence = float(result.get("confidence", 0.0) or 0.0)
        tokens = int(result.get("tokens", 0) or 0)

        # visual_grounding: VLM 真的引用到的图
        seg_index = {s.segment_id: s for s in visual_segments}
        visual_grounding = [
            {
                "segment_id": sid,
                "modality": seg_index[sid].modality.value if sid in seg_index else None,
                "document_id": seg_index[sid].document_id if sid in seg_index else None,
                "page": seg_index[sid].page if sid in seg_index else None,
            }
            for sid in mentioned_ids
            if sid in seg_index
        ]

        citations = (
            self.citation_aggregator.aggregate(segments) if self.citation_aggregator else []
        )

        # 综合置信度：retrieval 平均得分 * 0.5 + VLM 自报 * 0.5
        retrieval_avg = (
            sum(s.score for s in segments) / max(len(segments), 1) if segments else 0.0
        )
        confidence = round(min(1.0, max(0.0, retrieval_avg * 0.5 + vlm_confidence * 0.5)), 4)

        return VLMQueryResponse(
            answer=answer,
            citations=citations,
            visual_grounding=visual_grounding,
            confidence=confidence,
            duration_ms=0,  # 由调用方填
            vlm_used=True,
            debug={"tokens": tokens, "image_count": len(images)},
        )

    # ---- 文本降级路径 ----

    def _run_text_only(
        self,
        request: MultimodalQueryRequest,
        segments: list[RetrievedSegment],
    ) -> VLMQueryResponse:
        text_segments = [s for s in segments if not s.is_visual()]
        if not text_segments:
            text_segments = segments  # 实在没有就把所有 segment 当文本（content 是字符串时）

        # 简单拼接作为降级回答；上层若有 LLM 文本生成可替换
        snippet = self._format_text_context(text_segments[:3], max_chars_per_seg=200)
        answer = (
            "（VLM 未启用 / 未命中视觉模态，已降级纯文本检索）\n\n"
            f"基于检索到的内容：\n{snippet}\n\n"
            "如需结合附图分析，请开启 enable_vlm=true 并选择支持 vision 的模型。"
        )
        citations = (
            self.citation_aggregator.aggregate(segments) if self.citation_aggregator else []
        )
        retrieval_avg = (
            sum(s.score for s in segments) / max(len(segments), 1) if segments else 0.0
        )
        confidence = round(min(1.0, max(0.0, retrieval_avg)), 4)
        return VLMQueryResponse(
            answer=answer,
            citations=citations,
            visual_grounding=[],
            confidence=confidence,
            duration_ms=0,
            vlm_used=False,
            debug={"image_count": 0, "fallback": True},
        )

    # ---- helpers ----

    @staticmethod
    def _format_text_context(
        segments: list[RetrievedSegment],
        max_chars_per_seg: int = 400,
    ) -> str:
        """把 text segments 拼成 LLM 上下文。"""
        parts: list[str] = []
        for seg in segments:
            content = seg.content if isinstance(seg.content, str) else "[非文本内容]"
            if len(content) > max_chars_per_seg:
                content = content[:max_chars_per_seg] + "…"
            parts.append(
                f"[doc:{seg.document_id}#{seg.segment_id} modality={seg.modality.value}]"
                f"\n{content}"
            )
        return "\n\n".join(parts)

    @staticmethod
    def _format_user_prompt(query: str, text_context: str) -> str:
        return (
            f"用户问题：{query}\n\n"
            f"=== 文本上下文 ===\n{text_context if text_context else '（无文本上下文）'}\n\n"
            "请基于以上文本与附图作答。"
        )

    def _build_image_payload(
        self,
        visual_segments: list[RetrievedSegment],
    ) -> list[dict[str, Any]]:
        """把 image / seal segment 转成 ``{segment_id, base64, modality, hint}``。"""
        payload: list[dict[str, Any]] = []
        for seg in visual_segments:
            raw = seg.content
            if isinstance(raw, bytes):
                if len(raw) > self.max_image_bytes:
                    logger.warning(
                        "图片 {} 超过 {} bytes，已跳过",
                        seg.segment_id,
                        self.max_image_bytes,
                    )
                    continue
                b64 = base64.b64encode(raw).decode("ascii")
                payload.append(
                    {
                        "segment_id": seg.segment_id,
                        "base64": b64,
                        "modality": seg.modality.value,
                        "hint": "公章" if seg.modality == Modality.SEAL else "图像",
                    }
                )
            elif isinstance(raw, str) and (raw.startswith("http://") or raw.startswith("https://")):
                # 远程 URL：交给 VLMClient 自己取（不在这里下载）
                payload.append(
                    {
                        "segment_id": seg.segment_id,
                        "url": raw,
                        "modality": seg.modality.value,
                        "hint": "公章" if seg.modality == Modality.SEAL else "图像",
                    }
                )
            else:
                logger.debug(
                    "segment {} 视觉但 content 既非 bytes 也非 URL，跳过",
                    seg.segment_id,
                )
        return payload
