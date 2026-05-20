"""Database-backed SkillGovernanceService regressions."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from src.models import (
    Organization,
    SkillConnectorConfig,
    SkillEnabledVersion,
    SkillGovernanceAuditEvent,
)
from src.services.skill_evolution_service import (
    REQUIRED_SKILL_EVAL_CHECKS,
    SkillEvolutionError,
    SkillEvolutionStatus,
)
from src.services.skill_governance_service import SkillGovernanceService


def passing_checks() -> dict[str, bool]:
    return dict.fromkeys(REQUIRED_SKILL_EVAL_CHECKS, True)


@pytest.mark.asyncio
async def test_skill_governance_proposal_persists_baseline_without_enabling_agent_version(
    db_session, test_organization
):
    service = SkillGovernanceService(db_session)

    proposal = await service.create_proposal(
        org_id=test_organization.id,
        skill_name="Contract Review",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="failed_case:case-1",
        created_by="agent-1",
        created_by_role="agent",
    )
    restarted = SkillGovernanceService(db_session)

    assert proposal.status == SkillEvolutionStatus.DRAFT.value
    assert await restarted.is_skill_enabled(
        org_id=test_organization.id,
        skill_name="contract review",
        version="1.0.0",
    )
    assert not await restarted.is_skill_enabled(
        org_id=test_organization.id,
        skill_name="contract review",
        version="1.1.0",
    )
    assert [
        event.reason_code for event in await restarted.get_audit_events(org_id=test_organization.id)
    ] == ["draft_created"]


@pytest.mark.asyncio
async def test_skill_governance_requires_required_eval_before_approval(
    db_session, test_organization
):
    service = SkillGovernanceService(db_session)
    proposal = await service.create_proposal(
        org_id=test_organization.id,
        skill_name="tax-risk",
        current_version="2.0.0",
        proposed_version="2.1.0",
        source="feedback:fb-1",
        created_by="agent-2",
        created_by_role="agent",
    )

    with pytest.raises(SkillEvolutionError, match="must pass required eval"):
        await service.approve(
            org_id=test_organization.id,
            proposal_id=proposal.id,
            approver="owner-1",
            approver_role="owner",
        )

    events = await service.get_audit_events(org_id=test_organization.id)
    assert events[-1].reason_code == "eval_not_passed"
    assert not await service.is_skill_enabled(
        org_id=test_organization.id, skill_name="tax-risk", version="2.1.0"
    )


@pytest.mark.asyncio
async def test_skill_governance_failed_eval_rejects_and_blocks_release(
    db_session, test_organization
):
    service = SkillGovernanceService(db_session)
    proposal = await service.create_proposal(
        org_id=test_organization.id,
        skill_name="external-mcp",
        proposed_version="0.1.0",
        source="agent_proposal:run-1",
        created_by="agent-3",
        created_by_role="agent",
        risk_level="high",
    )

    await service.record_eval(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        checks={
            "offline_eval": True,
            "permission_regression": False,
            "prompt_injection": True,
        },
        actor="eval-harness",
    )

    with pytest.raises(SkillEvolutionError, match="must pass required eval"):
        await service.approve(
            org_id=test_organization.id,
            proposal_id=proposal.id,
            approver="admin-1",
            approver_role="admin",
        )

    assert proposal.status == SkillEvolutionStatus.REJECTED.value
    assert not await service.is_skill_enabled(
        org_id=test_organization.id, skill_name="external-mcp", version="0.1.0"
    )


@pytest.mark.asyncio
async def test_skill_governance_release_persists_enabled_version_and_audit_after_restart(
    db_session, test_organization
):
    service = SkillGovernanceService(db_session)
    proposal = await service.create_proposal(
        org_id=test_organization.id,
        skill_name="labor-dispute",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="eval:nightly-42",
        created_by="agent-4",
        created_by_role="agent",
    )

    await service.record_eval(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        checks=passing_checks(),
        actor="eval-harness",
    )
    await service.approve(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        approver="admin-1",
        approver_role="org_admin",
    )
    await service.gray_release(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        percentage=25,
        actor="release-manager",
    )
    restarted = SkillGovernanceService(db_session)

    enabled = (
        await db_session.execute(
            select(SkillEnabledVersion).where(SkillEnabledVersion.org_id == test_organization.id)
        )
    ).scalar_one()
    audits = (
        (
            await db_session.execute(
                select(SkillGovernanceAuditEvent)
                .where(SkillGovernanceAuditEvent.org_id == test_organization.id)
                .order_by(SkillGovernanceAuditEvent.created_at)
            )
        )
        .scalars()
        .all()
    )

    assert proposal.status == SkillEvolutionStatus.GRAY_RELEASED.value
    assert proposal.gray_percentage == 25
    assert enabled.skill_name == "labor-dispute"
    assert enabled.version == "1.1.0"
    assert enabled.proposal_id == proposal.id
    assert await restarted.is_skill_enabled(
        org_id=test_organization.id,
        skill_name="labor-dispute",
        version="1.1.0",
    )
    assert not await restarted.is_skill_enabled(
        org_id=test_organization.id,
        skill_name="labor-dispute",
        version="1.0.0",
    )
    assert [event.reason_code for event in audits] == [
        "draft_created",
        "eval_passed",
        "approved",
        "gray_released",
    ]
    assert all("token" not in str(event.metadata_json).lower() for event in audits)


@pytest.mark.asyncio
async def test_skill_governance_rollback_reverts_enabled_version(db_session, test_organization):
    service = SkillGovernanceService(db_session)
    proposal = await service.create_proposal(
        org_id=test_organization.id,
        skill_name="contract-review",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="eval:nightly-43",
        created_by="agent-6",
        created_by_role="agent",
    )
    await service.record_eval(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        checks=passing_checks(),
        actor="eval-harness",
    )
    await service.approve(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        approver="super-admin-1",
        approver_role="super_admin",
    )
    await service.gray_release(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        percentage=100,
        actor="release-manager",
    )

    await service.rollback(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        reason="privacy regression",
        actor="owner-1",
    )

    assert proposal.status == SkillEvolutionStatus.ROLLED_BACK.value
    assert not await service.is_skill_enabled(
        org_id=test_organization.id, skill_name="contract-review", version="1.1.0"
    )
    assert await service.is_skill_enabled(
        org_id=test_organization.id, skill_name="contract-review", version="1.0.0"
    )
    assert (await service.get_audit_events(org_id=test_organization.id))[
        -1
    ].reason_code == "rolled_back"


@pytest.mark.asyncio
async def test_skill_governance_is_org_scoped(db_session, test_organization):
    other_org = Organization(id=str(uuid4()), name="Other Org")
    db_session.add(other_org)
    await db_session.flush()
    service = SkillGovernanceService(db_session)
    proposal = await service.create_proposal(
        org_id=test_organization.id,
        skill_name="contract-review",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="eval:nightly-44",
        created_by="agent-7",
        created_by_role="agent",
    )
    await service.record_eval(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        checks=passing_checks(),
        actor="eval-harness",
    )
    await service.approve(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        approver="owner-1",
        approver_role="owner",
    )
    await service.gray_release(
        org_id=test_organization.id,
        proposal_id=proposal.id,
        percentage=100,
        actor="release-manager",
    )

    with pytest.raises(SkillEvolutionError, match="not found"):
        await service.record_eval(
            org_id=other_org.id,
            proposal_id=proposal.id,
            checks=passing_checks(),
            actor="eval-harness",
        )

    assert not await service.is_skill_enabled(
        org_id=other_org.id, skill_name="contract-review", version="1.1.0"
    )


@pytest.mark.asyncio
async def test_skill_connector_config_encrypts_credentials_and_sanitizes_audit(
    db_session, test_organization
):
    service = SkillGovernanceService(db_session)

    config = await service.create_connector_config(
        org_id=test_organization.id,
        skill_name="Contract Review",
        connector_name="Court Data",
        connector_type="http_api",
        endpoint_url="https://court.example.test/api",
        auth_type="api_key",
        credentials={"API_KEY": "sk-secret-value", "CLIENT_SECRET": "client-secret-value"},
        is_enabled=True,
        actor="admin-1",
    )
    await db_session.commit()
    restarted = SkillGovernanceService(db_session)
    listed = await restarted.list_connector_configs(
        org_id=test_organization.id, skill_name="contract review"
    )
    audits = await restarted.get_audit_events(org_id=test_organization.id)

    assert listed[0].id == config.id
    assert sorted(listed[0].encrypted_fields) == ["API_KEY", "CLIENT_SECRET"]
    assert "sk-secret-value" not in str(listed[0].encrypted_fields)
    assert "client-secret-value" not in str(listed[0].encrypted_fields)
    assert audits[-1].reason_code == "connector_created"
    assert audits[-1].resource_snapshot["credential_keys"] == ["API_KEY", "CLIENT_SECRET"]
    assert "sk-secret-value" not in str(audits[-1].resource_snapshot)
    assert "client-secret-value" not in str(audits[-1].metadata_json)


@pytest.mark.asyncio
async def test_skill_connector_update_preserves_or_replaces_credentials(
    db_session, test_organization
):
    service = SkillGovernanceService(db_session)
    config = await service.create_connector_config(
        org_id=test_organization.id,
        skill_name="tax-risk",
        connector_name="tax-bureau",
        connector_type="http_api",
        endpoint_url="https://tax.example.test",
        auth_type="api_key",
        credentials={"API_KEY": "sk-original-secret"},
        is_enabled=True,
        actor="admin-1",
    )
    original_fields = dict(config.encrypted_fields)

    metadata_only = await service.update_connector_config(
        org_id=test_organization.id,
        connector_id=config.id,
        actor="admin-2",
        endpoint_url="https://tax.example.test/v2",
        is_enabled=False,
    )
    metadata_only_fields = dict(metadata_only.encrypted_fields)
    assert metadata_only_fields == original_fields
    assert metadata_only.endpoint_url == "https://tax.example.test/v2"
    assert metadata_only.is_enabled is False

    cleared_endpoint = await service.update_connector_config(
        org_id=test_organization.id,
        connector_id=config.id,
        actor="admin-2",
        endpoint_url=None,
        replace_endpoint_url=True,
    )
    assert cleared_endpoint.endpoint_url is None
    assert dict(cleared_endpoint.encrypted_fields) == original_fields

    replaced = await service.update_connector_config(
        org_id=test_organization.id,
        connector_id=config.id,
        actor="admin-2",
        credentials={"TOKEN": "replacement-token"},
        replace_credentials=True,
    )

    assert sorted(replaced.encrypted_fields) == ["TOKEN"]
    assert "replacement-token" not in str(replaced.encrypted_fields)


@pytest.mark.asyncio
async def test_skill_connector_update_rejects_duplicate_skill_connector_pair(
    db_session, test_organization
):
    service = SkillGovernanceService(db_session)
    first = await service.create_connector_config(
        org_id=test_organization.id,
        skill_name="tax-risk",
        connector_name="tax-bureau",
        connector_type="http_api",
        endpoint_url="https://tax.example.test",
        auth_type="api_key",
        credentials={"API_KEY": "sk-first-secret"},
        is_enabled=True,
        actor="admin-1",
    )
    second = await service.create_connector_config(
        org_id=test_organization.id,
        skill_name="tax-risk",
        connector_name="invoice-api",
        connector_type="http_api",
        endpoint_url="https://invoice.example.test",
        auth_type="api_key",
        credentials={"API_KEY": "sk-second-secret"},
        is_enabled=True,
        actor="admin-1",
    )

    with pytest.raises(SkillEvolutionError, match="already exists"):
        await service.update_connector_config(
            org_id=test_organization.id,
            connector_id=second.id,
            actor="admin-2",
            connector_name=first.connector_name,
        )

    assert second.connector_name == "invoice-api"


@pytest.mark.asyncio
async def test_skill_connector_config_is_org_scoped(db_session, test_organization):
    other_org = Organization(id=str(uuid4()), name="Other Org")
    db_session.add(other_org)
    await db_session.flush()
    service = SkillGovernanceService(db_session)
    config = await service.create_connector_config(
        org_id=test_organization.id,
        skill_name="labor-dispute",
        connector_name="labor-api",
        connector_type="http_api",
        endpoint_url="https://labor.example.test",
        auth_type="api_key",
        credentials={"API_KEY": "sk-labor-secret"},
        is_enabled=True,
        actor="admin-1",
    )

    assert await service.list_connector_configs(org_id=other_org.id) == []
    with pytest.raises(SkillEvolutionError, match="not found"):
        await service.update_connector_config(
            org_id=other_org.id,
            connector_id=config.id,
            actor="admin-2",
            is_enabled=False,
        )

    stored = (
        await db_session.execute(
            select(SkillConnectorConfig).where(SkillConnectorConfig.org_id == test_organization.id)
        )
    ).scalar_one()
    assert stored.id == config.id
