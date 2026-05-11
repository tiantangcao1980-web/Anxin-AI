# -*- coding: utf-8 -*-
"""P13-B BelongsToChainBuilder 单元测试。"""

from __future__ import annotations

from src.services.rag.kg.base import (
    EntityType,
    Modality,
    RelationType,
    Segment,
)
from src.services.rag.kg.belongs_to_chain import BelongsToChainBuilder


def test_outline_builds_full_chain():
    structure = {
        "document": {"id": "doc_001", "title": "合作协议"},
        "outline": [
            {
                "id": "ch_1",
                "level": "chapter",
                "title": "第一章 总则",
                "children": [
                    {
                        "id": "art_1",
                        "level": "article",
                        "title": "第一条 合作目的",
                        "children": [
                            {
                                "id": "cl_1",
                                "level": "clause",
                                "title": "（一）",
                            }
                        ],
                    }
                ],
            }
        ],
    }
    builder = BelongsToChainBuilder()
    entities, relations = builder.build("doc_001", structure)

    # 4 个实体：文档 + 章 + 条 + 款
    assert len(entities) == 4
    levels = {e.properties["level"] for e in entities}
    assert {"document", "chapter", "article", "clause"}.issubset(levels)

    # 3 条 BELONGS_TO 关系
    belongs = [r for r in relations if r.type == RelationType.BELONGS_TO]
    assert len(belongs) == 3
    # 全部 confidence = 1.0
    assert all(r.confidence == 1.0 for r in belongs)
    # 全部非 cross_modal
    assert all(not r.cross_modal for r in belongs)


def test_outline_chain_links_match_parent_child_pairs():
    structure = {
        "document": {"id": "doc_001", "title": "Doc"},
        "outline": [
            {
                "id": "ch_1",
                "level": "chapter",
                "title": "第一章",
                "children": [
                    {"id": "art_1", "level": "article", "title": "第一条"},
                ],
            }
        ],
    }
    builder = BelongsToChainBuilder()
    entities, relations = builder.build("doc_001", structure)

    by_level = {e.properties["level"]: e for e in entities}
    chapter = by_level["chapter"]
    doc = by_level["document"]
    article = by_level["article"]

    # 章 BELONGS_TO 文档
    chap_to_doc = [
        r for r in relations
        if r.source_entity == chapter.entity_id and r.target_entity == doc.entity_id
    ]
    assert len(chap_to_doc) == 1

    # 条 BELONGS_TO 章
    art_to_chap = [
        r for r in relations
        if r.source_entity == article.entity_id and r.target_entity == chapter.entity_id
    ]
    assert len(art_to_chap) == 1


def test_fallback_extracts_articles_from_segments():
    """无 outline 时退化为从 segments 抓 第 N 条 / 第 N 章。"""
    seg_a = Segment(
        segment_id="s1",
        modality=Modality.TEXT.value,
        content="第一章 总则\n本协议适用于...",
    )
    seg_b = Segment(
        segment_id="s2",
        modality=Modality.TEXT.value,
        content="第一条 合作目的\n双方为...第二条 合作期限\n自...",
    )
    builder = BelongsToChainBuilder()
    entities, relations = builder.build(
        "doc_xyz", structure=None, segments=[seg_a, seg_b]
    )

    titles = {e.name for e in entities}
    assert "第一章" in titles
    assert "第一条" in titles
    assert "第二条" in titles

    # 至少有 2 条 BELONGS_TO（条 → 章 / 章 → 文档）
    belongs = [r for r in relations if r.type == RelationType.BELONGS_TO]
    assert len(belongs) >= 3


def test_no_structure_no_segments_only_returns_document_root():
    builder = BelongsToChainBuilder()
    entities, relations = builder.build("doc_solo", None, None)
    assert len(entities) == 1
    assert entities[0].properties["level"] == "document"
    assert relations == []


def test_document_entity_id_is_stable():
    builder = BelongsToChainBuilder()
    e1, _ = builder.build("doc_001", None, None)
    e2, _ = builder.build("doc_001", None, None)
    assert e1[0].entity_id == e2[0].entity_id
