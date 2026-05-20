"""引文聚合器（DeepTutor 风格）。

把 :class:`RetrievedSegment` 转成结构化、可点击跳转的引文：

- ``segment_id`` 唯一
- ``document_id`` + ``document_name`` + ``page`` + ``char_range``
- ``modality`` 标签（前端按 modality 配不同颜色 / 图标）
- ``snippet``：摘要文本（image / seal 走 alt-text 占位）
- ``score`` / ``score_breakdown``：调试用

同时按 document 聚合，便于前端做"按文档分组"视图。
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from src.services.rag.query.base import Modality, RetrievedSegment


@dataclass
class Citation:
    """单条引文。"""

    segment_id: str
    document_id: str
    document_name: str | None
    modality: str
    page: int | None
    char_range: list[int] | None  # [start, end]
    snippet: str
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class CitationAggregator:
    """聚合 :class:`RetrievedSegment` 为前端可消费的 citations。"""

    snippet_max_chars: int = 240

    def aggregate(self, segments: list[RetrievedSegment]) -> list[dict[str, Any]]:
        """返回扁平 citation 列表（保留排序）。"""
        return [self._to_citation(seg).to_dict() for seg in segments]

    def aggregate_grouped(
        self,
        segments: list[RetrievedSegment],
    ) -> dict[str, dict[str, Any]]:
        """按 ``document_id`` 聚合。

        返回::

            {
                "<doc_id>": {
                    "document_id": ...,
                    "document_name": ...,
                    "citations": [Citation, ...],
                    "best_score": float,
                },
                ...
            }
        """
        grouped: dict[str, dict[str, Any]] = {}
        for seg in segments:
            cit = self._to_citation(seg)
            bucket = grouped.setdefault(
                seg.document_id,
                {
                    "document_id": seg.document_id,
                    "document_name": cit.document_name,
                    "citations": [],
                    "best_score": float("-inf"),
                },
            )
            bucket["citations"].append(cit.to_dict())
            if seg.score > bucket["best_score"]:
                bucket["best_score"] = seg.score
        # 把 -inf 还原为 0.0（防止 JSON 序列化出 Infinity）
        for bucket in grouped.values():
            if bucket["best_score"] == float("-inf"):
                bucket["best_score"] = 0.0
        return grouped

    # ---- 内部 ----

    def _to_citation(self, seg: RetrievedSegment) -> Citation:
        modality = Modality.coerce(seg.modality)
        snippet = self._make_snippet(seg, modality)
        char_range: list[int] | None = list(seg.char_range) if seg.char_range else None
        document_name = seg.metadata.get("document_name") if seg.metadata else None
        return Citation(
            segment_id=seg.segment_id,
            document_id=seg.document_id,
            document_name=document_name,
            modality=modality.value,
            page=seg.page,
            char_range=char_range,
            snippet=snippet,
            score=round(float(seg.score), 6),
            score_breakdown={k: round(float(v), 6) for k, v in seg.breakdown.items()},
        )

    def _make_snippet(self, seg: RetrievedSegment, modality: Modality) -> str:
        if modality in (Modality.IMAGE, Modality.SEAL):
            alt = (
                seg.metadata.get("caption")
                if seg.metadata and seg.metadata.get("caption")
                else f"[{modality.value}]"
            )
            return str(alt)
        if isinstance(seg.content, bytes):
            return f"[binary {len(seg.content)} bytes]"
        text = str(seg.content or "")
        if len(text) > self.snippet_max_chars:
            return text[: self.snippet_max_chars] + "…"
        return text
