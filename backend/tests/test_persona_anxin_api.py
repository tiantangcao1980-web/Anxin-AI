"""P9-A: persona_anxin 路由 5 endpoint API 测试。

不依赖真 LLM —— 用 ``set_agent_for_test()`` 注入测试 agent，
其内部 ``chat`` 已被 monkeypatch 成可预期 stub。
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

from src.agents.personas import AnxinAssistantAgent, PersonaRegistry
from src.api.routes import persona_anxin as routes_anxin


@pytest_asyncio.fixture
async def _inject_test_agent():
    """构造 stub agent 并注入到路由层。

    注意：本 fixture 不动 ``PersonaRegistry``（避免影响其它 test 的 autoload 缓存），
    只把 anxin agent 自己 stub 掉。
    """
    with patch("src.agents.base.get_llm_config_sync", return_value=None):
        agent = AnxinAssistantAgent()
    # 让任何 chat() 调用直接返回固定文本
    agent.chat = AsyncMock(return_value="stub-llm-response")  # type: ignore[assignment]
    routes_anxin.set_agent_for_test(agent)
    yield agent
    routes_anxin.set_agent_for_test(None)


# ---------------------------------------------------------------------------
# classify-intent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_intent_fast_path(auth_client: AsyncClient, _inject_test_agent) -> None:
    r = await auth_client.post(
        "/api/v1/personas/anxin/classify-intent",
        json={"message": "帮我起草一份采购合同"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["primary_intent"] == "contract_steward"
    assert "contract_steward" in body["target_personas"]
    assert body["classifier"] == "fast_path"
    assert body["confidence"] >= 0.6


@pytest.mark.asyncio
async def test_classify_intent_validates_input(
    auth_client: AsyncClient, _inject_test_agent
) -> None:
    r = await auth_client.post(
        "/api/v1/personas/anxin/classify-intent",
        json={"message": ""},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# route
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_route(auth_client: AsyncClient, _inject_test_agent) -> None:
    intent_payload = {
        "primary_intent": "contract_steward",
        "target_personas": ["contract_steward", "operations_manager"],
        "confidence": 0.8,
        "reasoning": "x",
    }
    r = await auth_client.post(
        "/api/v1/personas/anxin/route",
        json={"intent": intent_payload, "context": {"user_message": "起草然后审批"}},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["primary_persona"] == "contract_steward"
    assert "operations_manager" in body["supporting_personas"]
    assert body["execution_mode"] in ("sequential", "parallel", "branching")


# ---------------------------------------------------------------------------
# decompose
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_decompose(auth_client: AsyncClient, _inject_test_agent) -> None:
    r = await auth_client.post(
        "/api/v1/personas/anxin/decompose",
        json={"task": "帮我起草合同 并 调研对方公司"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan_id"]
    assert len(body["subtasks"]) >= 2
    assert body["execution_mode"] in ("sequential", "parallel", "branching")


@pytest.mark.asyncio
async def test_decompose_validates(auth_client: AsyncClient, _inject_test_agent) -> None:
    r = await auth_client.post(
        "/api/v1/personas/anxin/decompose",
        json={"task": ""},
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# orchestrate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_orchestrate_empty_plan(auth_client: AsyncClient, _inject_test_agent) -> None:
    """空 plan → status=ok，subtask_results 空。"""
    r = await auth_client.post(
        "/api/v1/personas/anxin/orchestrate",
        json={
            "plan": {
                "plan_id": "p1",
                "user_query": "noop",
                "subtasks": [],
                "execution_mode": "sequential",
            }
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "ok"
    assert body["subtask_results"] == {}
    assert body["plan"]["plan_id"] == "p1"


@pytest.mark.asyncio
async def test_orchestrate_persona_missing_partial(
    auth_client: AsyncClient, _inject_test_agent
) -> None:
    """目标 persona 未注册 → subtask failed，整体 status=failed（仅 1 个 subtask 全部失败）。

    清空 registry 然后只放 anxin_assistant，确保 market_researcher 不在。
    """
    # 强制让 market_researcher 不在 registry 中
    registry = PersonaRegistry.instance()
    registry.unregister("market_researcher")

    r = await auth_client.post(
        "/api/v1/personas/anxin/orchestrate",
        json={
            "plan": {
                "plan_id": "p2",
                "user_query": "调研",
                "subtasks": [
                    {
                        "task_id": "s1",
                        "description": "调研",
                        "assigned_persona": "market_researcher",
                        "depends_on": [],
                        "inputs": {"task": "调研"},
                        "expected_output": "report",
                    }
                ],
                "execution_mode": "sequential",
            }
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # market_researcher 不可达 → 该 subtask failed
    assert "s1" in body["failed_subtasks"]
    assert body["subtask_results"]["s1"]["status"] == "failed"
    assert body["status"] in ("failed", "partial")
    # final_summary 应给出转人工建议或失败描述
    assert body["final_summary"]


# ---------------------------------------------------------------------------
# guide
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_guide(auth_client: AsyncClient, _inject_test_agent) -> None:
    r = await auth_client.post(
        "/api/v1/personas/anxin/guide",
        json={"vague_query": "我有点焦虑"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["suggested_personas"]) == 3
    assert body["follow_up_questions"]
    assert body["quick_actions"]
    assert body["message"]


@pytest.mark.asyncio
async def test_guide_fast_path(auth_client: AsyncClient, _inject_test_agent) -> None:
    r = await auth_client.post(
        "/api/v1/personas/anxin/guide",
        json={"vague_query": "可以帮我看看合同吗"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    persona_ids = [s["persona_id"] for s in body["suggested_personas"]]
    assert "contract_steward" in persona_ids


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_endpoints_require_auth(client: AsyncClient) -> None:
    """未登录用户访问应被拒（401 / 403）。"""
    r = await client.post(
        "/api/v1/personas/anxin/classify-intent",
        json={"message": "x"},
    )
    assert r.status_code in (401, 403)
