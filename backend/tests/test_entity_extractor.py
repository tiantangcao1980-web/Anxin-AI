# -*- coding: utf-8 -*-
"""P13-B EntityExtractor 单元测试。"""

from __future__ import annotations

import json

import pytest

from src.services.rag.kg.base import EntityType, Modality, Segment
from src.services.rag.kg.entity_extractor import EntityExtractor, _make_entity_id


# ---------------------------------------------------------------------------
# 关键词 fallback
# ---------------------------------------------------------------------------


async def test_keyword_extract_party_obligation_amount_date():
    seg = Segment(
        segment_id="s1",
        modality="text",
        content=(
            "甲方应当在 2025-06-30 前向乙方支付货款人民币 100,000.00 元，"
            "并保证按时交付。本合同适用《中华人民共和国民法典》第五百零九条。"
        ),
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([seg])

    types = {e.type for e in entities}
    assert EntityType.LEGAL_PARTY in types
    assert EntityType.AMOUNT in types
    assert EntityType.DATE in types
    assert EntityType.REGULATION in types
    # 触发词产生 OBLIGATION 子句
    assert EntityType.OBLIGATION in types

    # 含两个不同的 party：甲方 / 乙方
    party_names = {e.name for e in entities if e.type == EntityType.LEGAL_PARTY}
    assert {"甲方", "乙方"}.issubset(party_names)


async def test_keyword_extract_dedup_same_entity():
    """同一段内多次出现"甲方"应去重，但保留所有 mention 位置。"""
    seg = Segment(
        segment_id="s1",
        modality="text",
        content="甲方应付款。甲方负责安装。甲方承担运费。",
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([seg])

    parties = [e for e in entities if e.type == EntityType.LEGAL_PARTY and e.name == "甲方"]
    assert len(parties) == 1
    assert len(parties[0].mentions) >= 3


async def test_modality_segment_creates_seal_entity():
    seg = Segment(
        segment_id="seal_001",
        modality=Modality.SEAL.value,
        content="",
        metadata={"name": "甲方公章", "page": 3},
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([seg])

    assert len(entities) == 1
    e = entities[0]
    assert e.type == EntityType.SEAL
    assert e.name == "甲方公章"
    assert e.mentions[0]["modality"] == "seal"


# ---------------------------------------------------------------------------
# LLM 路径（mock async callable）
# ---------------------------------------------------------------------------


async def test_llm_extract_parses_json_array():
    fake_output = json.dumps(
        [
            {"name": "买方", "type": "legal_party", "aliases": ["甲方"], "confidence": 0.9},
            {"name": "《公司法》", "type": "regulation", "confidence": 0.95},
            {"name": "应支付货款", "type": "obligation", "confidence": 0.7},
        ],
        ensure_ascii=False,
    )
    calls: list[str] = []

    async def fake_llm(prompt: str) -> str:
        calls.append(prompt)
        return fake_output

    seg = Segment(
        segment_id="s1",
        modality="text",
        content="买方（甲方）应支付货款，依据《公司法》执行。",
    )
    extractor = EntityExtractor(llm_call=fake_llm, mode="llm")
    entities = await extractor.extract([seg])

    assert len(calls) == 1  # 只调用一次
    by_type = {e.type for e in entities}
    assert EntityType.LEGAL_PARTY in by_type
    assert EntityType.REGULATION in by_type
    assert EntityType.OBLIGATION in by_type

    party = next(e for e in entities if e.type == EntityType.LEGAL_PARTY)
    assert "甲方" in party.aliases


async def test_llm_extract_handles_markdown_fence():
    """LLM 偶尔会用 ```json ... ``` 包裹——测试解析鲁棒性。"""
    fake = """```json
[
  {"name": "甲方", "type": "legal_party", "confidence": 0.9}
]
```"""

    async def fake_llm(prompt: str) -> str:
        return fake

    seg = Segment(segment_id="s1", modality="text", content="甲方应付款")
    extractor = EntityExtractor(llm_call=fake_llm, mode="llm")
    entities = await extractor.extract([seg])

    assert len(entities) == 1
    assert entities[0].name == "甲方"


async def test_llm_failure_falls_back_to_keywords(monkeypatch):
    async def fake_llm(prompt: str) -> str:
        raise RuntimeError("LLM 服务超时")

    seg = Segment(
        segment_id="s1",
        modality="text",
        content="甲方应支付乙方人民币 5,000 元。",
    )
    extractor = EntityExtractor(llm_call=fake_llm, mode="auto")
    entities = await extractor.extract([seg])

    # 关键词 fallback 一定能识别出甲方/乙方/金额
    types = {e.type for e in entities}
    assert EntityType.LEGAL_PARTY in types
    assert EntityType.AMOUNT in types


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------


def test_make_entity_id_is_stable_and_unique():
    a = _make_entity_id("甲方", EntityType.LEGAL_PARTY)
    b = _make_entity_id("甲方", EntityType.LEGAL_PARTY)
    c = _make_entity_id("乙方", EntityType.LEGAL_PARTY)
    d = _make_entity_id("甲方", EntityType.OBLIGATION)
    assert a == b
    assert a != c
    assert a != d  # 同名不同类型也要分开


async def test_empty_segments_returns_empty():
    extractor = EntityExtractor(mode="mock")
    assert await extractor.extract([]) == []


async def test_non_text_modality_with_empty_content_skips_text_extraction():
    seg = Segment(
        segment_id="img_1",
        modality=Modality.IMAGE.value,
        content="",
        metadata={"caption": "公章特写"},
    )
    extractor = EntityExtractor(mode="mock")
    entities = await extractor.extract([seg])
    assert len(entities) == 1
    # IMAGE 段在 ontology 默认归 GENERIC（非 SEAL，因为 modality=image）
    assert entities[0].type == EntityType.GENERIC
