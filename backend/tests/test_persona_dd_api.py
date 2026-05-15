"""persona_dd 7 endpoint API 测试 (P9-D 尽调专家)。

⚠️ 设计说明：
v3/main 主 app 在 P6 fetch / P4 app_authorization 链上有 **预先存在**
的 import 损坏，与本 P9-D 工单无关。本测试用 **隔离 FastAPI app + 路由
mount + dep override** 直接挂载 P9-D 的 router，独立验证 7 endpoint 契约。

覆盖：
    POST /personas/dd/investigate-company
    POST /personas/dd/analyze-evidence
    POST /personas/dd/monitor-sentiment
    POST /personas/dd/relationship-graph
    POST /personas/dd/grade-risk
    GET  /personas/dd/reports
    GET  /personas/dd/reports/{report_id}
"""

from __future__ import annotations

import sys
import types
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

# JSONB → JSON for sqlite engine
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


# ---------------------------------------------------------------------------
# 临时 import shim：fetch / app_authorizations 链断裂时绕过
# ---------------------------------------------------------------------------
if "src.api.routes.fetch" not in sys.modules:
    _stub = types.ModuleType("src.api.routes.fetch")
    _stub.router = APIRouter()
    sys.modules["src.api.routes.fetch"] = _stub


from src.agents.personas.due_diligence_expert import DueDiligenceExpertPersona  # noqa: E402
from src.api.routes import persona_dd as persona_dd_module  # noqa: E402
from src.api.routes.persona_dd import router as persona_dd_router  # noqa: E402
from src.core.deps import get_current_user_required  # noqa: E402

BASE = "/personas/dd"


def _build_test_persona() -> DueDiligenceExpertPersona:
    """带 mock specialized agent + mock P6-C 源的 persona。"""
    dd_agent = SimpleNamespace(
        process=AsyncMock(
            return_value=SimpleNamespace(
                agent_name="dd",
                content="测试综合摘要",
                reasoning="",
                citations=[],
                actions=[],
                metadata={},
            )
        )
    )
    return DueDiligenceExpertPersona(
        dd_agent=dd_agent,
        evidence_agent=SimpleNamespace(),
        sentiment_agent=SimpleNamespace(),
    )


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    app = FastAPI()
    app.include_router(persona_dd_router, prefix="/personas/dd")

    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        email="dd@anxin.cn",
        role="user",
        organization_id=None,
    )

    async def _fake_user():
        return fake_user

    app.dependency_overrides[get_current_user_required] = _fake_user

    # 替换全局 agent，确保测试不发外网
    persona_dd_module.set_agent_for_test(_build_test_persona())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    persona_dd_module.set_agent_for_test(None)


# ---------------------------------------------------------------------------
# 1. investigate-company
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_investigate_company_endpoint(client):
    res = await client.post(
        f"{BASE}/investigate-company",
        json={"company_name": "测试科技有限公司", "depth": "quick"},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["target"] == "测试科技有限公司"
    assert data["target_type"] == "company"
    assert data["investigation_depth"] == "quick"
    assert data["report_id"].startswith("dd-")
    assert data["basic_info"] is not None
    assert "overall_risk_level" in data


@pytest.mark.asyncio
async def test_investigate_company_validates_input(client):
    res = await client.post(
        f"{BASE}/investigate-company", json={"company_name": "", "depth": "quick"}
    )
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# 2. analyze-evidence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_evidence_endpoint_supports(client):
    res = await client.post(
        f"{BASE}/analyze-evidence",
        json={
            "document_text": "本合同经双方签字盖章，乙方按时履约支付全部款项。",
            "claim": "乙方按时履约",
        },
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["claim"] == "乙方按时履约"
    assert data["supports_claim"] is True
    assert data["confidence"] >= 0
    assert isinstance(data["forgery_indicators"], list)


@pytest.mark.asyncio
async def test_analyze_evidence_endpoint_validates(client):
    res = await client.post(f"{BASE}/analyze-evidence", json={"document_text": "", "claim": ""})
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# 3. monitor-sentiment
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_monitor_sentiment_endpoint(client):
    res = await client.post(
        f"{BASE}/monitor-sentiment",
        json={"target": "ACME", "sources": ["weibo", "news"], "lookback_days": 30},
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["target"] == "ACME"
    assert "weibo" in data["by_source"]
    assert data["overall_sentiment"] in {"positive", "neutral", "negative", "mixed"}
    assert data["trend"] in {"improving", "stable", "deteriorating"}


# ---------------------------------------------------------------------------
# 4. relationship-graph
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_relationship_graph_endpoint(client):
    res = await client.post(f"{BASE}/relationship-graph", json={"entity": "TestCo", "depth": 2})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["root_entity"] == "TestCo"
    assert data["depth"] == 2
    assert len(data["nodes"]) >= 1
    # 第一个节点是 root
    assert data["nodes"][0]["name"] == "TestCo"
    # 边引用的节点都在 nodes 里
    node_ids = {n["id"] for n in data["nodes"]}
    for e in data["edges"]:
        assert e["from_id"] in node_ids and e["to_id"] in node_ids


@pytest.mark.asyncio
async def test_relationship_graph_validates_depth(client):
    res = await client.post(f"{BASE}/relationship-graph", json={"entity": "TestCo", "depth": 99})
    assert res.status_code == 422  # Field 上限 ≤ 3


# ---------------------------------------------------------------------------
# 5. grade-risk
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_grade_risk_via_report_id(client):
    # 先生成一个报告
    r1 = await client.post(
        f"{BASE}/investigate-company",
        json={"company_name": "评级公司", "depth": "quick"},
    )
    rid = r1.json()["report_id"]

    r2 = await client.post(f"{BASE}/grade-risk", json={"report_id": rid})
    assert r2.status_code == 200, r2.text
    data = r2.json()
    assert data["grade"] in {"AAA", "AA", "A", "BBB", "BB", "B", "C", "D"}
    assert 0 <= data["score"] <= 100
    assert data["recommended_action"] in {"trust", "verify_more", "monitor", "avoid"}


@pytest.mark.asyncio
async def test_grade_risk_unknown_report_returns_404(client):
    res = await client.post(f"{BASE}/grade-risk", json={"report_id": "dd-doesnotexist"})
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_grade_risk_requires_report_or_id(client):
    res = await client.post(f"{BASE}/grade-risk", json={})
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# 6. GET /reports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_reports_after_investigate(client):
    await client.post(
        f"{BASE}/investigate-company",
        json={"company_name": "列表公司A", "depth": "quick"},
    )
    await client.post(
        f"{BASE}/investigate-company",
        json={"company_name": "列表公司B", "depth": "quick"},
    )
    res = await client.get(f"{BASE}/reports")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 2

    # 按 target 过滤
    res2 = await client.get(f"{BASE}/reports?target=列表公司A")
    assert res2.status_code == 200
    items = res2.json()["items"]
    assert all("列表公司A" in it["target"] for it in items)


# ---------------------------------------------------------------------------
# 7. GET /reports/{id}
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_report_by_id(client):
    r1 = await client.post(
        f"{BASE}/investigate-company",
        json={"company_name": "单查公司", "depth": "quick"},
    )
    rid = r1.json()["report_id"]
    r2 = await client.get(f"{BASE}/reports/{rid}")
    assert r2.status_code == 200
    assert r2.json()["report_id"] == rid


@pytest.mark.asyncio
async def test_get_report_not_found(client):
    res = await client.get(f"{BASE}/reports/dd-missing")
    assert res.status_code == 404
