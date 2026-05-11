# -*- coding: utf-8 -*-
"""P13-C: CitationAggregator 单元测试。

覆盖：

- 基本字段映射
- snippet 截断
- image / seal 走 caption 或 modality 占位
- aggregate_grouped 按文档聚合
- score_breakdown 透出
"""

from __future__ import annotations

from src.services.rag.query.base import Modality, RetrievedSegment
from src.services.rag.query.citation_aggregator import (
    Citation,
    CitationAggregator,
)


def _seg(
    seg_id: str,
    modality: Modality,
    content,
    doc: str = "doc-1",
    score: float = 0.5,
    page: int | None = 3,
    char_range: tuple[int, int] | None = (10, 50),
    metadata: dict | None = None,
    breakdown: dict | None = None,
) -> RetrievedSegment:
    return RetrievedSegment(
        segment_id=seg_id,
        document_id=doc,
        modality=modality,
        content=content,
        score=score,
        page=page,
        char_range=char_range,
        metadata=metadata or {"document_name": "示例合同.pdf"},
        breakdown=breakdown or {"base_score": score, "modality_weight": 1.0},
    )


def test_aggregate_text_segment() -> None:
    agg = CitationAggregator()
    segs = [_seg("s1", Modality.TEXT, "甲方应在合同生效后 30 日内支付")]
    out = agg.aggregate(segs)
    assert len(out) == 1
    c = out[0]
    assert c["segment_id"] == "s1"
    assert c["document_id"] == "doc-1"
    assert c["document_name"] == "示例合同.pdf"
    assert c["modality"] == "text"
    assert c["page"] == 3
    assert c["char_range"] == [10, 50]
    assert "甲方" in c["snippet"]
    assert c["score"] == 0.5
    assert "modality_weight" in c["score_breakdown"]


def test_snippet_truncation() -> None:
    long = "甲" * 500
    agg = CitationAggregator(snippet_max_chars=50)
    out = agg.aggregate([_seg("s", Modality.TEXT, long)])
    assert out[0]["snippet"].endswith("…")
    # 截 50 字符 + 省略号
    assert len(out[0]["snippet"]) == 51


def test_image_segment_snippet_uses_caption() -> None:
    agg = CitationAggregator()
    segs = [
        _seg(
            "img1",
            Modality.IMAGE,
            b"\x89PNG",
            metadata={"caption": "现场照片：堆放的货物", "document_name": "证据.zip"},
        )
    ]
    out = agg.aggregate(segs)
    assert out[0]["snippet"] == "现场照片：堆放的货物"
    assert out[0]["modality"] == "image"


def test_image_segment_snippet_falls_back() -> None:
    agg = CitationAggregator()
    segs = [_seg("img1", Modality.IMAGE, b"\x89PNG", metadata={"document_name": "x"})]
    out = agg.aggregate(segs)
    assert out[0]["snippet"] == "[image]"


def test_seal_modality_label() -> None:
    agg = CitationAggregator()
    segs = [_seg("seal1", Modality.SEAL, b"\xff", metadata={"document_name": "x"})]
    out = agg.aggregate(segs)
    assert out[0]["modality"] == "seal"
    assert out[0]["snippet"] == "[seal]"


def test_aggregate_grouped_by_document() -> None:
    agg = CitationAggregator()
    segs = [
        _seg("a1", Modality.TEXT, "A1", doc="docA", score=0.7),
        _seg("a2", Modality.TEXT, "A2", doc="docA", score=0.5),
        _seg("b1", Modality.TEXT, "B1", doc="docB", score=0.6),
    ]
    grouped = agg.aggregate_grouped(segs)

    assert set(grouped.keys()) == {"docA", "docB"}
    assert len(grouped["docA"]["citations"]) == 2
    assert grouped["docA"]["best_score"] == 0.7
    assert grouped["docB"]["best_score"] == 0.6


def test_aggregate_grouped_empty() -> None:
    agg = CitationAggregator()
    grouped = agg.aggregate_grouped([])
    assert grouped == {}


def test_citation_dataclass_to_dict() -> None:
    c = Citation(
        segment_id="s",
        document_id="d",
        document_name=None,
        modality="text",
        page=1,
        char_range=[0, 5],
        snippet="hi",
        score=0.5,
    )
    d = c.to_dict()
    assert d["segment_id"] == "s"
    assert d["document_name"] is None
    assert d["score_breakdown"] == {}


def test_score_breakdown_rounded() -> None:
    """breakdown 的 float 被规整到 6 位，避免 -inf / 巨长尾数。"""
    agg = CitationAggregator()
    segs = [
        _seg(
            "s",
            Modality.TEXT,
            "hi",
            breakdown={"base_score": 1 / 3, "kg_boost": 0.0},
        )
    ]
    out = agg.aggregate(segs)
    assert out[0]["score_breakdown"]["base_score"] == round(1 / 3, 6)


def test_no_metadata_document_name_is_none() -> None:
    agg = CitationAggregator()
    segs = [
        RetrievedSegment(
            segment_id="x",
            document_id="d",
            modality=Modality.TEXT,
            content="content",
            score=0.5,
        )
    ]
    out = agg.aggregate(segs)
    assert out[0]["document_name"] is None
