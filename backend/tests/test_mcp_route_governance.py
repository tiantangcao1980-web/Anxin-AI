"""MCP tool execution route-token governance regressions."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from src.models import AgentAuditEvent
from src.services.agent_governance_service import AgentGovernanceService
from src.services.mcp_client_service import (
    MCP_TOOL_ROUTE_SCOPE,
    McpClientService,
    McpRouteAuthorizationError,
)


class _FakeMcpSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        self.calls.append((tool_name, arguments))
        return {"tool_name": tool_name, "arguments": arguments}


def _service_with_session() -> tuple[McpClientService, _FakeMcpSession]:
    service = McpClientService()
    session = _FakeMcpSession()
    service._sessions["trusted"] = session
    return service, session


@pytest.mark.asyncio
async def test_mcp_tool_call_keeps_existing_dev_path_without_route_token(monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_TOOL_ROUTE_TOKEN_REQUIRED", False)
    service, session = _service_with_session()

    result = await service.call_tool("trusted__search", {"q": "合同风险"})

    assert result == {"tool_name": "search", "arguments": {"q": "合同风险"}}
    assert session.calls == [("search", {"q": "合同风险"})]


@pytest.mark.asyncio
async def test_mcp_tool_call_requires_route_token_in_commercial_environment(monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_TOOL_ROUTE_TOKEN_REQUIRED", False)
    service, session = _service_with_session()

    with pytest.raises(McpRouteAuthorizationError, match="MCP route token required"):
        await service.call_tool("trusted__search", {"q": "合同风险"})

    assert session.calls == []


@pytest.mark.asyncio
async def test_mcp_tool_call_uses_db_backed_route_token(monkeypatch, db_session, test_organization):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    service, session = _service_with_session()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="trusted",
        route_type="mcp",
        allowed_consumers=["legal_advisor"],
        allowed_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="trusted",
        consumer_id="legal_advisor",
        requested_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )

    result = await service.call_tool(
        "trusted__search",
        {"q": "合同风险"},
        org_id=test_organization.id,
        route_token=issued.token,
        consumer_id="legal_advisor",
        actor_user_id=str(uuid4()),
        db=db_session,
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

    assert result == {"tool_name": "search", "arguments": {"q": "合同风险"}}
    assert session.calls == [("search", {"q": "合同风险"})]
    assert [event.reason_code for event in audits] == ["issued", "allowed"]


@pytest.mark.asyncio
async def test_mcp_tool_call_rejects_route_token_for_different_connector(
    monkeypatch,
    db_session,
    test_organization,
):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    service, session = _service_with_session()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="other-connector",
        route_type="mcp",
        allowed_consumers=["legal_advisor"],
        allowed_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="other-connector",
        consumer_id="legal_advisor",
        requested_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )

    with pytest.raises(McpRouteAuthorizationError, match="capability_route_mismatch"):
        await service.call_tool(
            "trusted__search",
            {"q": "合同风险"},
            org_id=test_organization.id,
            route_token=issued.token,
            consumer_id="legal_advisor",
            db=db_session,
        )

    assert session.calls == []


@pytest.mark.asyncio
async def test_mcp_tool_call_fails_closed_after_route_revocation(
    monkeypatch, db_session, test_organization
):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "production")
    service, session = _service_with_session()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="trusted",
        route_type="mcp",
        allowed_consumers=["legal_advisor"],
        allowed_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="trusted",
        consumer_id="legal_advisor",
        requested_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )
    await governance.revoke_capability_route(
        org_id=test_organization.id,
        route_key="trusted",
        reason="owner_revoked",
    )

    with pytest.raises(McpRouteAuthorizationError, match="capability_route_revoked"):
        await service.call_tool(
            "trusted__search",
            {"q": "合同风险"},
            org_id=test_organization.id,
            route_token=issued.token,
            consumer_id="legal_advisor",
            db=db_session,
        )

    assert session.calls == []


@pytest.mark.asyncio
async def test_mcp_tool_call_enforces_route_token_consumer(
    monkeypatch, db_session, test_organization
):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_TOOL_ROUTE_TOKEN_REQUIRED", True)
    service, session = _service_with_session()
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="trusted",
        route_type="mcp",
        allowed_consumers=["legal_advisor"],
        allowed_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="trusted",
        consumer_id="legal_advisor",
        requested_scopes=[MCP_TOOL_ROUTE_SCOPE],
    )

    with pytest.raises(McpRouteAuthorizationError, match="route_token_consumer_mismatch"):
        await service.call_tool(
            "trusted__search",
            {"q": "合同风险"},
            org_id=test_organization.id,
            route_token=issued.token,
            consumer_id="risk_assessor",
            db=db_session,
        )

    assert session.calls == []
