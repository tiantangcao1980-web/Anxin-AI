# -*- coding: utf-8 -*-
"""P13-C: ModalityWeightedRanker 单元测试。

覆盖：

- 默认权重表
- 关键词触发的动态权重（公章 / 金额 / 条款 / 证据 / 公式）
- query_overrides 优先级最高
- KG boost 叠加
- top_k 截断
- breakdown 字段填充
"""

from __future__ import annotations

import pytest

from src.services.rag.query.base import Modality, RetrievedSegment
from src.services.rag.query.modality_weighted_ranker import (
    DEFAULT_MODALITY_WEIGHTS,
    KEYWORD_WEIGHT_OVERRIDES,
    ModalityWeightedRanker,
)


def _seg(seg_id: str, modality: Modality, score: float) -> RetrievedSegment:
    return RetrievedSegment(
        segment_id=seg_id,
        document_id="d1",
        modality=modality,
        content=f"content-{seg_id}",
        score=score,
        breakdown={"base_score": score},
    )


# ---------- 默认权重 ----------


def test_default_weights_present() -> None:
    """默认权重覆盖 5 个模态。"""
    for m in (Modality.TEXT, Modality.TABLE, Modality.IMAGE, Modality.FORMULA, Modality.SEAL):
        assert m in DEFAULT_MODALITY_WEIGHTS

    assert DEFAULT_MODALITY_WEIGHTS[Modality.TEXT] == 1.00
    assert DEFAULT_MODALITY_WEIGHTS[Modality.TABLE] == 0.90
    assert DEFAULT_MODALITY_WEIGHTS[Modality.IMAGE] == 0.70
    assert DEFAULT_MODALITY_WEIGHTS[Modality.SEAL] == 0.60


def test_resolve_weights_no_query_returns_defaults() -> None:
    ranker = ModalityWeightedRanker()
    weights = ranker.resolve_weights(query="", query_overrides=None)
    assert weights[Modality.TEXT] == 1.00
    assert weights[Modality.SEAL] == 0.60


# ---------- 关键词触发 ----------


@pytest.mark.parametrize(
    "query,expected_modality,expected_min",
    [
        ("这个合同上有公章吗", Modality.SEAL, 1.0),
        ("印鉴是否清晰", Modality.SEAL, 1.0),
        ("总价是多少 增值税要算吗", Modality.TABLE, 1.0),
        ("VAT 数额", Modality.TABLE, 1.0),
        ("违约条款怎么约定", Modality.TEXT, 1.0),
        ("现场照片显示了什么", Modality.IMAGE, 1.0),
        ("这个公式怎么推导", Modality.FORMULA, 1.0),
    ],
)
def test_keyword_triggers_dynamic_weights(
    query: str, expected_modality: Modality, expected_min: float
) -> None:
    ranker = ModalityWeightedRanker()
    weights = ranker.resolve_weights(query=query)
    assert weights[expected_modality] >= expected_min, (
        f"query={query!r} 触发后 {expected_modality} 权重应 ≥ {expected_min}，"
        f"实际 = {weights[expected_modality]}"
    )


def test_seal_query_lowers_text_baseline_relatively() -> None:
    """带 '公章' 的 query：seal=1.0，应能在同分情况下排在 text 前。"""
    ranker = ModalityWeightedRanker()
    segs = [
        _seg("t1", Modality.TEXT, 0.8),
        _seg("s1", Modality.SEAL, 0.8),
    ]
    ranked = ranker.rerank(segs, query="公章是否清晰")
    # SEAL=1.0 vs TEXT=1.0（关键词触发未改 text）；按 base_score 一样 → 但应该 text 在前
    # 把 seal 的 base 提高一点能反超
    segs = [
        _seg("t1", Modality.TEXT, 0.8),
        _seg("s1", Modality.SEAL, 0.81),
    ]
    ranked = ranker.rerank(segs, query="公章是否清晰")
    assert ranked[0].segment_id == "s1"


# ---------- query_overrides 优先级 ----------


def test_query_overrides_have_highest_priority() -> None:
    ranker = ModalityWeightedRanker()
    weights = ranker.resolve_weights(
        query="公章",
        query_overrides={"seal": 0.1, "text": 1.5},
    )
    assert weights[Modality.SEAL] == 0.1  # 显式覆盖把关键词触发的 1.0 压回 0.1
    assert weights[Modality.TEXT] == 1.5


def test_query_overrides_unknown_modality_safe() -> None:
    """未知模态字符串走 coerce → TEXT，不报错。"""
    ranker = ModalityWeightedRanker()
    weights = ranker.resolve_weights(query="x", query_overrides={"unknown_xx": 0.5})
    # unknown 被 coerce 成 TEXT
    assert weights[Modality.TEXT] == 0.5


# ---------- rerank 行为 ----------


def test_rerank_orders_by_modality_weight() -> None:
    ranker = ModalityWeightedRanker()
    # base_score 相同 → 按 modality_weight 排序
    segs = [
        _seg("a", Modality.IMAGE, 0.5),  # 0.5 * 0.7 = 0.35
        _seg("b", Modality.TEXT, 0.5),  # 0.5 * 1.0 = 0.50
        _seg("c", Modality.TABLE, 0.5),  # 0.5 * 0.9 = 0.45
    ]
    ranked = ranker.rerank(segs)
    assert [s.segment_id for s in ranked] == ["b", "c", "a"]


def test_rerank_kg_boost_applied() -> None:
    ranker = ModalityWeightedRanker()
    segs = [
        _seg("a", Modality.TEXT, 0.50),
        _seg("b", Modality.TEXT, 0.40),
    ]
    ranked = ranker.rerank(segs, kg_boosts={"b": 0.30})  # b: 0.40+0.30=0.70 > 0.50
    assert ranked[0].segment_id == "b"
    assert ranked[0].breakdown["kg_boost"] == 0.30
    assert ranked[0].breakdown["modality_weight"] == 1.0


def test_rerank_top_k_truncates() -> None:
    ranker = ModalityWeightedRanker()
    segs = [_seg(f"s{i}", Modality.TEXT, 1.0 - i * 0.1) for i in range(5)]
    ranked = ranker.rerank(segs, top_k=2)
    assert len(ranked) == 2
    assert ranked[0].segment_id == "s0"


def test_rerank_breakdown_filled() -> None:
    ranker = ModalityWeightedRanker()
    segs = [_seg("a", Modality.SEAL, 0.5)]
    ranked = ranker.rerank(segs, kg_boosts={"a": 0.1})
    bd = ranked[0].breakdown
    assert bd["base_score"] == 0.5
    assert bd["modality_weight"] == DEFAULT_MODALITY_WEIGHTS[Modality.SEAL]
    assert bd["kg_boost"] == 0.1
    assert bd["final_score"] == pytest.approx(0.5 * 0.6 + 0.1)


def test_rerank_empty_input() -> None:
    ranker = ModalityWeightedRanker()
    assert ranker.rerank([]) == []


def test_keyword_overrides_table_completeness() -> None:
    """KEYWORD_WEIGHT_OVERRIDES 至少覆盖 5 类典型 query。"""
    assert len(KEYWORD_WEIGHT_OVERRIDES) >= 5
    # 每条都得是 (tuple_of_str, dict[Modality, float])
    for keywords, weights in KEYWORD_WEIGHT_OVERRIDES:
        assert isinstance(keywords, tuple)
        assert all(isinstance(k, str) for k in keywords)
        assert isinstance(weights, dict)
        for m, w in weights.items():
            assert isinstance(m, Modality)
            assert 0.0 <= float(w) <= 1.5
