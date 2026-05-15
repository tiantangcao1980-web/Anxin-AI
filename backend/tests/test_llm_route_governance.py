"""LLM runtime route-token governance regressions."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.agents.base import (
    AgentConfig,
    AgentResponse,
    BaseLegalAgent,
    _task_llm_route_context_var,
)
from src.api.routes.chat import _extract_llm_route_credentials
from src.models import AgentAuditEvent
from src.services.agent_governance_service import AgentGovernanceService
from src.services.llm_route_governance import (
    DEFAULT_LLM_ROUTE_KEY,
    LLM_ROUTE_SCOPE,
    LLMRouteAuthorizationError,
    llm_route_consumer_for_user,
)
from src.services.rag_service import RAGContext, RAGService


class _RouteGuardAgent(BaseLegalAgent):
    def __init__(self) -> None:
        super().__init__(
            AgentConfig(
                name="route_guard_agent",
                role="Route guard",
                description="Route guard test agent",
                system_prompt="You are a route guard test agent.",
            )
        )

    async def process(self, task: dict) -> AgentResponse:
        return AgentResponse(agent_name=self.name, content=str(task.get("description", "")))


def _configured_agent(monkeypatch) -> _RouteGuardAgent:
    from src.services import mcp_client_service

    agent = _RouteGuardAgent()
    agent.llm_config = SimpleNamespace(
        api_key="sk-valid-test-key",
        api_base_url="https://llm.example.test/v1",
        model_name="gpt-test",
        provider="openai",
        temperature=0.7,
    )
    agent.model_name = "gpt-test"
    monkeypatch.setattr(
        mcp_client_service.mcp_client_service,
        "get_all_tools",
        AsyncMock(return_value=[]),
    )
    return agent


@pytest.mark.asyncio
async def test_llm_chat_requires_route_token_in_commercial_environment(monkeypatch):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(llm_route_governance.settings, "LLM_ROUTE_TOKEN_REQUIRED", False)
    agent = _configured_agent(monkeypatch)
    network_call = AsyncMock(
        side_effect=AssertionError("LLM network must not be called without route token")
    )
    monkeypatch.setattr(agent, "_call_llm_with_retry", network_call)

    result = await agent.chat("合同风险怎么判断")

    assert "LLM route token required" in result
    network_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_llm_chat_uses_db_backed_route_token(monkeypatch, db_session, test_organization):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")
    agent = _configured_agent(monkeypatch)
    network_call = AsyncMock(return_value={"choices": [{"message": {"content": "ok"}}]})
    monkeypatch.setattr(agent, "_call_llm_with_retry", network_call)
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key=DEFAULT_LLM_ROUTE_KEY,
        route_type="llm",
        allowed_consumers=["chat-worker"],
        allowed_scopes=[LLM_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key=DEFAULT_LLM_ROUTE_KEY,
        consumer_id="chat-worker",
        requested_scopes=[LLM_ROUTE_SCOPE],
    )

    result = await agent.chat(
        "合同风险怎么判断",
        llm_route_context={
            "db": db_session,
            "org_id": test_organization.id,
            "route_token": issued.token,
            "consumer_id": "chat-worker",
        },
    )
    audits = (
        (
            await db_session.execute(
                select(AgentAuditEvent).where(AgentAuditEvent.org_id == test_organization.id)
            )
        )
        .scalars()
        .all()
    )

    assert result == "ok"
    network_call.assert_awaited_once()
    assert [event.reason_code for event in audits] == ["issued", "allowed"]


@pytest.mark.asyncio
async def test_llm_chat_fails_after_route_revocation(monkeypatch, db_session, test_organization):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")
    agent = _configured_agent(monkeypatch)
    network_call = AsyncMock(
        side_effect=AssertionError("revoked route must fail before LLM network")
    )
    monkeypatch.setattr(agent, "_call_llm_with_retry", network_call)
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="revoked-llm",
        route_type="llm",
        allowed_consumers=["chat-worker"],
        allowed_scopes=[LLM_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="revoked-llm",
        consumer_id="chat-worker",
        requested_scopes=[LLM_ROUTE_SCOPE],
    )
    await governance.revoke_capability_route(
        org_id=test_organization.id,
        route_key="revoked-llm",
        reason="owner_revoked",
    )

    result = await agent.chat(
        "合同风险怎么判断",
        llm_route_context={
            "db": db_session,
            "org_id": test_organization.id,
            "route_token": issued.token,
            "consumer_id": "chat-worker",
        },
    )

    assert "capability_route_revoked" in result
    network_call.assert_not_awaited()


@pytest.mark.asyncio
async def test_llm_stream_chat_requires_route_token_before_network(monkeypatch):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "staging")
    agent = _configured_agent(monkeypatch)
    http_client = AsyncMock()
    http_client.post.side_effect = AssertionError(
        "streaming LLM network must not be called without route token"
    )
    monkeypatch.setattr(agent, "get_http_client", AsyncMock(return_value=http_client))

    queue = await agent.stream_chat("请流式回答")
    first = await queue.get()
    end = await queue.get()

    assert "LLM route token required" in str(first)
    assert end is None
    http_client.post.assert_not_called()


@pytest.mark.asyncio
async def test_llm_stream_chat_uses_task_route_context_var(
    monkeypatch,
    db_session,
    test_organization,
):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")
    agent = _configured_agent(monkeypatch)

    class _FakeStreamResponse:
        status_code = 200

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def aiter_lines(self):
            yield 'data: {"choices":[{"delta":{"content":"ok"}}]}'
            yield "data: [DONE]"

    class _FakeHttpClient:
        def __init__(self) -> None:
            self.stream_calls = 0

        def stream(self, *args, **kwargs):
            self.stream_calls += 1
            return _FakeStreamResponse()

    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="ws-llm",
        route_type="llm",
        allowed_consumers=["ws-chat"],
        allowed_scopes=[LLM_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="ws-llm",
        consumer_id="ws-chat",
        requested_scopes=[LLM_ROUTE_SCOPE],
    )
    http_client = _FakeHttpClient()
    monkeypatch.setattr(agent, "get_http_client", AsyncMock(return_value=http_client))

    token = _task_llm_route_context_var.set(
        {
            "db": db_session,
            "org_id": test_organization.id,
            "route_token": issued.token,
            "consumer_id": "ws-chat",
        }
    )
    try:
        queue = await agent.stream_chat("请流式回答")
        first = await queue.get()
        end = await queue.get()
    finally:
        _task_llm_route_context_var.reset(token)

    assert first == "ok"
    assert end is None
    assert http_client.stream_calls == 1


def test_websocket_llm_route_credentials_support_auth_headers_and_messages():
    auth_token, auth_consumer = _extract_llm_route_credentials(
        {"token": "access-token", "route_token": "route-auth"},
        {
            "capability_route_token": "route-a",
            "capability_consumer_id": "user:a",
        },
    )
    message_token, message_consumer = _extract_llm_route_credentials(
        {
            "X-Capability-Route-Token": "route-b",
            "X-Capability-Consumer-Id": "user:b",
        }
    )

    assert auth_token == "route-auth"
    assert auth_consumer == "user:a"
    assert message_token == "route-b"
    assert message_consumer == "user:b"


@pytest.mark.asyncio
async def test_chat_route_token_endpoint_issues_user_bound_token(
    monkeypatch,
    auth_client,
    db_session,
    test_user,
    test_organization,
):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")
    consumer_id = llm_route_consumer_for_user(str(test_user.id))
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key=DEFAULT_LLM_ROUTE_KEY,
        route_type="llm",
        allowed_consumers=[consumer_id],
        allowed_scopes=[LLM_ROUTE_SCOPE],
    )

    response = await auth_client.post("/api/v1/chat/route-token", json={})
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["required"] is True
    assert body["route_key"] == DEFAULT_LLM_ROUTE_KEY
    assert body["consumer_id"] == consumer_id
    assert body["scope"] == LLM_ROUTE_SCOPE
    assert body["route_token"].startswith("anxin_route_")


@pytest.mark.asyncio
async def test_authorize_llm_route_raises_typed_error(monkeypatch):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")

    with pytest.raises(LLMRouteAuthorizationError, match="missing consumer_id"):
        await llm_route_governance.authorize_llm_route(
            org_id="org-a",
            route_token="token-a",
            consumer_id=None,
            db=object(),  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_rag_generate_requires_route_token_before_direct_llm(monkeypatch):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")
    service = RAGService()
    create_call_count = 0

    def fake_create(**kwargs):
        nonlocal create_call_count
        create_call_count += 1
        raise AssertionError("RAG direct LLM must not be called without route token")

    service.llm_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(service, "_is_local_model_api", lambda: False)
    context = RAGContext(
        query="合同风险",
        retrieved_chunks=[],
        reranked_chunks=[],
        context_text="合同资料",
        sources=[],
    )

    answer, tokens_used = await service.generate("合同风险", context)

    assert "LLM route token required" in answer
    assert tokens_used == 0
    assert create_call_count == 0


@pytest.mark.asyncio
async def test_rag_generate_uses_db_backed_route_token(
    monkeypatch,
    db_session,
    test_organization,
):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")
    service = RAGService()
    create_call_count = 0

    def fake_create(**kwargs):
        nonlocal create_call_count
        create_call_count += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="rag-ok"))],
            usage=SimpleNamespace(total_tokens=7),
        )

    service.llm_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(service, "_is_local_model_api", lambda: False)
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="rag-llm",
        route_type="llm",
        allowed_consumers=["rag-worker"],
        allowed_scopes=[LLM_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="rag-llm",
        consumer_id="rag-worker",
        requested_scopes=[LLM_ROUTE_SCOPE],
    )
    context = RAGContext(
        query="合同风险",
        retrieved_chunks=[],
        reranked_chunks=[],
        context_text="合同资料",
        sources=[],
    )

    answer, tokens_used = await service.generate(
        "合同风险",
        context,
        llm_route_context={
            "db": db_session,
            "org_id": test_organization.id,
            "route_token": issued.token,
            "consumer_id": "rag-worker",
        },
    )

    assert answer == "rag-ok"
    assert tokens_used == 7
    assert create_call_count == 1


@pytest.mark.asyncio
async def test_rag_generate_fails_after_route_revocation(
    monkeypatch,
    db_session,
    test_organization,
):
    from src.services import llm_route_governance

    monkeypatch.setattr(llm_route_governance.settings, "ENVIRONMENT", "production")
    service = RAGService()
    create_call_count = 0

    def fake_create(**kwargs):
        nonlocal create_call_count
        create_call_count += 1
        raise AssertionError("revoked RAG route must fail before direct LLM call")

    service.llm_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create))
    )
    monkeypatch.setattr(service, "_is_local_model_api", lambda: False)
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="revoked-rag-llm",
        route_type="llm",
        allowed_consumers=["rag-worker"],
        allowed_scopes=[LLM_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="revoked-rag-llm",
        consumer_id="rag-worker",
        requested_scopes=[LLM_ROUTE_SCOPE],
    )
    await governance.revoke_capability_route(
        org_id=test_organization.id,
        route_key="revoked-rag-llm",
        reason="owner_revoked",
    )
    context = RAGContext(
        query="合同风险",
        retrieved_chunks=[],
        reranked_chunks=[],
        context_text="合同资料",
        sources=[],
    )

    answer, tokens_used = await service.generate(
        "合同风险",
        context,
        llm_route_context={
            "db": db_session,
            "org_id": test_organization.id,
            "route_token": issued.token,
            "consumer_id": "rag-worker",
        },
    )

    assert "capability_route_revoked" in answer
    assert tokens_used == 0
    assert create_call_count == 0
