"""多模态检索器。

流程（参考 RAG-Anything 的 Multimodal Retrieval）：

1. **向量 + BM25 混合检索**（消费 P13-A 的 ``chunking_service`` / 多模态分块）
2. **KG 实体命中加 boost**（消费 P13-B 的 KG）
3. **模态扩展**：命中 text segment → 自动拉取同 section 的 image / table / seal segments
   （cross_modal: True 关系；由 P13-A 输出）
4. **模态加权重排**（:class:`ModalityWeightedRanker`）
5. **top_k 截断**

所有上游依赖通过 :mod:`base` 中的 Protocol 注入，便于：

- 测试 mock
- 在 P13-A / P13-B 落地之前先跑通端到端骨架
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from loguru import logger

from src.services.rag.query.base import (
    KGBooster,
    Modality,
    ModalityExpander,
    MultimodalQueryRequest,
    RetrievedSegment,
    VectorSearcher,
)
from src.services.rag.query.modality_weighted_ranker import ModalityWeightedRanker


@dataclass
class MultimodalRetriever:
    """多模态检索器，组合 vector / KG / 模态扩展 / 重排。

    依赖通过构造器注入：

    - ``vector_searcher``：必填
    - ``kg_booster``：可选；None 时跳过 KG boost
    - ``modality_expander``：可选；None 时不做模态扩展
    - ``ranker``：可选；None 时使用默认 :class:`ModalityWeightedRanker`
    """

    vector_searcher: VectorSearcher
    kg_booster: KGBooster | None = None
    modality_expander: ModalityExpander | None = None
    ranker: ModalityWeightedRanker | None = None

    # 扩展候选池放大倍数（在 top_k 之上多取若干，以便重排后仍能截 top_k）
    candidate_multiplier: int = 3

    def __post_init__(self) -> None:
        if self.ranker is None:
            self.ranker = ModalityWeightedRanker()

    async def retrieve(
        self,
        request: MultimodalQueryRequest,
    ) -> list[RetrievedSegment]:
        """执行完整多模态检索流程。"""
        # 1) 向量 + BM25 混合检索（多取一些用于扩展 + 重排）
        candidate_k = max(request.top_k * self.candidate_multiplier, request.top_k)
        try:
            primary = await self.vector_searcher.search(
                query=request.query,
                top_k=candidate_k,
                document_ids=request.document_ids,
            )
        except Exception as exc:  # pragma: no cover - 防御
            logger.exception("vector_searcher.search 失败: {}", exc)
            return []

        if not primary:
            logger.debug("MultimodalRetriever: vector 检索为空")
            return []

        # 记录 base_score（重排时会读）
        for seg in primary:
            seg.breakdown.setdefault("base_score", seg.score)
            seg.modality = Modality.coerce(seg.modality)

        # 2) 模态扩展（同章节 / cross_modal linked）
        expanded: list[RetrievedSegment] = list(primary)
        if self.modality_expander is not None:
            try:
                extras = await self.modality_expander.expand(segments=primary)
            except Exception as exc:
                logger.warning("modality_expander.expand 失败，跳过: {}", exc)
                extras = []
            existing_ids = {s.segment_id for s in expanded}
            for seg in extras:
                if seg.segment_id in existing_ids:
                    continue
                seg.modality = Modality.coerce(seg.modality)
                seg.breakdown.setdefault("base_score", seg.score)
                seg.breakdown["expanded"] = 1.0  # 标记
                expanded.append(seg)
                existing_ids.add(seg.segment_id)

        # 3) KG boost
        kg_boosts: dict[str, float] = {}
        if self.kg_booster is not None:
            try:
                kg_boosts = await self.kg_booster.boost(
                    query=request.query,
                    segments=expanded,
                )
            except Exception as exc:
                logger.warning("kg_booster.boost 失败，跳过: {}", exc)
                kg_boosts = {}

        # 4) 模态加权重排
        ranked = self.ranker.rerank(  # type: ignore[union-attr]
            expanded,
            query=request.query,
            query_overrides=request.modality_weights,
            kg_boosts=kg_boosts,
            top_k=request.top_k,
        )

        logger.debug(
            "MultimodalRetriever: query={!r} primary={} expanded={} ranked={}",
            request.query,
            len(primary),
            len(expanded),
            len(ranked),
        )
        return ranked

    # ---- 辅助：仅做 vector 检索（fallback 路径） ----

    async def text_only(
        self,
        request: MultimodalQueryRequest,
    ) -> list[RetrievedSegment]:
        """纯文本检索（不做模态扩展、不做 VLM），供 fallback API 使用。"""
        primary = await self.vector_searcher.search(
            query=request.query,
            top_k=request.top_k,
            document_ids=request.document_ids,
        )
        text_only = [
            s for s in primary if Modality.coerce(s.modality) == Modality.TEXT
        ]
        for seg in text_only:
            seg.breakdown.setdefault("base_score", seg.score)
            seg.breakdown.setdefault("final_score", seg.score)
        return text_only[: request.top_k]

    # ---- 元信息 ----

    def describe(self) -> dict[str, Any]:
        """返回检索器组件就绪状态，供 /health endpoint 使用。"""
        return {
            "vector_searcher": self.vector_searcher.__class__.__name__,
            "kg_booster": self.kg_booster.__class__.__name__ if self.kg_booster else None,
            "modality_expander": (
                self.modality_expander.__class__.__name__
                if self.modality_expander
                else None
            ),
            "candidate_multiplier": self.candidate_multiplier,
        }
