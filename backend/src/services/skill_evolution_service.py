"""Governed Skill evolution lifecycle controls.

Agents may propose skill changes, but production enablement stays behind
evaluation, human approval, gray release, rollback, and audit events.
This first implementation is intentionally local and dependency-free so the
commercial readiness gate can lock the fail-closed semantics before a durable
database model is added.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum

AUTHORIZED_SKILL_APPROVER_ROLES = frozenset({
    "owner",
    "boss",
    "super_admin",
    "org_admin",
    "admin",
})

REQUIRED_SKILL_EVAL_CHECKS = frozenset({
    "offline_eval",
    "permission_regression",
    "prompt_injection",
    "privacy_mode",
    "audit_log",
})


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


class SkillEvolutionStatus(str, Enum):
    DRAFT = "draft"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    GRAY_RELEASED = "gray_released"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


class SkillEvolutionError(ValueError):
    """Raised when a skill evolution transition is not allowed."""


@dataclass(frozen=True)
class SkillEvolutionAuditEvent:
    event_id: str
    action: str
    proposal_id: str
    skill_name: str
    status: SkillEvolutionStatus
    actor: str
    reason_code: str
    created_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class SkillEvolutionProposal:
    proposal_id: str
    skill_name: str
    current_version: str | None
    proposed_version: str
    source: str
    created_by: str
    created_by_role: str
    risk_level: str
    status: SkillEvolutionStatus
    created_at: datetime
    eval_results: dict[str, bool] = field(default_factory=dict)
    approved_by: str | None = None
    approver_role: str | None = None
    approved_at: datetime | None = None
    gray_percentage: int | None = None
    released_at: datetime | None = None
    rolled_back_at: datetime | None = None
    rollback_reason: str | None = None


class SkillEvolutionService:
    """Fail-closed gate for Skill self-improvement and release."""

    def __init__(self) -> None:
        self._proposals: dict[str, SkillEvolutionProposal] = {}
        self._enabled_versions: dict[str, str] = {}
        self._audit_log: list[SkillEvolutionAuditEvent] = []
        self._max_audit = 3000

    def create_proposal(
        self,
        *,
        skill_name: str,
        proposed_version: str,
        source: str,
        created_by: str,
        created_by_role: str,
        current_version: str | None = None,
        risk_level: str = "medium",
        now: datetime | None = None,
    ) -> SkillEvolutionProposal:
        skill_name = _normalize(skill_name)
        proposed_version = (proposed_version or "").strip()
        source = (source or "").strip()
        created_by = (created_by or "").strip()
        created_by_role = _normalize(created_by_role)
        normalized_current = (current_version or "").strip() or None

        if not skill_name:
            raise SkillEvolutionError("skill_name is required")
        if not proposed_version:
            raise SkillEvolutionError("proposed_version is required")
        if normalized_current and normalized_current == proposed_version:
            raise SkillEvolutionError("proposed_version must differ from current_version")
        if not source:
            raise SkillEvolutionError("source is required")
        if not created_by:
            raise SkillEvolutionError("created_by is required")

        created_at = now or _now()
        proposal = SkillEvolutionProposal(
            proposal_id=f"skill_evo_{uuid.uuid4().hex}",
            skill_name=skill_name,
            current_version=normalized_current,
            proposed_version=proposed_version,
            source=source,
            created_by=created_by,
            created_by_role=created_by_role,
            risk_level=_normalize(risk_level) or "medium",
            status=SkillEvolutionStatus.DRAFT,
            created_at=created_at,
        )
        self._proposals[proposal.proposal_id] = proposal
        if normalized_current and skill_name not in self._enabled_versions:
            self._enabled_versions[skill_name] = normalized_current
        self._audit(
            action="skill_evolution.proposal.create",
            proposal=proposal,
            actor=created_by,
            reason_code="draft_created",
            metadata={"created_by_role": created_by_role},
            now=created_at,
        )
        return proposal

    def record_eval(
        self,
        proposal_id: str,
        checks: dict[str, bool],
        *,
        actor: str,
        now: datetime | None = None,
    ) -> SkillEvolutionProposal:
        proposal = self._get(proposal_id)
        checked_at = now or _now()
        normalized_checks = {
            _normalize(name): bool(passed)
            for name, passed in checks.items()
            if _normalize(name)
        }
        if not normalized_checks:
            raise SkillEvolutionError("at least one eval check is required")
        if proposal.status not in {SkillEvolutionStatus.DRAFT, SkillEvolutionStatus.EVALUATED, SkillEvolutionStatus.REJECTED}:
            self._audit(
                action="skill_evolution.eval.deny",
                proposal=proposal,
                actor=actor,
                reason_code="eval_transition_denied",
                metadata={"proposal_status": proposal.status.value},
                now=checked_at,
            )
            raise SkillEvolutionError(f"cannot record eval when proposal is {proposal.status.value}")

        proposal.eval_results = normalized_checks
        missing = REQUIRED_SKILL_EVAL_CHECKS - set(normalized_checks)
        failed = {name for name, passed in normalized_checks.items() if not passed}
        if missing or failed:
            proposal.status = SkillEvolutionStatus.REJECTED
            self._audit(
                action="skill_evolution.eval.record",
                proposal=proposal,
                actor=actor,
                reason_code="eval_failed",
                metadata={
                    "missing": ",".join(sorted(missing)),
                    "failed": ",".join(sorted(failed)),
                },
                now=checked_at,
            )
            return proposal

        proposal.status = SkillEvolutionStatus.EVALUATED
        self._audit(
            action="skill_evolution.eval.record",
            proposal=proposal,
            actor=actor,
            reason_code="eval_passed",
            metadata={"check_count": str(len(normalized_checks))},
            now=checked_at,
        )
        return proposal

    def approve(
        self,
        proposal_id: str,
        *,
        approver: str,
        approver_role: str,
        now: datetime | None = None,
    ) -> SkillEvolutionProposal:
        proposal = self._get(proposal_id)
        approved_at = now or _now()
        role = _normalize(approver_role)
        if role not in AUTHORIZED_SKILL_APPROVER_ROLES:
            self._audit(
                action="skill_evolution.approval.deny",
                proposal=proposal,
                actor=approver,
                reason_code="unauthorized_approver",
                metadata={"approver_role": role},
                now=approved_at,
            )
            raise SkillEvolutionError("approver role is not authorized for skill evolution")
        if proposal.status != SkillEvolutionStatus.EVALUATED or not self._eval_complete(proposal):
            self._audit(
                action="skill_evolution.approval.deny",
                proposal=proposal,
                actor=approver,
                reason_code="eval_not_passed",
                metadata={"proposal_status": proposal.status.value},
                now=approved_at,
            )
            raise SkillEvolutionError("skill evolution proposal must pass required eval checks before approval")

        proposal.status = SkillEvolutionStatus.APPROVED
        proposal.approved_by = approver
        proposal.approver_role = role
        proposal.approved_at = approved_at
        self._audit(
            action="skill_evolution.approval.approve",
            proposal=proposal,
            actor=approver,
            reason_code="approved",
            metadata={"approver_role": role},
            now=approved_at,
        )
        return proposal

    def gray_release(
        self,
        proposal_id: str,
        *,
        percentage: int,
        actor: str,
        now: datetime | None = None,
    ) -> SkillEvolutionProposal:
        proposal = self._get(proposal_id)
        released_at = now or _now()
        if proposal.status != SkillEvolutionStatus.APPROVED:
            self._audit(
                action="skill_evolution.release.deny",
                proposal=proposal,
                actor=actor,
                reason_code="approval_required",
                metadata={"proposal_status": proposal.status.value},
                now=released_at,
            )
            raise SkillEvolutionError("skill evolution proposal must be approved before gray release")
        if percentage < 1 or percentage > 100:
            self._audit(
                action="skill_evolution.release.deny",
                proposal=proposal,
                actor=actor,
                reason_code="invalid_gray_percentage",
                metadata={"percentage": str(percentage)},
                now=released_at,
            )
            raise SkillEvolutionError("gray release percentage must be between 1 and 100")

        proposal.status = SkillEvolutionStatus.GRAY_RELEASED
        proposal.gray_percentage = percentage
        proposal.released_at = released_at
        self._enabled_versions[proposal.skill_name] = proposal.proposed_version
        self._audit(
            action="skill_evolution.release.gray",
            proposal=proposal,
            actor=actor,
            reason_code="gray_released",
            metadata={"percentage": str(percentage)},
            now=released_at,
        )
        return proposal

    def rollback(
        self,
        proposal_id: str,
        *,
        reason: str,
        actor: str,
        now: datetime | None = None,
    ) -> SkillEvolutionProposal:
        proposal = self._get(proposal_id)
        rolled_back_at = now or _now()
        if proposal.status not in {
            SkillEvolutionStatus.APPROVED,
            SkillEvolutionStatus.GRAY_RELEASED,
            SkillEvolutionStatus.ROLLED_BACK,
        }:
            self._audit(
                action="skill_evolution.release.rollback_deny",
                proposal=proposal,
                actor=actor,
                reason_code="rollback_not_allowed",
                metadata={"proposal_status": proposal.status.value},
                now=rolled_back_at,
            )
            raise SkillEvolutionError("only approved or released skill evolution proposals can be rolled back")

        proposal.status = SkillEvolutionStatus.ROLLED_BACK
        proposal.rolled_back_at = rolled_back_at
        proposal.rollback_reason = (reason or "").strip() or "rollback"
        if proposal.current_version:
            self._enabled_versions[proposal.skill_name] = proposal.current_version
        else:
            self._enabled_versions.pop(proposal.skill_name, None)
        self._audit(
            action="skill_evolution.release.rollback",
            proposal=proposal,
            actor=actor,
            reason_code="rolled_back",
            metadata={"reason": proposal.rollback_reason},
            now=rolled_back_at,
        )
        return proposal

    def is_skill_enabled(self, skill_name: str, version: str | None = None) -> bool:
        enabled_version = self._enabled_versions.get(_normalize(skill_name))
        if not enabled_version:
            return False
        return version is None or enabled_version == (version or "").strip()

    def get_enabled_version(self, skill_name: str) -> str | None:
        return self._enabled_versions.get(_normalize(skill_name))

    def get_proposal(self, proposal_id: str) -> SkillEvolutionProposal | None:
        return self._proposals.get(proposal_id)

    def get_audit_events(self, limit: int = 100) -> list[SkillEvolutionAuditEvent]:
        if limit <= 0:
            return []
        return list(self._audit_log[-limit:])

    def clear(self) -> None:
        self._proposals.clear()
        self._enabled_versions.clear()
        self._audit_log.clear()

    def _get(self, proposal_id: str) -> SkillEvolutionProposal:
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise SkillEvolutionError("skill evolution proposal not found")
        return proposal

    @staticmethod
    def _eval_complete(proposal: SkillEvolutionProposal) -> bool:
        return REQUIRED_SKILL_EVAL_CHECKS.issubset(proposal.eval_results) and all(
            proposal.eval_results[name] for name in REQUIRED_SKILL_EVAL_CHECKS
        )

    def _audit(
        self,
        *,
        action: str,
        proposal: SkillEvolutionProposal,
        actor: str,
        reason_code: str,
        now: datetime,
        metadata: dict[str, str] | None = None,
    ) -> str:
        event_id = uuid.uuid4().hex
        self._audit_log.append(SkillEvolutionAuditEvent(
            event_id=event_id,
            action=action,
            proposal_id=proposal.proposal_id,
            skill_name=proposal.skill_name,
            status=proposal.status,
            actor=actor,
            reason_code=reason_code,
            created_at=now,
            metadata=metadata or {},
        ))
        if len(self._audit_log) > self._max_audit:
            self._audit_log = self._audit_log[-self._max_audit:]
        return event_id


skill_evolution_service = SkillEvolutionService()
