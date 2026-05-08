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


@pytest.mark.asyncio
async def test_permission_regression_employee_browser_fill_is_rejected(
    db_session,
    test_organization,
    test_user,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="browser-fill",
        route_type="browser",
        allowed_consumers=["agent-browser"],
        allowed_scopes=["browser:write"],
        risk_level="l3",
        policy={
            "required_feature": "browser_automation",
            "allowed_roles": ["admin", "owner", "boss", "super_admin"],
            "required_permissions": ["browser:write"],
        },
    )

    decision = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="browser.fill_form",
        actor_user_id=test_user.id,
        actor_role="employee",
        permissions={"browser:write"},
        subscription_features={"browser_automation": True},
        route_key="browser-fill",
        device_trusted=True,
    )

    assert decision.allowed is False
    assert decision.reason_code == "role_not_allowed"
    assert decision.required_action == "contact_admin"


@pytest.mark.asyncio
async def test_permission_regression_department_admin_report_agent_is_allowed(
    db_session,
    test_organization,
    test_admin,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="department-report-agent",
        route_type="llm",
        allowed_consumers=["agent-report"],
        allowed_scopes=["report:generate"],
        risk_level="l2",
        policy={
            "required_feature": "management_reports",
            "allowed_roles": ["department_admin", "admin", "owner"],
            "required_permissions": ["org:read", "report:generate"],
        },
    )

    decision = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="agent.report.generate",
        actor_user_id=test_admin.id,
        actor_role="department_admin",
        permissions={"org:read", "report:generate"},
        subscription_features={"management_reports": True},
        route_key="department-report-agent",
        channel_policy={"allowed_actions": ["execute"]},
    )

    assert decision.allowed is True
    assert decision.reason_code == "allowed"


@pytest.mark.asyncio
async def test_permission_regression_boss_desktop_control_requires_approval_then_allows(
    db_session,
    test_organization,
    test_user,
    test_admin,
):
    checked_at = datetime(2026, 5, 8, tzinfo=UTC)
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="boss-desktop-control",
        route_type="desktop-control",
        allowed_consumers=["desktop-host"],
        allowed_scopes=["desktop:control"],
        risk_level="l4",
        policy={
            "required_feature": "remote_desktop_control",
            "allowed_roles": ["boss", "owner", "super_admin"],
            "required_permissions": ["desktop:control"],
        },
    )
    engine = CapabilityPolicyEngine(db_session)

    missing_approval = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="desktop.remote_command",
        actor_user_id=test_user.id,
        actor_role="boss",
        permissions={"desktop:control"},
        subscription_features={"remote_desktop_control": True},
        route_key="boss-desktop-control",
        device_trusted=True,
        now=checked_at,
    )

    approval_service = AgentApprovalService(db_session)
    requested = await approval_service.request_approval(
        org_id=test_organization.id,
        route_key="boss-desktop-control",
        action_type="desktop.remote_command",
        risk_level="l4",
        requested_by=test_user.id,
        expires_at=checked_at + timedelta(minutes=10),
        now=checked_at,
    )
    await approval_service.decide_approval(
        org_id=test_organization.id,
        approval_id=requested.approval_id,
        decision="approve",
        decided_by=test_admin.id,
        decider_role="boss",
        now=checked_at,
    )
    allowed = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="desktop.remote_command",
        actor_user_id=test_user.id,
        actor_role="boss",
        permissions={"desktop:control"},
        subscription_features={"remote_desktop_control": True},
        route_key="boss-desktop-control",
        device_trusted=True,
        approval_id=requested.approval_id,
        now=checked_at,
    )

    assert missing_approval.allowed is False
    assert missing_approval.reason_code == "approval_required"
    assert missing_approval.required_action == "request_approval"
    assert allowed.allowed is True
    assert allowed.reason_code == "allowed"


@pytest.mark.asyncio
async def test_permission_regression_super_admin_mcp_revocation_fails_next_call(
    db_session,
    test_organization,
    test_admin,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="super-admin-mcp",
        route_type="mcp",
        allowed_consumers=["worker-mcp"],
        allowed_scopes=["mcp:call"],
        risk_level="l2",
        policy={
            "required_feature": "approved_mcp_connectors",
            "allowed_roles": ["super_admin"],
            "required_permissions": ["mcp:call"],
        },
    )
    issued = await governance.issue_route_token(
        org_id=test_organization.id,
        route_key="super-admin-mcp",
        consumer_id="worker-mcp",
        requested_scopes=["mcp:call"],
    )

    before = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="mcp.call_tool",
        actor_user_id=test_admin.id,
        actor_role="super_admin",
        permissions={"mcp:call"},
        subscription_features={"approved_mcp_connectors": True},
        route_key="super-admin-mcp",
    )
    revocation = await governance.revoke_capability_route(
        org_id=test_organization.id,
        route_key="super-admin-mcp",
        reason="super_admin_disabled_connector",
        actor_user_id=test_admin.id,
    )
    route_denied = await CapabilityPolicyEngine(db_session).can_execute_capability(
        org_id=test_organization.id,
        capability_key="mcp.call_tool",
        actor_user_id=test_admin.id,
        actor_role="super_admin",
        permissions={"mcp:call"},
        subscription_features={"approved_mcp_connectors": True},
        route_key="super-admin-mcp",
    )
    token_denied = await governance.validate_route_token(
        org_id=test_organization.id,
        raw_token=issued.token,
        required_scope="mcp:call",
        consumer_id="worker-mcp",
    )

    assert before.allowed is True
    assert revocation.revoked is True
    assert route_denied.allowed is False
    assert route_denied.reason_code == "capability_route_revoked"
    assert token_denied.allowed is False
    assert token_denied.reason_code == "capability_route_revoked"


@pytest.mark.asyncio
async def test_permission_regression_external_provider_material_package_boundary(
    db_session,
    test_organization,
    test_admin,
):
    governance = AgentGovernanceService(db_session)
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="external-material-package",
        route_type="external-api",
        allowed_consumers=["provider-portal"],
        allowed_scopes=["material:package"],
        risk_level="l2",
        policy={
            "required_feature": "provider_material_package",
            "allowed_roles": ["external_provider", "lawyer", "tax_advisor"],
            "required_permissions": ["material:package"],
        },
    )
    await governance.create_capability_route(
        org_id=test_organization.id,
        route_key="raw-contract-export",
        route_type="external-api",
        allowed_consumers=["provider-portal"],
        allowed_scopes=["contract:export"],
        risk_level="l3",
        policy={
            "required_feature": "contract_export",
            "allowed_roles": ["admin", "owner", "boss", "super_admin"],
            "required_permissions": ["contract:export"],
        },
    )
    engine = CapabilityPolicyEngine(db_session)

    material_package = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="material.package.prepare",
        actor_user_id=test_admin.id,
        actor_role="external_provider",
        permissions={"material:package"},
        subscription_features={"provider_material_package": True},
        route_key="external-material-package",
        data_scope="external",
        privacy_mode="hybrid",
    )
    raw_export = await engine.can_execute_capability(
        org_id=test_organization.id,
        capability_key="contract.raw_export",
        actor_user_id=test_admin.id,
        actor_role="external_provider",
        permissions={"material:package"},
        subscription_features={"contract_export": True, "provider_material_package": True},
        route_key="raw-contract-export",
        data_scope="external",
        privacy_mode="hybrid",
    )

    assert material_package.allowed is True
    assert material_package.reason_code == "allowed"
    assert raw_export.allowed is False
    assert raw_export.reason_code == "role_not_allowed"
