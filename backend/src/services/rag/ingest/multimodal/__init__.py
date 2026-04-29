# -*- coding: utf-8 -*-
"""多模态文档解析（P13-A）。

借鉴 HKUDS/RAG-Anything 的 MinerU + 模态路由分流设计：

- :class:`MultimodalIngestor`：抽象接口，所有适配器（MinerU、Office、扫描件
  专用 OCR）都实现 ``ingest`` / ``supports``。
- :class:`MinerUIngestor`：MinerU 适配器（当前 mock + 真接入 TODO）。
- :class:`ModalityRouter`：把 :class:`ParsedSegment` 分流到 text/image/table/
  formula/seal 各自的下游处理器。
- :class:`SealDetector` / :class:`TableExtractor` / :class:`FormulaRecognizer`：
  各模态专用器（mock，预留真实接入位点）。
- :class:`LayoutPreserver`：中文法律文档"章 / 条 / 款 / 项"层级保留。

下游契约（与 P13-B KG / P13-C VLM Query 衔接）：

    IngestResult.segments → 每个 ParsedSegment 是知识图谱节点候选 +
    向量化候选，metadata 带 page / bbox / parent_section / confidence。
"""

from src.services.rag.ingest.multimodal.base import (
    IngestResult,
    MultimodalIngestor,
    ParsedSegment,
)
from src.services.rag.ingest.multimodal.formula_recognizer import FormulaRecognizer
from src.services.rag.ingest.multimodal.layout_preserver import LayoutPreserver
from src.services.rag.ingest.multimodal.mineru_adapter import MinerUIngestor
from src.services.rag.ingest.multimodal.modality_router import ModalityRouter
from src.services.rag.ingest.multimodal.seal_detector import SealDetector
from src.services.rag.ingest.multimodal.table_extractor import TableExtractor

__all__ = [
    "FormulaRecognizer",
    "IngestResult",
    "LayoutPreserver",
    "MinerUIngestor",
    "ModalityRouter",
    "MultimodalIngestor",
    "ParsedSegment",
    "SealDetector",
    "TableExtractor",
]
