"""Unified capability policy engine regressions."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from src.models.agent_governance import AgentAuditEvent
from src.services.agent_approval_service import AgentApprovalService
from src.services.agent_governance_service import AgentGovernanceService
from src.services.capability_policy_engine import CapabilityPolicyEngine


@pytest.mark.asyncio
async def test_unified_capability_policy_allows_when_all_controls_pass(
    db_session,
    test_organization,
    test_admin,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="knowledge-search",
        route_type="knowledge",
        allowed_consumers=["worker-knowledge"],
        allowed_scopes=["knowledge:read"],
        risk_level="l2",
        policy={
            "required_feature": "knowledge_base",
            "allowed_roles": ["admin", "owner"],
            "required_permissions": ["knowledge:read"],
        },
    )

    decision = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="knowledge.search",
        actor_user_id=test_admin.id,
        actor_role="admin",
        permissions={"knowledge:read"},
        subscription_features={"knowledge_base": True},
        risk_level="l2",
        privacy_mode="hybrid",
        device_trusted=True,
        channel_policy={"allowed_actions": ["execute"]},
        route_key="knowledge-search",
    )

    audit = (
        await db_session.execute(
            select(AgentAuditEvent).where(AgentAuditEvent.id == decision.audit_event_id)
        )
    ).scalar_one()

    assert decision.allowed is True
    assert decision.reason_code == "allowed"
    assert decision.required_action is None
    assert audit.action == "capability_policy.evaluate"
    assert audit.status == "success"
    assert audit.resource_id == "knowledge.search"


@pytest.mark.asyncio
async def test_unified_capability_policy_fails_closed_for_missing_subscription_and_permission(
    db_session,
    test_organization,
    test_admin,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="browser-research",
        route_type="browser",
        allowed_consumers=["worker-browser"],
        allowed_scopes=["browser:read"],
        risk_level="l2",
        policy={
            "required_feature": "browser_automation",
            "required_permissions": ["browser:read"],
        },
    )
    engine = CapabilityPolicyEngine(db_session)

    missing_feature = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="browser.research",
        actor_user_id=test_admin.id,
        actor_role="admin",
        permissions={"browser:read"},
        subscription_features={"knowledge_base": True},
        route_key="browser-research",
    )
    missing_permission = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="browser.research",
        actor_user_id=test_admin.id,
        actor_role="admin",
        permissions=set(),
        subscription_features={"browser_automation": True},
        route_key="browser-research",
    )

    assert missing_feature.allowed is False
    assert missing_feature.reason_code == "missing_subscription_feature"
    assert missing_feature.required_action == "subscribe"
    assert missing_permission.allowed is False
    assert missing_permission.reason_code == "missing_permission"
    assert missing_permission.required_action == "contact_admin"


@pytest.mark.asyncio
async def test_unified_capability_policy_denies_top_secret_networked_or_external_scope(
    db_session,
    test_organization,
    test_admin,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="mcp-approved",
        route_type="mcp",
        allowed_consumers=["worker-mcp"],
        allowed_scopes=["mcp:call"],
        risk_level="l2",
    )

    decision = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="mcp.call",
        actor_user_id=test_admin.id,
        actor_role="admin",
        permissions={"mcp:call"},
        subscription_features={"all"},
        route_key="mcp-approved",
        privacy_mode="top_secret",
        data_scope="external",
    )

    assert decision.allowed is False
    assert decision.reason_code == "privacy_mode_denied"
    assert decision.required_action == "switch_mode"


@pytest.mark.asyncio
async def test_unified_capability_policy_requires_trusted_device_for_desktop_control(
    db_session,
    test_organization,
    test_admin,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="desktop-control",
        route_type="desktop-control",
        allowed_consumers=["worker-desktop"],
        allowed_scopes=["desktop:control"],
        risk_level="l2",
    )

    decision = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="desktop.status_probe",
        actor_user_id=test_admin.id,
        actor_role="admin",
        permissions={"desktop:control"},
        subscription_features={"all"},
        route_key="desktop-control",
        device_trusted=False,
    )

    assert decision.allowed is False
    assert decision.reason_code == "untrusted_device"
    assert decision.required_action == "pair_device"


@pytest.mark.asyncio
async def test_unified_capability_policy_respects_channel_policy(
    db_session,
    test_organization,
    test_admin,
):
    decision = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="knowledge.search",
        actor_user_id=test_admin.id,
        actor_role="admin",
        permissions={"knowledge:read"},
        subscription_features={"all"},
        channel_policy={"allowed_actions": ["view"]},
    )

    assert decision.allowed is False
    assert decision.reason_code == "channel_policy_denied"
    assert decision.required_action == "contact_admin"


@pytest.mark.asyncio
async def test_unified_capability_policy_requires_and_accepts_high_risk_approval(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    checked_at = datetime(2026, 5, 8, tzinfo=UTC)
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="desktop-high-risk",
        route_type="desktop-control",
        allowed_consumers=["worker-desktop"],
        allowed_scopes=["desktop:control"],
        risk_level="l4",
    )
    engine = CapabilityPolicyEngine(db_session)

    missing_approval = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="desktop.remote_command",
        actor_user_id=test_user.id,
        actor_role="employee",
        permissions={"desktop:control"},
        subscription_features={"all"},
        risk_level="l4",
        route_key="desktop-high-risk",
        device_trusted=True,
        now=checked_at,
    )

    approval_service = AgentApprovalService(db_session)
    requested = await approval_service.request_approval(
        org_id=test_organization.id,
        action_type="desktop.remote_command",
        risk_level="l4",
        requested_by=test_user.id,
        route_key="desktop-high-risk",
        expires_at=checked_at + timedelta(minutes=10),
        now=checked_at,
    )
    await approval_service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="admin",
        now=checked_at,
    )
    allowed = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="desktop.remote_command",
        actor_user_id=test_user.id,
        actor_role="employee",
        permissions={"desktop:control"},
        subscription_features={"all"},
        risk_level="l4",
        route_key="desktop-high-risk",
        device_trusted=True,
        approval_id=requested.approval_id,
        now=checked_at,
    )

    audit_reasons = (
        await db_session.execute(
            select(AgentAuditEvent)
            .where(AgentAuditEvent.org_id == test_organization.id)
            .order_by(AgentAuditEvent.created_at, AgentAuditEvent.id)
        )
    ).scalars().all()
    allowed_audit = (
        await db_session.execute(
            select(AgentAuditEvent).where(AgentAuditEvent.id == allowed.audit_event_id)
        )
    ).scalar_one()

    assert missing_approval.allowed is False
    assert missing_approval.reason_code == "approval_required"
    assert missing_approval.required_action == "request_approval"
    assert requested.allowed is True
    assert allowed.allowed is True
    assert allowed.reason_code == "allowed"
    assert "approval_required" in [event.reason_code for event in audit_reasons]
    assert allowed_audit.action == "capability_policy.evaluate"
    assert allowed_audit.reason_code == "allowed"
