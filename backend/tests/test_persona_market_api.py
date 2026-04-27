# -*- coding: utf-8 -*-
"""P7-B: persona_market 路由 5 endpoint API 测试。

不依赖真 LLM —— 用 ``set_agent_for_test()`` 注入 stub agent。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（与其它 API 测试保持一致）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):
    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


import json

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.agents.personas.market_researcher import MarketResearcherAgent
from src.api.routes import persona_market as routes_market


def _stub_llm() -> callable:
    payload = {"summary": "stub-summary", "rationale": "stub", "next_questions": []}

    def _c(system: str, user: str) -> str:  # noqa: ARG001
        return json.dumps(payload, ensure_ascii=False)

    return _c


@pytest_asyncio.fixture(autouse=True)
async def _inject_test_agent():
    agent = MarketResearcherAgent(llm_callable=_stub_llm(), fetch_service=None)
    routes_market.set_agent_for_test(agent)
    yield agent
    routes_market.set_agent_for_test(None)


# ---------------------------------------------------------------------------
# investigate-company
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_investigate_company(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/personas/market/investigate-company",
        json={"company": "X 集团", "depth": 1},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona_id"] == "market_researcher"
    assert "X 集团" in body["question"]
    assert body["report_id"]
    assert isinstance(body["steps"], list)
    assert body["suggested_actions"]


@pytest.mark.asyncio
async def test_investigate_company_validates_input(auth_client: AsyncClient) -> None:
    # depth 越界
    r = await auth_client.post(
        "/api/v1/personas/market/investigate-company",
        json={"company": "X", "depth": 99},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# competitor-monitor
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_competitor_monitor(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/personas/market/competitor-monitor",
        json={"competitors": ["A", "B"], "aspects": ["产品"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] == 2
    assert set(body["items"].keys()) == {"A", "B"}
    for name, rep in body["items"].items():
        assert rep["persona_id"] == "market_researcher"
        assert name in rep["question"]


@pytest.mark.asyncio
async def test_competitor_monitor_requires_at_least_one(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/personas/market/competitor-monitor",
        json={"competitors": []},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# industry-trends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_industry_trends(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/personas/market/industry-trends",
        json={"industry": "新能源", "lookback_days": 30},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["industry"] == "新能源"
    assert body["lookback_days"] == 30
    assert "axes" in body
    assert set(body["axes"].keys()) == {"policy", "tech", "capital", "market"}
    assert body["report"]["persona_id"] == "market_researcher"


# ---------------------------------------------------------------------------
# deep-research
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deep_research(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/personas/market/deep-research",
        json={"question": "东南亚 EV 配件市场规模？", "max_iterations": 1},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["question"].startswith("东南亚")
    assert isinstance(body["citations"], list)
    assert len(body["steps"]) >= 1


@pytest.mark.asyncio
async def test_deep_research_validates_iterations(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        "/api/v1/personas/market/deep-research",
        json={"question": "X", "max_iterations": 0},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /research/{report_id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_research_after_deep_research(auth_client: AsyncClient) -> None:
    # 先创建一份
    r1 = await auth_client.post(
        "/api/v1/personas/market/deep-research",
        json={"question": "缓存一下", "max_iterations": 1},
    )
    assert r1.status_code == 200
    rid = r1.json()["report_id"]

    r2 = await auth_client.get(f"/api/v1/personas/market/research/{rid}")
    assert r2.status_code == 200
    assert r2.json()["report_id"] == rid


@pytest.mark.asyncio
async def test_get_research_404(auth_client: AsyncClient) -> None:
    r = await auth_client.get("/api/v1/personas/market/research/no-such-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoints_require_auth(client: AsyncClient) -> None:
    """未登录用户访问应被拒（401 / 403）。"""
    r = await client.post(
        "/api/v1/personas/market/deep-research",
        json={"question": "x", "max_iterations": 1},
    )
    assert r.status_code in (401, 403)
