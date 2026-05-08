"""AgentApproval API regressions for Human-in-the-loop governance."""

import pytest
from sqlalchemy import select

from src.models import AgentApproval, AgentAuditEvent
from src.services.agent_governance_service import AgentGovernanceService


@pytest.mark.asyncio
async def test_agent_approval_api_requires_auth(client):
    response = await client.post(
        "/api/v1/agent-approvals",
        json={"action_type": "desktop.remote_command", "risk_level": "l4"},
    )

    assert response.status_code in {401, 403}


@pytest.mark.asyncio
async def test_agent_approval_api_create_approve_validate_round_trip(
    auth_client,
    admin_auth_client,
    db_session,
    test_organization,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="api-approved-mcp",
        route_type="mcp",
        allowed_consumers=["worker-1"],
        allowed_scopes=["mcp:call"],
        risk_level="l3",
    )

    create = await auth_client.post(
        "/api/v1/agent-approvals",
        json={
            "action_type": "mcp.call_tool",
            "risk_level": "l3",
            "route_key": "api-approved-mcp",
            "payload": {
                "business_reason": "run approved connector",
                "api_key": "should-never-leak",
            },
        },
    )

    assert create.status_code == 200
    created_body = create.json()
    assert created_body["code"] == 200
    approval_id = created_body["data"]["approval_id"]

    approval = (
        await db_session.execute(select(AgentApproval).where(AgentApproval.id == approval_id))
    ).scalar_one()
    assert approval.payload == {
        "business_reason": "run approved connector",
        "api_key": "[redacted]",
    }

    own_list = await auth_client.get("/api/v1/agent-approvals")
    assert own_list.status_code == 200
    listed_items = own_list.json()["data"]["items"]
    listed_approval = next(item for item in listed_items if item["id"] == approval_id)
    assert listed_approval["payload"]["api_key"] == "[redacted]"

    pending_count = await admin_auth_client.get("/api/v1/agent-approvals/pending/count")
    assert pending_count.status_code == 200
    assert pending_count.json()["data"]["pending"] == 1

    approved = await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/approve",
        json={"note": "owner approved the connector call"},
    )
    assert approved.status_code == 200
    assert approved.json()["code"] == 200
    assert approved.json()["data"]["status"] == "approved"

    validated = await auth_client.post(
        "/api/v1/agent-approvals/validate",
        json={
            "approval_id": approval_id,
            "action_type": "mcp.call_tool",
            "route_key": "api-approved-mcp",
        },
    )
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert validated.status_code == 200
    assert validated.json()["code"] == 200
    assert validated.json()["data"]["allowed"] is True
    assert [event.reason_code for event in audits] == ["requested", "approved", "allowed"]
    assert "should-never-leak" not in str(audits)


@pytest.mark.asyncio
async def test_agent_approval_api_employee_cannot_decide_and_status_remains_pending(
    auth_client,
    db_session,
):
    create = await auth_client.post(
        "/api/v1/agent-approvals",
        json={"action_type": "desktop.remote_command", "risk_level": "l4"},
    )
    approval_id = create.json()["data"]["approval_id"]

    forbidden = await auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/approve",
        json={"note": "self approve"},
    )

    approval = (
        await db_session.execute(select(AgentApproval).where(AgentApproval.id == approval_id))
    ).scalar_one()

    assert forbidden.status_code == 200
    assert forbidden.json()["code"] == 403
    assert forbidden.json()["data"]["reason_code"] == "approver_role_not_allowed"
    assert approval.status == "pending"


@pytest.mark.asyncio
async def test_agent_approval_api_revocation_blocks_later_validation(
    auth_client,
    admin_auth_client,
    db_session,
):
    create = await auth_client.post(
        "/api/v1/agent-approvals",
        json={"action_type": "skill.enable_high_risk", "risk_level": "l3"},
    )
    approval_id = create.json()["data"]["approval_id"]
    await admin_auth_client.post(f"/api/v1/agent-approvals/{approval_id}/approve", json={"note": "ok"})

    revoked = await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/revoke",
        json={"reason": "owner stopped the task"},
    )
    after = await auth_client.post(
        "/api/v1/agent-approvals/validate",
        json={
            "approval_id": approval_id,
            "action_type": "skill.enable_high_risk",
        },
    )

    assert revoked.status_code == 200
    assert revoked.json()["code"] == 200
    assert after.status_code == 200
    assert after.json()["code"] == 400
    assert after.json()["data"]["reason_code"] == "approval_revoked"
