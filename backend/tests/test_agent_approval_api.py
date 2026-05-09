"""AgentApproval API regressions for Human-in-the-loop governance."""

import pytest
from sqlalchemy import select

from src.models import AgentApproval, AgentAuditEvent, CapabilityRoute
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

    audit_response = await auth_client.get(f"/api/v1/agent-approvals/{approval_id}/audit-events")
    assert audit_response.status_code == 200
    audit_body = audit_response.json()
    assert audit_body["code"] == 200
    assert audit_body["data"]["total"] == 3
    assert [item["reason_code"] for item in audit_body["data"]["items"]] == ["allowed", "approved", "requested"]
    assert {item["resource_id"] for item in audit_body["data"]["items"]} == {approval_id}
    assert "should-never-leak" not in str(audit_body)

    export_response = await auth_client.get(f"/api/v1/agent-approvals/{approval_id}/audit-export")
    assert export_response.status_code == 200
    export_body = export_response.json()
    assert export_body["code"] == 200
    assert export_body["data"]["schema_version"] == "agent_approval_audit_export.v1"
    assert export_body["data"]["approval"]["id"] == approval_id
    assert export_body["data"]["approval"]["payload"]["api_key"] == "[redacted]"
    assert export_body["data"]["total"] == 3
    assert [item["reason_code"] for item in export_body["data"]["audit_events"]] == [
        "allowed",
        "approved",
        "requested",
    ]
    assert export_body["data"]["generated_at"]
    assert "should-never-leak" not in str(export_body)


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


@pytest.mark.asyncio
async def test_agent_approval_workspace_control_fails_closed_and_writes_audit(
    auth_client,
    admin_auth_client,
    db_session,
    test_organization,
):
    create = await auth_client.post(
        "/api/v1/agent-approvals",
        json={"action_type": "browser.remote_control", "risk_level": "l4"},
    )
    approval_id = create.json()["data"]["approval_id"]
    await admin_auth_client.post(f"/api/v1/agent-approvals/{approval_id}/approve", json={"note": "ok"})

    controlled = await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/workspace-control",
        json={"action": "pause", "reason": "operator paused a high-risk workspace"},
    )

    approval = (
        await db_session.execute(select(AgentApproval).where(AgentApproval.id == approval_id))
    ).scalar_one()
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert controlled.status_code == 200
    assert controlled.json()["code"] == 409
    assert controlled.json()["data"]["allowed"] is False
    assert controlled.json()["data"]["reason_code"] == "runtime_not_integrated"
    assert controlled.json()["data"]["status"] == "approved"
    assert approval.status == "approved"
    assert audits[-1].action == "agent_workspace.pause"
    assert audits[-1].status == "denied"
    assert audits[-1].reason_code == "runtime_not_integrated"


@pytest.mark.asyncio
async def test_agent_approval_workspace_control_accepts_local_runtime_rehearsal(
    auth_client,
    admin_auth_client,
    db_session,
    test_organization,
):
    create = await auth_client.post(
        "/api/v1/agent-approvals",
        json={
            "action_type": "browser.remote_control",
            "risk_level": "l4",
            "payload": {
                "workspace_runtime": {"mode": "local_rehearsal"},
                "api_key": "should-never-leak",
            },
        },
    )
    approval_id = create.json()["data"]["approval_id"]
    await admin_auth_client.post(f"/api/v1/agent-approvals/{approval_id}/approve", json={"note": "ok"})

    controlled = await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/workspace-control",
        json={"action": "takeover", "reason": "operator rehearses takeover"},
    )

    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()
    payload = controlled.json()["data"]

    assert controlled.status_code == 200
    assert controlled.json()["code"] == 200
    assert payload["allowed"] is True
    assert payload["reason_code"] == "takeover_accepted"
    assert payload["workspace_snapshot"]["runtime_control"]["mode"] == "local_rehearsal"
    assert payload["workspace_snapshot"]["runtime_control"]["external_side_effects"] is False
    assert payload["workspace_snapshot"]["runtime_controls"]["takeover"] == "available_local_rehearsal"
    assert audits[-1].action == "agent_workspace.takeover"
    assert audits[-1].status == "success"
    assert audits[-1].reason_code == "takeover_accepted"
    assert "should-never-leak" not in str(payload)
    assert "should-never-leak" not in str(audits)


@pytest.mark.asyncio
async def test_agent_approval_workspace_observe_returns_snapshot_and_writes_audit(
    auth_client,
    admin_auth_client,
    db_session,
    test_organization,
):
    create = await auth_client.post(
        "/api/v1/agent-approvals",
        json={"action_type": "browser.remote_control", "risk_level": "l4"},
    )
    approval_id = create.json()["data"]["approval_id"]
    await admin_auth_client.post(f"/api/v1/agent-approvals/{approval_id}/approve", json={"note": "ok"})
    await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/artifacts",
        json={
            "artifact_type": "summary",
            "title": "旁听摘要",
            "content": {
                "finding": "read-only snapshot",
                "api_key": "should-never-leak",
            },
            "metadata": {"source": "workspace", "raw_token": "never-store"},
        },
    )

    observed = await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/workspace-control",
        json={"action": "observe", "reason": "operator observes a high-risk workspace"},
    )

    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()
    payload = observed.json()["data"]

    assert observed.status_code == 200
    assert observed.json()["code"] == 200
    assert payload["allowed"] is True
    assert payload["reason_code"] == "observe_snapshot_ready"
    assert payload["workspace_snapshot"]["runtime_controls"]["observe"] == "available"
    assert payload["workspace_snapshot"]["runtime_controls"]["pause"] == "runtime_not_integrated"
    assert payload["workspace_snapshot"]["artifacts"][0]["title"] == "旁听摘要"
    assert payload["workspace_snapshot"]["artifacts"][0]["content"]["api_key"] == "[redacted]"
    assert payload["workspace_snapshot"]["audit_events"][0]["action"] == "agent_workspace.observe"
    assert audits[-1].action == "agent_workspace.observe"
    assert audits[-1].status == "success"
    assert audits[-1].reason_code == "observe_snapshot_ready"
    assert "should-never-leak" not in str(payload)
    assert "never-store" not in str(audits)


