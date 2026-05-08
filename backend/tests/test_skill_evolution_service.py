"""Skill Evolution Gate regressions."""

import pytest

from src.services.skill_evolution_service import (
    REQUIRED_SKILL_EVAL_CHECKS,
    SkillEvolutionError,
    SkillEvolutionService,
    SkillEvolutionStatus,
)


def passing_checks() -> dict[str, bool]:
    return dict.fromkeys(REQUIRED_SKILL_EVAL_CHECKS, True)


def test_agent_proposal_stays_draft_and_does_not_enable_proposed_version():
    service = SkillEvolutionService()

    proposal = service.create_proposal(
        skill_name="Contract Review",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="failed_case:case-1",
        created_by="agent-1",
        created_by_role="agent",
    )

    assert proposal.status == SkillEvolutionStatus.DRAFT
    assert service.is_skill_enabled("contract review", "1.0.0") is True
    assert service.is_skill_enabled("contract review", "1.1.0") is False
    assert [event.reason_code for event in service.get_audit_events()] == ["draft_created"]


def test_approval_before_required_eval_is_denied_and_audited():
    service = SkillEvolutionService()
    proposal = service.create_proposal(
        skill_name="tax-risk",
        current_version="2.0.0",
        proposed_version="2.1.0",
        source="feedback:fb-1",
        created_by="agent-2",
        created_by_role="agent",
    )

    with pytest.raises(SkillEvolutionError, match="must pass required eval"):
        service.approve(
            proposal.proposal_id,
            approver="owner-1",
            approver_role="owner",
        )

    assert service.is_skill_enabled("tax-risk", "2.1.0") is False
    assert service.get_audit_events()[-1].reason_code == "eval_not_passed"


def test_failing_eval_rejects_proposal_and_blocks_approval():
    service = SkillEvolutionService()
    proposal = service.create_proposal(
        skill_name="external-mcp",
        current_version=None,
        proposed_version="0.1.0",
        source="agent_proposal:run-1",
        created_by="agent-3",
        created_by_role="agent",
        risk_level="high",
    )

    service.record_eval(
        proposal.proposal_id,
        {
            "offline_eval": True,
            "permission_regression": False,
            "prompt_injection": True,
        },
        actor="eval-harness",
    )

    with pytest.raises(SkillEvolutionError, match="must pass required eval"):
        service.approve(
            proposal.proposal_id,
            approver="admin-1",
            approver_role="admin",
        )

    assert proposal.status == SkillEvolutionStatus.REJECTED
    assert service.is_skill_enabled("external-mcp", "0.1.0") is False


def test_authorized_approval_and_gray_release_enable_exact_proposed_version():
    service = SkillEvolutionService()
    proposal = service.create_proposal(
        skill_name="labor-dispute",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="eval:nightly-42",
        created_by="agent-4",
        created_by_role="agent",
    )

    service.record_eval(
        proposal.proposal_id,
        passing_checks(),
        actor="eval-harness",
    )
    assert proposal.status == SkillEvolutionStatus.EVALUATED

    approved = service.approve(
        proposal.proposal_id,
        approver="admin-1",
        approver_role="org_admin",
    )
    assert approved.status == SkillEvolutionStatus.APPROVED

    released = service.gray_release(
        proposal.proposal_id,
        percentage=25,
        actor="release-manager",
    )

    assert released.status == SkillEvolutionStatus.GRAY_RELEASED
    assert released.gray_percentage == 25
    assert service.is_skill_enabled("labor-dispute", "1.1.0") is True
    assert service.is_skill_enabled("labor-dispute", "1.0.0") is False
    assert [event.reason_code for event in service.get_audit_events()] == [
        "draft_created",
        "eval_passed",
        "approved",
        "gray_released",
    ]


def test_unauthorized_approver_and_invalid_gray_release_fail_closed():
    service = SkillEvolutionService()
    proposal = service.create_proposal(
        skill_name="browser-automation",
        current_version="3.0.0",
        proposed_version="3.1.0",
        source="incident:inc-1",
        created_by="agent-5",
        created_by_role="agent",
    )
    service.record_eval(proposal.proposal_id, passing_checks(), actor="eval-harness")

    with pytest.raises(SkillEvolutionError, match="not authorized"):
        service.approve(
            proposal.proposal_id,
            approver="lawyer-1",
            approver_role="lawyer",
        )

    service.approve(
        proposal.proposal_id,
        approver="owner-1",
        approver_role="owner",
    )
    with pytest.raises(SkillEvolutionError, match="between 1 and 100"):
        service.gray_release(
            proposal.proposal_id,
            percentage=0,
            actor="release-manager",
        )

    assert service.is_skill_enabled("browser-automation", "3.1.0") is False
    assert service.get_audit_events()[-1].reason_code == "invalid_gray_percentage"


def test_rollback_immediately_reverts_enabled_version_and_audits():
    service = SkillEvolutionService()
    proposal = service.create_proposal(
        skill_name="contract-review",
        current_version="1.0.0",
        proposed_version="1.1.0",
        source="eval:nightly-43",
        created_by="agent-6",
        created_by_role="agent",
    )
    service.record_eval(proposal.proposal_id, passing_checks(), actor="eval-harness")
    service.approve(
        proposal.proposal_id,
        approver="super-admin-1",
        approver_role="super_admin",
    )
    service.gray_release(
        proposal.proposal_id,
        percentage=100,
        actor="release-manager",
    )

    service.rollback(
        proposal.proposal_id,
        reason="privacy regression",
        actor="owner-1",
    )

    assert proposal.status == SkillEvolutionStatus.ROLLED_BACK
    assert service.is_skill_enabled("contract-review", "1.1.0") is False
    assert service.is_skill_enabled("contract-review", "1.0.0") is True
    assert service.get_audit_events()[-1].reason_code == "rolled_back"
