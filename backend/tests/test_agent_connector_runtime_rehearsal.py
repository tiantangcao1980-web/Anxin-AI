"""Local approved connector rehearsal for enterprise Agent governance."""

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


class _ApprovedConnectorSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        self.calls.append((tool_name, arguments))
        return {
            "artifact_type": "approved_connector_call",
            "provider": "local-mock-mcp",
            "tool_name": tool_name,
            "argument_keys": sorted(arguments.keys()),
            "redacted": True,
        }


@pytest.mark.asyncio
async def test_approved_connector_rehearsal_allows_once_then_fails_closed_after_revocation(
    monkeypatch,
    db_session,
    test_organization,
):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "production")
    service = McpClientService()
    session = _ApprovedConnectorSession()
    service._sessions["approved-materials"] = session
    governance = AgentGovernanceService(db_session)
    actor_user_id = str(uuid4())

    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="approved-materials",
        route_type="mcp",
        provider="local-mock-mcp",
        risk_level="l2",
        allowed_consumers=["legal_advisor"],
        allowed_scopes=[MCP_TOOL_ROUTE_SCOPE],
        policy={"purpose": "release-rehearsal", "credential_secret": "[redacted]"},
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="approved-materials",
        consumer_id="legal_advisor",
        requested_scopes=[MCP_TOOL_ROUTE_SCOPE],
        actor_user_id=actor_user_id,
    )

    result = await service.call_tool(
        "approved-materials__collect_case_snapshot",
        {"case_id": "case-redacted", "fields": ["summary", "risk_flags"]},
        org_id=test_organization.id,
        route_token=issued.token,
        consumer_id="legal_advisor",
        actor_user_id=actor_user_id,
        db=db_session,
    )
    revoked = await governance.revoke_capability_route(
        org_id=test_organization.id,
        route_key="approved-materials",
        reason="release-rehearsal-complete",
        actor_user_id=actor_user_id,
    )

    with pytest.raises(McpRouteAuthorizationError, match="capability_route_revoked"):
        await service.call_tool(
            "approved-materials__collect_case_snapshot",
            {"case_id": "case-redacted", "fields": ["summary"]},
            org_id=test_organization.id,
            route_token=issued.token,
            consumer_id="legal_advisor",
            actor_user_id=actor_user_id,
            db=db_session,
        )

    audits = (
        (
            await db_session.execute(
                select(AgentAuditEvent)
                .where(AgentAuditEvent.org_id == test_organization.id)
                .order_by(AgentAuditEvent.created_at.asc(), AgentAuditEvent.id.asc())
            )
        )
        .scalars()
        .all()
    )
    reason_codes = [event.reason_code for event in audits]

    assert issued.allowed is True
    assert revoked.revoked is True
    assert revoked.revoked_lease_count == 1
    assert result == {
        "artifact_type": "approved_connector_call",
        "provider": "local-mock-mcp",
        "tool_name": "collect_case_snapshot",
        "argument_keys": ["case_id", "fields"],
        "redacted": True,
    }
    assert session.calls == [
        ("collect_case_snapshot", {"case_id": "case-redacted", "fields": ["summary", "risk_flags"]})
    ]
    assert {"issued", "allowed", "revoked", "capability_route_revoked"}.issubset(reason_codes)
    assert issued.token is not None
    assert issued.token not in repr([event.metadata_json for event in audits])
