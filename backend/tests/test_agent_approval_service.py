"""DB-backed AgentApproval service regressions."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.models import AgentApproval, AgentAuditEvent
from src.services.agent_approval_service import AgentApprovalService
from src.services.agent_governance_service import AgentGovernanceService


@pytest.mark.asyncio
async def test_request_approval_persists_sanitized_payload_and_audit(db_session, test_organization, test_user):
    governance = AgentGovernanceService(db_session)
    route = await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="high-risk-browser",
        route_type="browser",
        allowed_consumers=["worker-1"],
        allowed_scopes=["browser:write"],
        risk_level="l4",
    )
    service = AgentApprovalService(db_session)

    requested = await service.request_approval(
        org_id=test_organization.id,
        route_key="high-risk-browser",
        action_type="browser.fill_form",
        risk_level="l4",
        requested_by=test_user.id,
        payload={
            "business_reason": "fill annual report",
            "raw_token": "secret-token",
            "nested": {"api_key": "secret-key", "safe": "value"},
        },
    )

    approval = (
        await db_session.execute(select(AgentApproval).where(AgentApproval.id == requested.approval_id))
    ).scalar_one()
    audits = (
        await db_session.execute(select(AgentAuditEvent).where(AgentAuditEvent.org_id == test_organization.id))
    ).scalars().all()

    assert requested.allowed is True
    assert requested.reason_code == "requested"
    assert requested.approval_id == approval.id
    assert approval.route_id == route.id
    assert approval.status == "pending"
    assert approval.payload == {
        "business_reason": "fill annual report",
        "raw_token": "[redacted]",
        "nested": {"api_key": "[redacted]", "safe": "value"},
    }
    assert audits[-1].action == "agent_approval.request"
    assert audits[-1].reason_code == "requested"
    assert "secret-token" not in str(audits[-1].metadata_json)
    assert "secret-key" not in str(audits[-1].resource_snapshot)


@pytest.mark.asyncio
async def test_decide_approval_requires_authorized_role_and_keeps_denied_pending(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        action_type="desktop.remote_command",
        risk_level="l4",
        requested_by=test_user.id,
    )

    denied = await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_user.id,
        decider_role="employee",
    )
    approved = await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
        note="desktop operator confirmed",
    )

    approval = (
        await db_session.execute(select(AgentApproval).where(AgentApproval.id == requested.approval_id))
    ).scalar_one()
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert denied.allowed is False
    assert denied.reason_code == "approver_role_not_allowed"
    assert approved.allowed is True
    assert approved.status == "approved"
    assert approval.status == "approved"
    assert approval.decided_by == test_admin.id
    assert [event.reason_code for event in audits] == [
        "requested",
        "approver_role_not_allowed",
        "approved",
    ]


@pytest.mark.asyncio
async def test_validate_approval_requires_approved_action_and_route(db_session, test_organization, test_user, test_admin):
    governance = AgentGovernanceService(db_session)
    route = await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="approved-mcp",
        route_type="mcp",
        allowed_consumers=["worker-1"],
        allowed_scopes=["mcp:call"],
        risk_level="l3",
    )
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        route_key="approved-mcp",
        action_type="mcp.call_tool",
        risk_level="l3",
        requested_by=test_user.id,
    )

    before = await service.validate_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action_type="mcp.call_tool",
        route_key="approved-mcp",
    )
    await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
    )
    wrong_action = await service.validate_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action_type="mcp.delete_tool",
        route_key="approved-mcp",
    )
    allowed = await service.validate_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action_type="mcp.call_tool",
        route_id=route.id,
    )

    assert before.allowed is False
    assert before.reason_code == "approval_not_approved"
    assert wrong_action.allowed is False
    assert wrong_action.reason_code == "approval_action_mismatch"
    assert allowed.allowed is True
    assert allowed.reason_code == "allowed"


@pytest.mark.asyncio
async def test_expired_approval_fails_closed_and_marks_status(db_session, test_organization, test_user, test_admin):
    issued_at = datetime(2026, 5, 8, tzinfo=UTC)
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        action_type="skill.enable_high_risk",
        risk_level="l3",
        requested_by=test_user.id,
        expires_at=issued_at + timedelta(minutes=5),
        now=issued_at,
    )
    await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
        now=issued_at + timedelta(minutes=1),
    )

    expired = await service.validate_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action_type="skill.enable_high_risk",
        now=issued_at + timedelta(minutes=6),
    )

    approval = (
        await db_session.execute(select(AgentApproval).where(AgentApproval.id == requested.approval_id))
    ).scalar_one()

    assert expired.allowed is False
    assert expired.reason_code == "approval_expired"
    assert approval.status == "expired"
    assert approval.resolved_at.replace(tzinfo=UTC) == issued_at + timedelta(minutes=6)


@pytest.mark.asyncio
async def test_revoked_approval_fails_closed_after_previous_approval(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        action_type="desktop.remote_command",
        risk_level="l4",
        requested_by=test_user.id,
    )
    await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
    )
    before = await service.validate_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action_type="desktop.remote_command",
    )
    revoked = await service.revoke_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        revoked_by=test_admin.id,
        revoker_role="admin",
        reason="owner stopped the task",
    )
    after = await service.validate_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action_type="desktop.remote_command",
    )

    assert before.allowed is True
    assert revoked.allowed is True
    assert revoked.status == "revoked"
    assert after.allowed is False
    assert after.reason_code == "approval_revoked"


@pytest.mark.asyncio
async def test_workspace_control_requires_approved_approval(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        action_type="browser.remote_control",
        risk_level="l4",
        requested_by=test_user.id,
    )

    controlled = await service.control_workspace(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action="takeover",
        actor_user_id=test_admin.id,
        actor_role="admin",
        reason="operator tried to take over before approval",
    )

    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert controlled.allowed is False
    assert controlled.reason_code == "approval_not_approved"
    assert controlled.status == "pending"
    assert audits[-1].action == "agent_workspace.takeover"
    assert audits[-1].status == "denied"
    assert audits[-1].reason_code == "approval_not_approved"
    assert audits[-1].metadata_json["workspace_control"] == "takeover"


@pytest.mark.asyncio
async def test_workspace_control_fails_closed_until_runtime_is_integrated(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        action_type="browser.remote_control",
        risk_level="l4",
        requested_by=test_user.id,
    )
    await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
    )

    controlled = await service.control_workspace(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action="pause",
        actor_user_id=test_admin.id,
        actor_role="admin",
        reason="owner paused live desktop work",
    )

    approval = (
        await db_session.execute(select(AgentApproval).where(AgentApproval.id == requested.approval_id))
    ).scalar_one()
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert controlled.allowed is False
    assert controlled.reason_code == "runtime_not_integrated"
    assert controlled.status == "approved"
    assert approval.status == "approved"
    assert audits[-1].action == "agent_workspace.pause"
    assert audits[-1].status == "denied"
    assert audits[-1].reason_code == "runtime_not_integrated"
    assert audits[-1].metadata_json == {
        "actor_role": "admin",
        "workspace_control": "pause",
        "reason_present": "true",
    }


@pytest.mark.asyncio
async def test_workspace_observe_returns_read_only_snapshot_and_writes_audit(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        action_type="browser.remote_control",
        risk_level="l4",
        requested_by=test_user.id,
    )
    await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
    )
    await service.add_workspace_artifact(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        artifact_type="summary",
        title="旁听摘要",
        content={
            "finding": "safe probe only",
            "api_key": "should-never-leak",
            "nested": {"client_secret": "also-secret", "safe": "ok"},
        },
        metadata={"source": "workspace", "raw_token": "never-store"},
        actor_user_id=test_admin.id,
        actor_role="admin",
    )

    observed = await service.control_workspace(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        action="observe",
        actor_user_id=test_admin.id,
        actor_role="admin",
        reason="owner observes high-risk work",
    )

    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert observed.allowed is True
    assert observed.reason_code == "observe_snapshot_ready"
    assert observed.status == "approved"
    assert observed.workspace_snapshot is not None
    assert observed.workspace_snapshot["runtime_controls"] == {
        "observe": "available",
        "pause": "runtime_not_integrated",
        "takeover": "runtime_not_integrated",
        "terminate": "runtime_not_integrated",
    }
    assert observed.workspace_snapshot["artifacts"][0]["title"] == "旁听摘要"
    assert observed.workspace_snapshot["artifacts"][0]["content"]["api_key"] == "[redacted]"
    assert observed.workspace_snapshot["artifacts"][0]["content"]["nested"]["client_secret"] == "[redacted]"
    assert observed.workspace_snapshot["audit_events"][0]["action"] == "agent_workspace.observe"
    assert observed.workspace_snapshot["observe_audit_event_id"] == observed.audit_event_id
    assert audits[-1].action == "agent_workspace.observe"
    assert audits[-1].status == "success"
    assert audits[-1].reason_code == "observe_snapshot_ready"
    assert audits[-1].metadata_json["workspace_control"] == "observe"
    assert audits[-1].metadata_json["runtime_control_state"] == "read_only_snapshot"
    assert "should-never-leak" not in str(observed.workspace_snapshot)
    assert "never-store" not in str(audits)


@pytest.mark.asyncio
async def test_workspace_artifacts_require_approved_workspace_and_redact_payload(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    service = AgentApprovalService(db_session)
    requested = await service.request_approval(
        org_id=test_organization.id,
        action_type="browser.remote_control",
        risk_level="l4",
        requested_by=test_user.id,
    )

    before_approval = await service.add_workspace_artifact(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        artifact_type="summary",
        title="执行摘要",
        content={"finding": "pending"},
        actor_user_id=test_admin.id,
        actor_role="admin",
    )
    await service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
    )
    employee_denied = await service.add_workspace_artifact(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        artifact_type="summary",
        title="员工摘要",
        content={"finding": "not allowed"},
        actor_user_id=test_user.id,
        actor_role="employee",
    )
    recorded = await service.add_workspace_artifact(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        artifact_type="summary",
        title="高风险操作摘要",
        content={
            "finding": "仅生成可审计摘要",
            "api_key": "should-never-persist",
            "nested": {"client_secret": "also-secret", "safe": "ok"},
        },
        metadata={"source": "workspace", "raw_token": "do-not-store"},
        actor_user_id=test_admin.id,
        actor_role="admin",
    )
    artifacts = await service.list_workspace_artifacts(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
    )
    audits = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at)
        )
    ).scalars().all()

    assert before_approval.allowed is False
    assert before_approval.reason_code == "approval_not_approved"
    assert employee_denied.allowed is False
    assert employee_denied.reason_code == "approver_role_not_allowed"
    assert recorded.allowed is True
    assert recorded.reason_code == "artifact_recorded"
    assert recorded.artifact is not None
    assert recorded.artifact.content == {
        "finding": "仅生成可审计摘要",
        "api_key": "[redacted]",
        "nested": {"client_secret": "[redacted]", "safe": "ok"},
    }
    assert recorded.artifact.metadata == {"source": "workspace", "raw_token": "[redacted]"}
    assert len(artifacts) == 1
    assert artifacts[0].title == "高风险操作摘要"
    assert audits[-1].action == "agent_workspace.artifact.add"
    assert audits[-1].status == "success"
    assert audits[-1].reason_code == "artifact_recorded"
    assert "should-never-persist" not in str(audits)
    assert "do-not-store" not in str(audits)
