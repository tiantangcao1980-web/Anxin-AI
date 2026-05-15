"""P13-C VLM 增强 Query 模块。

公开 API：

- :class:`MultimodalQueryRequest` / :class:`RetrievedSegment` / :class:`VLMQueryResponse` (base)
- :class:`MultimodalRetriever`  (multimodal_retriever)
- :class:`VLMQueryEngine`       (vlm_query_engine)
- :class:`ModalityWeightedRanker` (modality_weighted_ranker)
- :class:`CitationAggregator`   (citation_aggregator)

借鉴 HKUDS RAG-Anything 的 VLM-Enhanced Query 模式：
检索时把命中段附带的图（合同附件图 / 证据照片 / 公章 / 财务表截图）
一起喂给 VLM 作答，得到 visual_grounding。
"""

from src.services.rag.query.base import (
    KGBooster,
    Modality,
    ModalityExpander,
    MultimodalQueryRequest,
    RetrievedSegment,
    VectorSearcher,
    VLMClient,
    VLMQueryResponse,
)
from src.services.rag.query.citation_aggregator import (
    Citation,
    CitationAggregator,
)
from src.services.rag.query.modality_weighted_ranker import (
    DEFAULT_MODALITY_WEIGHTS,
    KEYWORD_WEIGHT_OVERRIDES,
    ModalityWeightedRanker,
)
from src.services.rag.query.multimodal_retriever import MultimodalRetriever
from src.services.rag.query.vlm_query_engine import VLMQueryEngine

__all__ = [
    "MultimodalQueryRequest",
    "RetrievedSegment",
    "VLMQueryResponse",
    "Modality",
    "VectorSearcher",
    "KGBooster",
    "ModalityExpander",
    "VLMClient",
    "ModalityWeightedRanker",
    "DEFAULT_MODALITY_WEIGHTS",
    "KEYWORD_WEIGHT_OVERRIDES",
    "MultimodalRetriever",
    "VLMQueryEngine",
    "CitationAggregator",
    "Citation",
]
