"""多模态接入抽象契约。

::

    ParsedSegment   单段解析结果（text / image / table / formula / seal）
    IngestResult    单文档总解析结果
    MultimodalIngestor   抽象适配器接口

所有 segment 输出统一契约：

- ``segment_id``：在文档内全局唯一，建议使用 ``f"{doc_id}:{idx}"``。
- ``modality``：枚举字符串。下游 ``ModalityRouter`` 据此分流。
- ``content``：文本类是 ``str``；图像 / 公章是 ``bytes``（PNG / JPEG）；
  表格是已结构化的 markdown 字符串；公式是 LaTeX 字符串。
- ``metadata``：必含 ``page`` / ``bbox`` / ``parent_section``，可选
  ``confidence`` / ``language`` 等。
- ``embeddings``：留给下游 RAG 流水线填充，本阶段不产出。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Modality(str, Enum):
    """模态枚举。下游 :class:`ModalityRouter` 据此分流处理。"""

    TEXT = "text"
    IMAGE = "image"
    TABLE = "table"
    FORMULA = "formula"
    SEAL = "seal"


@dataclass
class ParsedSegment:
    """单段解析结果（一页 / 一区域 / 一个图表）。"""

    segment_id: str
    modality: str  # 见 :class:`Modality`
    content: str | bytes
    metadata: dict[str, Any] = field(default_factory=dict)
    embeddings: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为可 JSON 化的 dict（``bytes`` content 会替换为占位符）。"""
        if isinstance(self.content, bytes):
            content_repr: str | bytes = f"<bytes:{len(self.content)}>"
        else:
            content_repr = self.content
        return {
            "segment_id": self.segment_id,
            "modality": self.modality,
            "content": content_repr,
            "metadata": self.metadata,
            "embeddings": self.embeddings,
        }


@dataclass
class IngestResult:
    """单文档完整解析结果。"""

    document_id: str
    segments: list[ParsedSegment] = field(default_factory=list)
    structure: dict[str, Any] = field(default_factory=dict)
    statistics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def count_by_modality(self) -> dict[str, int]:
        """按模态聚合 segment 计数（便于 statistics 上报）。"""
        counts: dict[str, int] = {}
        for seg in self.segments:
            counts[seg.modality] = counts.get(seg.modality, 0) + 1
        return counts

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "segments": [s.to_dict() for s in self.segments],
            "structure": self.structure,
            "statistics": self.statistics,
            "warnings": self.warnings,
        }


class MultimodalIngestor(ABC):
    """多模态文档解析适配器抽象基类。

    实现方需要：

    1. ``supports(file_path)``：根据扩展名 / magic number 判断是否能解析。
    2. ``ingest(file_path, doc_type)``：异步解析并返回 :class:`IngestResult`。

    子类示例：:class:`MinerUIngestor`（PDF / 扫描件 / Office）。
    """

    @abstractmethod
    async def ingest(self, file_path: Path, doc_type: str = "auto") -> IngestResult:
        """解析单文档为多模态 segment 列表。

        Args:
            file_path: 待解析文件绝对路径。
            doc_type: 文档类型提示（``contract`` / ``scan`` / ``report`` / ``auto``）。
                ``auto`` 会基于 magic number / 扩展名 / 文件名启发式判断。

        Returns:
            :class:`IngestResult`，包含 segment 列表 + 结构树 + 统计信息。
        """

    @abstractmethod
    async def supports(self, file_path: Path) -> bool:
        """判断当前适配器是否能解析该文件。"""
