"""AI 议价多轮策略专项测试（P7-E）。

覆盖路径：
    Round 1   anchor 在 target_price - 30%
    Round 2-3 concede（按 mood 让 5/7/10%）
    Round 4+  trade（条件换价）
    ±5%       close_deal（move_type 仍标 concede）
    +15%      walk_away
    非法输入   ValueError
    脚本格式   中英文双脚本
"""

from __future__ import annotations

import pytest
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.agents.personas.ecommerce_assistant import (  # noqa: E402
    ANCHOR_DISCOUNT_PCT,
    CLOSE_DEAL_BAND_PCT,
    CONCEDE_STEP_AGGRESSIVE,
    CONCEDE_STEP_FRIENDLY,
    TRADE_AFTER_ROUND,
    WALK_AWAY_THRESHOLD_PCT,
    EcommerceAssistantAgent,
)


@pytest.fixture
def persona() -> EcommerceAssistantAgent:
    return EcommerceAssistantAgent()


# ---------------------------------------------------------------------------
# 阈值常量回归测试 — 防止后续误改
# ---------------------------------------------------------------------------
def test_strategy_constants():
    assert ANCHOR_DISCOUNT_PCT == 30.0
    assert WALK_AWAY_THRESHOLD_PCT == 15.0
    assert CLOSE_DEAL_BAND_PCT == 5.0
    assert TRADE_AFTER_ROUND == 3
    assert CONCEDE_STEP_AGGRESSIVE < CONCEDE_STEP_FRIENDLY  # aggressive 让得少


# ---------------------------------------------------------------------------
# Round 1: anchor
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_round1_anchors_at_minus_30pct(persona):
    move = await persona.negotiate(target_price=100.0, mood="moderate", history=[])
    assert move.move_type == "anchor"
    # 70 = 100 * (1 - 30%)
    assert move.proposed_price == pytest.approx(70.0, abs=0.01)
    # 双语脚本
    assert "中：" in move.script_text
    assert "EN:" in move.script_text or "EN：" in move.script_text
    # bottom_line_distance_pct = 30
    assert move.bottom_line_distance_pct == pytest.approx(30.0, abs=0.1)


# ---------------------------------------------------------------------------
# Round 2-3: concede
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_round2_concedes_with_mood(persona):
    history = [{"round": 1, "our_price": 70.0, "their_price": 110.0}]
    move = await persona.negotiate(target_price=100.0, mood="aggressive", history=history)
    assert move.move_type == "concede"
    # aggressive 让 5%：70 + 5 = 75
    assert move.proposed_price == pytest.approx(75.0, abs=0.5)


@pytest.mark.asyncio
async def test_round2_friendly_concedes_more(persona):
    history = [{"round": 1, "our_price": 70.0, "their_price": 110.0}]
    move = await persona.negotiate(target_price=100.0, mood="friendly", history=history)
    # friendly 让 10%：70 + 10 = 80
    assert move.proposed_price == pytest.approx(80.0, abs=0.5)


# ---------------------------------------------------------------------------
# Round 4+: trade
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_round4_switches_to_trade(persona):
    history = [
        {"round": 1, "our_price": 70.0, "their_price": 110.0},
        {"round": 2, "our_price": 75.0, "their_price": 108.0},
        {"round": 3, "our_price": 82.0, "their_price": 106.0},
    ]
    move = await persona.negotiate(target_price=100.0, mood="moderate", history=history)
    assert move.move_type == "trade"
    # trade 必须带换价条件
    assert "moq" in move.proposed_terms
    assert "framework_months" in move.proposed_terms
    # 中英文脚本里都要提 MOQ
    assert "MOQ" in move.script_text


# ---------------------------------------------------------------------------
# Close deal: ±5% 内
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_close_deal_when_within_band(persona):
    # 对方报价 102，距 100 仅 2%，触发收口
    history = [
        {"round": 1, "our_price": 70.0, "their_price": 110.0},
        {"round": 2, "our_price": 95.0, "their_price": 102.0},
    ]
    move = await persona.negotiate(target_price=100.0, mood="moderate", history=history)
    # 收口仍标 concede（语义 = 最后一让），但 terms 显示 close_deal
    assert move.move_type == "concede"
    assert move.proposed_terms.get("action") == "close_deal"
    # 终价取双方平均
    assert move.proposed_price == pytest.approx(101.0, abs=0.5)


# ---------------------------------------------------------------------------
# Walk away: > +15%
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_walk_away_when_over_threshold(persona):
    # 对方报价 120，target=100，超出 20% → walk_away
    history = [{"round": 1, "our_price": 70.0, "their_price": 120.0}]
    move = await persona.negotiate(target_price=100.0, mood="moderate", history=history)
    assert move.move_type == "walk_away"
    assert move.proposed_terms.get("action") == "walk_away"
    # 距离 = 20%
    assert move.bottom_line_distance_pct == pytest.approx(20.0, abs=0.5)
    # 脚本必须保持礼貌（"再观察"等收尾）
    assert "再观察" in move.script_text or "re-evaluate" in move.script_text.lower()


@pytest.mark.asyncio
async def test_walk_away_boundary_just_under_15pct_does_not_trigger(persona):
    # 略低于 +15% 阈值 → 不触发 walk_away（应走 concede / trade 路径）
    history = [{"round": 1, "our_price": 70.0, "their_price": 114.0}]
    move = await persona.negotiate(target_price=100.0, mood="moderate", history=history)
    assert move.move_type != "walk_away"  # 阈值内不触发


@pytest.mark.asyncio
async def test_walk_away_just_over_15pct_triggers(persona):
    history = [{"round": 1, "our_price": 70.0, "their_price": 115.5}]
    move = await persona.negotiate(target_price=100.0, mood="moderate", history=history)
    assert move.move_type == "walk_away"


# ---------------------------------------------------------------------------
# 输入校验
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_mood_raises(persona):
    with pytest.raises(ValueError, match="mood"):
        await persona.negotiate(target_price=100.0, mood="hostile", history=[])


@pytest.mark.asyncio
async def test_negative_target_price_raises(persona):
    with pytest.raises(ValueError, match="target_price"):
        await persona.negotiate(target_price=-1.0, mood="moderate", history=[])


# ---------------------------------------------------------------------------
# 让步单调性：连续多轮让步价格不应回退
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concede_monotonic_increase(persona):
    history = [{"round": 1, "our_price": 70.0, "their_price": 110.0}]
    move2 = await persona.negotiate(target_price=100.0, mood="moderate", history=history)
    history.append({"round": 2, "our_price": move2.proposed_price, "their_price": 108.0})
    move3 = await persona.negotiate(target_price=100.0, mood="moderate", history=history)
    assert move3.proposed_price >= move2.proposed_price  # 让步单调
    assert move3.proposed_price <= 100.0  # 不超过 target


# ---------------------------------------------------------------------------
# 脚本质量：anchor 包含付款条款，不只有价格
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_anchor_script_contains_payment_terms(persona):
    move = await persona.negotiate(target_price=200.0, mood="moderate", history=[])
    # anchor 必须带付款条款（影响落地 likelihood）
    assert (
        "T/T" in move.script_text
        or "deposit" in move.script_text.lower()
        or "定金" in move.script_text
    )
