"""P9-B: persona_legal 路由 6 endpoint API 测试。

覆盖：
    POST /api/v1/personas/legal/consult
    POST /api/v1/personas/legal/research
    POST /api/v1/personas/legal/assess-risk
    POST /api/v1/personas/legal/check-compliance
    GET  /api/v1/personas/legal/regulatory-updates
    GET  /api/v1/personas/legal/legal-basis-explain

鉴权：所有 endpoint 都要求登录用户（401/403 守卫）。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（与其它 API 测试保持一致）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):

    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from src.agents.base import AgentResponse
from src.agents.personas.legal_advisor import LegalAdvisorPersona
from src.api.routes import persona_legal as routes_legal

PREFIX = "/api/v1/personas/legal"


# ---------------------------------------------------------------------------
# Stub specialized agents（不调用真 LLM）
# ---------------------------------------------------------------------------
def _make_stub_agent() -> LegalAdvisorPersona:
    """构造一个 5 个 specialized agent 全部 mock 的 persona。"""
    advisor = AsyncMock()
    researcher = AsyncMock()
    risk = AsyncMock()
    compliance = AsyncMock()
    monitor = AsyncMock()

    # 默认返回值（每个 endpoint 测试可覆盖）
    advisor.process.return_value = AgentResponse(
        agent_name="法律顾问Agent",
        content=(
            "根据《劳动合同法》第46条规定，需要支付经济补偿。\n\n"
            "```json\n"
            '{"legal_basis":[{"source":"law:劳动合同法","article":"第46条",'
            '"title":"劳动合同法","confidence":0.9}],'
            '"related_topics":["经济补偿"],'
            '"suggested_actions":["保留劳动合同"],'
            '"confidence":0.85}\n'
            "```"
        ),
    )
    researcher.search_laws.return_value = {
        "keywords": ["x"],
        "results": "《个人信息保护法》第13条规定...",
        "agent": "法规研究Agent",
    }
    risk.process.return_value = AgentResponse(
        agent_name="风险评估Agent",
        content=(
            "高风险\n\n"
            "```json\n"
            '{"risk_level":"high","risk_factors":[{"factor":"未取得授权",'
            '"severity":"high","likelihood":"high","description":"违反PIPL"}],'
            '"mitigation_suggestions":["增加弹窗"],'
            '"regulatory_basis":[]}\n'
            "```"
        ),
    )
    compliance.process.return_value = AgentResponse(
        agent_name="合规审核Agent",
        content=(
            "partial\n\n"
            "```json\n"
            '{"overall_compliance":"partial","score":75.0,'
            '"issues":[{"clause":"第3条","regulation":"PIPL","severity":"high",'
            '"suggestion":"重写"}]}\n'
            "```"
        ),
    )
    monitor.process.return_value = AgentResponse(
        agent_name="监管监测Agent",
        content=(
            "## 最新法规\n\n"
            "```json\n"
            '{"updates":[{"title":"《劳动合同法》修订",'
            '"issuing_authority":"全国人大","issued_date":"2026-04-01",'
            '"summary":"加强保护","affected_domains":["劳动"]}]}\n'
            "```"
        ),
    )

    with patch("src.agents.base.get_llm_config_sync", return_value=None):
        instance = LegalAdvisorPersona(
            advisor=advisor,
            researcher=researcher,
            risk=risk,
            compliance=compliance,
            monitor=monitor,
        )
    return instance


@pytest_asyncio.fixture(autouse=True)
async def _inject_test_agent():
    agent = _make_stub_agent()
    routes_legal.set_agent_for_test(agent)
    yield agent
    routes_legal.set_agent_for_test(None)


# ---------------------------------------------------------------------------
# 1. POST /consult
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_consult_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/consult",
        json={"question": "劳动合同到期不续签需要赔偿吗"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona_id"] == "legal_advisor"
    assert "劳动合同到期" in body["question"]
    assert body["consultation_id"]
    # disclaimer 必须存在
    assert "不构成正式法律意见" in body["disclaimer"]
    assert len(body["legal_basis"]) >= 1


@pytest.mark.asyncio
async def test_consult_validates_empty_question(auth_client: AsyncClient) -> None:
    r = await auth_client.post(f"{PREFIX}/consult", json={"question": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_consult_with_context(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/consult",
        json={
            "question": "我可以拒绝加班吗",
            "context": {"role": "员工", "industry": "制造业"},
        },
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 2. POST /research
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_research_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/research",
        json={
            "keyword": "个人信息保护",
            "law_type": "law",
            "jurisdiction": "national",
            "limit": 10,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona_id"] == "legal_advisor"
    assert body["query"]["keyword"] == "个人信息保护"
    assert body["query"]["law_type"] == "law"
    assert body["total_found"] >= 1


@pytest.mark.asyncio
async def test_research_validates_empty_keyword(auth_client: AsyncClient) -> None:
    r = await auth_client.post(f"{PREFIX}/research", json={"keyword": ""})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_research_validates_limit_range(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/research",
        json={"keyword": "x", "limit": 1000},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 3. POST /assess-risk
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_assess_risk_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/assess-risk",
        json={
            "scenario": "上线一个用户画像产品",
            "jurisdiction": "中国大陆",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona_id"] == "legal_advisor"
    assert body["risk_level"] in {"low", "medium", "high", "critical"}
    assert body["risk_level"] == "high"
    assert body["jurisdiction"] == "中国大陆"
    assert len(body["risk_factors"]) >= 1
    assert "增加弹窗" in body["mitigation_suggestions"]


@pytest.mark.asyncio
async def test_assess_risk_validates_empty_scenario(auth_client: AsyncClient) -> None:
    r = await auth_client.post(f"{PREFIX}/assess-risk", json={"scenario": ""})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 4. POST /check-compliance
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_check_compliance_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/check-compliance",
        json={
            "document_text": "用户协议第一条……" * 30,
            "regulation_set": "PIPL",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona_id"] == "legal_advisor"
    assert body["regulation_set"] == "PIPL"
    assert body["overall_compliance"] in {"compliant", "partial", "non-compliant"}
    assert body["overall_compliance"] == "partial"
    assert body["score"] == pytest.approx(75.0)
    assert len(body["issues"]) == 1


@pytest.mark.asyncio
async def test_check_compliance_validates_empty_doc(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/check-compliance",
        json={"document_text": "", "regulation_set": "PIPL"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_check_compliance_validates_empty_regulation(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/check-compliance",
        json={"document_text": "abc", "regulation_set": ""},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# 5. GET /regulatory-updates
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_regulatory_updates_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/regulatory-updates",
        params={"domain": "劳动法", "since_days": 30},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["domain"] == "劳动法"
    assert body["since_days"] == 30
    assert body["total"] == 1
    assert len(body["updates"]) == 1
    assert body["updates"][0]["title"].startswith("《劳动合同法》")


@pytest.mark.asyncio
async def test_regulatory_updates_validates_since_days(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/regulatory-updates",
        params={"domain": "劳动法", "since_days": 0},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_regulatory_updates_default_since_days(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/regulatory-updates",
        params={"domain": "数据合规"},
    )
    assert r.status_code == 200
    assert r.json()["since_days"] == 30


# ---------------------------------------------------------------------------
# 6. GET /legal-basis-explain
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_legal_basis_explain_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/legal-basis-explain",
        params={"law_id": "劳动合同法#46"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["law_id"] == "劳动合同法#46"
    assert body["title"] == "劳动合同法"
    assert body["article"] == "第46条"
    assert body["explanation"]


@pytest.mark.asyncio
async def test_legal_basis_explain_without_article(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/legal-basis-explain",
        params={"law_id": "民法典"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "民法典"
    assert body["article"] == ""


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_consult_requires_auth(client: AsyncClient) -> None:
    r = await client.post(f"{PREFIX}/consult", json={"question": "x"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_research_requires_auth(client: AsyncClient) -> None:
    r = await client.post(f"{PREFIX}/research", json={"keyword": "x"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_assess_risk_requires_auth(client: AsyncClient) -> None:
    r = await client.post(f"{PREFIX}/assess-risk", json={"scenario": "x"})
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_check_compliance_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        f"{PREFIX}/check-compliance",
        json={"document_text": "x", "regulation_set": "PIPL"},
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_regulatory_updates_requires_auth(client: AsyncClient) -> None:
    r = await client.get(
        f"{PREFIX}/regulatory-updates",
        params={"domain": "劳动法"},
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_legal_basis_explain_requires_auth(client: AsyncClient) -> None:
    r = await client.get(
        f"{PREFIX}/legal-basis-explain",
        params={"law_id": "x"},
    )
    assert r.status_code in (401, 403)