@pytest.mark.asyncio
async def test_agent_workspace_artifact_api_redacts_and_exports(
    auth_client,
    admin_auth_client,
    db_session,
    test_organization,
):
    create = await auth_client.post(
        "/api/v1/agent-approvals",
        json={"action_type": "browser.remote_control", "risk_level": "l4"},
    )
    approval_id = create.json()["data"]["approval_id"]

    pending_artifact = await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/artifacts",
        json={
            "artifact_type": "summary",
            "title": "未批准摘要",
            "content": {"finding": "pending"},
        },
    )
    await admin_auth_client.post(f"/api/v1/agent-approvals/{approval_id}/approve", json={"note": "ok"})
    employee_artifact = await auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/artifacts",
        json={
            "artifact_type": "summary",
            "title": "员工摘要",
            "content": {"finding": "not allowed"},
        },
    )
    created = await admin_auth_client.post(
        f"/api/v1/agent-approvals/{approval_id}/artifacts",
        json={
            "artifact_type": "summary",
            "title": "桌面远控摘要",
            "content": {
                "finding": "safe probe only",
                "api_key": "should-never-leak",
                "nested": {"client_secret": "also-secret", "safe": "ok"},
            },
            "metadata": {"source": "workspace", "raw_token": "never-store"},
        },
    )
    listed = await admin_auth_client.get(f"/api/v1/agent-approvals/{approval_id}/artifacts")
    exported = await admin_auth_client.get(f"/api/v1/agent-approvals/{approval_id}/artifacts/export")
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert pending_artifact.status_code == 200
    assert pending_artifact.json()["code"] == 400
    assert pending_artifact.json()["data"]["reason_code"] == "approval_not_approved"
    assert employee_artifact.status_code == 200
    assert employee_artifact.json()["code"] == 403
    assert employee_artifact.json()["data"]["reason_code"] == "approver_role_not_allowed"
    assert created.status_code == 200
    assert created.json()["code"] == 200
    assert created.json()["data"]["reason_code"] == "artifact_recorded"
    assert created.json()["data"]["artifact"]["content"]["api_key"] == "[redacted]"
    assert created.json()["data"]["artifact"]["content"]["nested"]["client_secret"] == "[redacted]"
    assert created.json()["data"]["artifact"]["metadata"]["raw_token"] == "[redacted]"
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] == 1
    assert listed.json()["data"]["items"][0]["title"] == "桌面远控摘要"
    assert exported.status_code == 200
    assert exported.json()["data"]["schema_version"] == "agent_workspace_artifacts_export.v1"
    assert exported.json()["data"]["total"] == 1
    assert exported.json()["data"]["artifacts"][0]["content"]["finding"] == "safe probe only"
    assert audits[-1].action == "agent_workspace.artifact.add"
    assert audits[-1].reason_code == "artifact_recorded"
    assert "should-never-leak" not in str(created.json())
    assert "also-secret" not in str(exported.json())
    assert "never-store" not in str(audits)


@pytest.mark.asyncio
async def test_capability_route_policy_api_is_admin_only_and_revokes_tokens(
    auth_client,
    admin_auth_client,
    db_session,
    test_organization,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="browser-fill",
        route_type="browser",
        allowed_consumers=["browser-worker"],
        allowed_scopes=["browser:fill"],
        risk_level="l3",
        status="enabled",
        policy={"requires_approval": True},
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="browser-fill",
        consumer_id="browser-worker",
        requested_scopes=["browser:fill"],
    )

    employee_update = await auth_client.patch(
        "/api/v1/agent-approvals/capability-routes/browser-fill",
        json={"status": "disabled"},
    )
    admin_list = await admin_auth_client.get("/api/v1/agent-approvals/capability-routes")
    admin_update = await admin_auth_client.patch(
        "/api/v1/agent-approvals/capability-routes/browser-fill",
        json={
            "status": "disabled",
            "allowed_consumers": ["owner-agent"],
            "allowed_scopes": ["browser:fill", "browser:read"],
            "policy": {
                "required_feature": "browser_automation",
                "secret_token": "should-never-leak",
            },
        },
    )
    after = await governance.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="browser:fill",
        consumer_id="browser-worker",
    )
    route = (
        await db_session.execute(
            select(CapabilityRoute).where(
                CapabilityRoute.org_id == test_organization.id,
                CapabilityRoute.route_key == "browser-fill",
            )
        )
    ).scalar_one()

    assert employee_update.status_code == 200
    assert employee_update.json()["code"] == 403
    assert admin_list.status_code == 200
    assert admin_list.json()["data"]["total"] == 1
    assert admin_list.json()["data"]["items"][0]["route_key"] == "browser-fill"
    assert admin_update.status_code == 200
    assert admin_update.json()["code"] == 200
    assert admin_update.json()["data"]["revoked_lease_count"] == 1
    assert admin_update.json()["data"]["route"]["status"] == "disabled"
    assert admin_update.json()["data"]["route"]["policy"]["secret_token"] == "[redacted]"
    assert route.allowed_consumers == ["owner-agent"]
    assert route.allowed_scopes == ["browser:fill", "browser:read"]
    assert after.allowed is False
    assert after.reason_code == "capability_route_disabled"
    assert "should-never-leak" not in str(admin_update.json())
