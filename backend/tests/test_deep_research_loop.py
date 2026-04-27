# -*- coding: utf-8 -*-
"""P7-B: DeepResearch 迭代循环单测 —— 收敛 / 去重 / 引文累积。

覆盖闸门：
    1. max_iterations 硬上限
    2. pending 空时提前停
    3. citations 数到上限提前停
    4. 同 query 不会跑两次（去重）
    5. confidence 计算 / report 缓存
"""

from __future__ import annotations

import json

import pytest

from src.agents.personas.market_researcher import (
    MarketResearcherAgent,
    _MAX_CITATIONS_PER_REPORT,
)
from src.agents.personas.research_models import (
    Citation,
    ResearchReport,
    compute_confidence,
)


def _llm_stub_with_next(next_qs: list[str]):
    def _call(system: str, user: str) -> str:  # noqa: ARG001
        return json.dumps(
            {"summary": "ok", "rationale": "stub", "next_questions": next_qs},
            ensure_ascii=False,
        )

    return _call


# ---------------------------------------------------------------------------
# 闸门 1: max_iterations 硬上限
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_research_respects_max_iterations():
    """即使每步都吐出 next_questions，也不超过 max_iterations。"""
    agent = MarketResearcherAgent(
        llm_callable=_llm_stub_with_next(["新问题 A", "新问题 B"]),
    )

    async def fake_kb(q: str, k: int):  # noqa: ARG001
        return [{"title": f"kb-{q}", "url": f"http://kb/{q}", "excerpt": "..."}]

    agent.kb_search = fake_kb

    report = await agent.deep_research("母问题", max_iterations=3)
    assert len(report.steps) <= 3


# ---------------------------------------------------------------------------
# 闸门 2: pending 空 → 提前停
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_research_stops_when_pending_empty():
    """LLM 不吐 next_questions、无 seed → 1 步后停。"""
    agent = MarketResearcherAgent(llm_callable=_llm_stub_with_next([]))
    report = await agent.deep_research("母问题", max_iterations=10)
    assert len(report.steps) == 1


# ---------------------------------------------------------------------------
# 闸门 3: citations 上限
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_research_caps_citations():
    """每步注入 100 条 kb 引文，最终 report 内不会超 _MAX_CITATIONS_PER_REPORT。"""
    agent = MarketResearcherAgent(llm_callable=_llm_stub_with_next([]))

    async def big_kb(q: str, k: int):  # noqa: ARG001
        return [
            {"title": f"t-{i}", "url": f"http://x/{q}/{i}", "excerpt": "..."}
            for i in range(100)
        ]

    agent.kb_search = big_kb

    report = await agent.deep_research("X", max_iterations=5)
    assert len(report.citations) <= _MAX_CITATIONS_PER_REPORT


# ---------------------------------------------------------------------------
# 闸门 4: 去重（同 query 不重复跑）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_research_dedup_query_loop():
    """LLM 始终把母问题作为 next → 应被 visited 集合截断。"""
    agent = MarketResearcherAgent(llm_callable=_llm_stub_with_next(["母问题"]))

    async def kb(q: str, k: int):  # noqa: ARG001
        return [{"title": "x", "url": "http://x/once", "excerpt": "..."}]

    agent.kb_search = kb

    report = await agent.deep_research("母问题", max_iterations=10)
    assert len(report.steps) == 1


@pytest.mark.asyncio
async def test_deep_research_dedup_seed_query_with_question():
    """seed_queries 含母问题副本 → 仍只跑 1 步。"""
    agent = MarketResearcherAgent(llm_callable=_llm_stub_with_next([]))
    report = await agent.deep_research(
        "Q",
        max_iterations=5,
        seed_queries=["q", " Q ", "Q\n"],
    )
    # 「Q」/「 Q 」 normalize 后相等，只算 1 次
    assert len(report.steps) == 1


# ---------------------------------------------------------------------------
# 引文累积 + confidence 计算
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_research_accumulates_citations():
    agent = MarketResearcherAgent(llm_callable=_llm_stub_with_next([]))

    async def kb(q: str, k: int):  # noqa: ARG001
        return [
            {"title": "a", "url": f"http://a/{q}", "excerpt": "x", "confidence": 0.8},
            {"title": "b", "url": f"http://b/{q}", "excerpt": "y", "confidence": 0.6},
        ]

    agent.kb_search = kb

    report = await agent.deep_research(
        "Q", max_iterations=2, seed_queries=["seed1"]
    )
    # 至少跑了 2 步（Q + seed1），合计 4 条引文
    assert len(report.citations) >= 4
    assert 0 < report.confidence_score <= 1.0


def test_compute_confidence_few_citations_penalty():
    from src.agents.personas.research_models import ResearchStep

    step = ResearchStep(
        step_id=1,
        query="q",
        findings=[Citation(source="kb", url="u", confidence=1.0)],
    )
    # 只有 1 条 → 应被 ×0.6 惩罚
    assert compute_confidence([step]) == pytest.approx(0.6, abs=1e-6)


def test_compute_confidence_zero_when_empty():
    assert compute_confidence([]) == 0.0


# ---------------------------------------------------------------------------
# 报告缓存（GET /research/{id} 用）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_cached_after_deep_research():
    agent = MarketResearcherAgent(llm_callable=_llm_stub_with_next([]))
    report = await agent.deep_research("Q", max_iterations=1)
    cached = agent.get_report(report.report_id)
    assert cached is not None
    assert cached.report_id == report.report_id


@pytest.mark.asyncio
async def test_report_cache_lru_eviction():
    agent = MarketResearcherAgent(llm_callable=_llm_stub_with_next([]))
    # 故意改小容量，只能放 3 份
    from src.agents.personas import market_researcher as mr

    agent._report_cache.clear()
    monkey_cap = 3
    original = mr._REPORT_CACHE_CAP
    mr._REPORT_CACHE_CAP = monkey_cap
    try:
        ids = []
        for i in range(5):
            r = await agent.deep_research(f"Q{i}", max_iterations=1)
            ids.append(r.report_id)
        # 前两份应被淘汰
        assert agent.get_report(ids[0]) is None
        assert agent.get_report(ids[-1]) is not None
        assert len(agent._report_cache) == monkey_cap
    finally:
        mr._REPORT_CACHE_CAP = original


# ---------------------------------------------------------------------------
# next_questions 限深 (_MAX_NEXT_QUESTIONS_PER_STEP = 2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_next_questions_capped_per_step():
    """LLM 吐 5 个 next_questions，每步只入栈前 2 个。"""
    agent = MarketResearcherAgent(
        llm_callable=_llm_stub_with_next(["a", "b", "c", "d", "e"]),
    )
    report = await agent.deep_research("Q", max_iterations=1)
    assert len(report.steps[0].next_questions) <= 2


# ---------------------------------------------------------------------------
# parse_synth_response 容错
# ---------------------------------------------------------------------------


def test_parse_synth_response_extracts_json_in_text():
    raw = '前缀文本 ... {"summary": "S", "rationale": "R", "next_questions": ["x"]} 尾巴'
    parsed = MarketResearcherAgent._parse_synth_response(raw)
    assert parsed["summary"] == "S"
    assert parsed["rationale"] == "R"
    assert parsed["next_questions"] == ["x"]


def test_parse_synth_response_falls_back_to_summary():
    raw = "纯自然语言无 JSON"
    parsed = MarketResearcherAgent._parse_synth_response(raw)
    assert parsed["summary"] == "纯自然语言无 JSON"
    assert parsed["next_questions"] == []
