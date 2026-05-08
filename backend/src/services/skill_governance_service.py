"""Database-backed Skill governance lifecycle controls."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_governance import (
    SkillEnabledVersion,
    SkillGovernanceAuditEvent,
    SkillGovernanceProposal,
)
from src.services.skill_evolution_service import (
    AUTHORIZED_SKILL_APPROVER_ROLES,
    REQUIRED_SKILL_EVAL_CHECKS,
    SkillEvolutionError,
    SkillEvolutionStatus,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


class SkillGovernanceService:
    """Persists Skill proposal, evaluation, approval, release, rollback, and audit state."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_proposal(
        self,
        *,
        org_id: str,
        skill_name: str,
        proposed_version: str,
        source: str,
        created_by: str,
        created_by_role: str,
        current_version: str | None = None,
        risk_level: str = "medium",
        now: datetime | None = None,
    ) -> SkillGovernanceProposal:
        created_at = now or _now()
        normalized_skill = _required(_normalize(skill_name), "skill_name")
        normalized_proposed = _required(proposed_version, "proposed_version")
        normalized_source = _required(source, "source")
        normalized_actor = _required(created_by, "created_by")
        normalized_role = _normalize(created_by_role) or "agent"
        normalized_current = (current_version or "").strip() or None
        if normalized_current and normalized_current == normalized_proposed:
            raise SkillEvolutionError("proposed_version must differ from current_version")

        proposal = SkillGovernanceProposal(
            org_id=org_id,
            skill_name=normalized_skill,
            current_version=normalized_current,
            proposed_version=normalized_proposed,
            source=normalized_source,
            created_by=normalized_actor,
            created_by_role=normalized_role,
            risk_level=_normalize(risk_level) or "medium",
            status=SkillEvolutionStatus.DRAFT.value,
            eval_results={},
        )
        self.db.add(proposal)
        await self.db.flush()

        if normalized_current and await self.get_enabled_version(org_id=org_id, skill_name=normalized_skill) is None:
            await self._upsert_enabled_version(
                org_id=org_id,
                skill_name=normalized_skill,
                version=normalized_current,
                proposal_id=None,
                now=created_at,
            )

        self._audit(
            org_id=org_id,
            proposal=proposal,
            action="skill_governance.proposal.create",
            status="success",
            actor=normalized_actor,
            reason_code="draft_created",
            metadata={"created_by_role": normalized_role},
            now=created_at,
        )
        await self.db.flush()
        return proposal

    async def record_eval(
        self,
        *,
        org_id: str,
        proposal_id: str,
        checks: dict[str, bool],
        actor: str,
        now: datetime | None = None,
    ) -> SkillGovernanceProposal:
        proposal = await self._get_proposal(org_id=org_id, proposal_id=proposal_id)
        checked_at = now or _now()
        normalized_checks = {
            _normalize(name): bool(passed)
            for name, passed in checks.items()
            if _normalize(name)
        }
        if not normalized_checks:
            raise SkillEvolutionError("at least one eval check is required")
        if proposal.status not in {
            SkillEvolutionStatus.DRAFT.value,
            SkillEvolutionStatus.EVALUATED.value,
            SkillEvolutionStatus.REJECTED.value,
        }:
            self._audit(
                org_id=org_id,
                proposal=proposal,
                action="skill_governance.eval.deny",
                status="denied",
                actor=actor,
                reason_code="eval_transition_denied",
                metadata={"proposal_status": proposal.status},
                now=checked_at,
            )
            await self.db.flush()
            raise SkillEvolutionError(f"cannot record eval when proposal is {proposal.status}")

        proposal.eval_results = normalized_checks
        missing = REQUIRED_SKILL_EVAL_CHECKS - set(normalized_checks)
        failed = {name for name, passed in normalized_checks.items() if not passed}
        if missing or failed:
            proposal.status = SkillEvolutionStatus.REJECTED.value
            self._audit(
                org_id=org_id,
                proposal=proposal,
                action="skill_governance.eval.record",
                status="denied",
                actor=actor,
                reason_code="eval_failed",
                metadata={
                    "missing": ",".join(sorted(missing)),
                    "failed": ",".join(sorted(failed)),
                },
                now=checked_at,
            )
            await self.db.flush()
            return proposal

        proposal.status = SkillEvolutionStatus.EVALUATED.value
        self._audit(
            org_id=org_id,
            proposal=proposal,
            action="skill_governance.eval.record",
            status="success",
            actor=actor,
            reason_code="eval_passed",
            metadata={"check_count": str(len(normalized_checks))},
            now=checked_at,
        )
        await self.db.flush()
        return proposal

    async def approve(
        self,
        *,
        org_id: str,
        proposal_id: str,
        approver: str,
        approver_role: str,
        now: datetime | None = None,
    ) -> SkillGovernanceProposal:
        proposal = await self._get_proposal(org_id=org_id, proposal_id=proposal_id)
        approved_at = now or _now()
        role = _normalize(approver_role)
        if role not in AUTHORIZED_SKILL_APPROVER_ROLES:
            self._audit(
                org_id=org_id,
                proposal=proposal,
                action="skill_governance.approval.deny",
                status="denied",
                actor=approver,
                reason_code="unauthorized_approver",
                metadata={"approver_role": role},
                now=approved_at,
            )
            await self.db.flush()
            raise SkillEvolutionError("approver role is not authorized for skill evolution")
        if proposal.status != SkillEvolutionStatus.EVALUATED.value or not _eval_complete(proposal):
            self._audit(
                org_id=org_id,
                proposal=proposal,
                action="skill_governance.approval.deny",
                status="denied",
                actor=approver,
                reason_code="eval_not_passed",
                metadata={"proposal_status": proposal.status},
                now=approved_at,
            )
            await self.db.flush()
            raise SkillEvolutionError("skill evolution proposal must pass required eval checks before approval")

        proposal.status = SkillEvolutionStatus.APPROVED.value
        proposal.approved_by = approver
        proposal.approver_role = role
        proposal.approved_at = approved_at
        self._audit(
            org_id=org_id,
            proposal=proposal,
            action="skill_governance.approval.approve",
            status="success",
            actor=approver,
            reason_code="approved",
            metadata={"approver_role": role},
            now=approved_at,
        )
        await self.db.flush()
        return proposal

    async def gray_release(
        self,
        *,
        org_id: str,
        proposal_id: str,
        percentage: int,
        actor: str,
        now: datetime | None = None,
    ) -> SkillGovernanceProposal:
        proposal = await self._get_proposal(org_id=org_id, proposal_id=proposal_id)
        released_at = now or _now()
        if proposal.status != SkillEvolutionStatus.APPROVED.value:
            self._audit(
                org_id=org_id,
                proposal=proposal,
                action="skill_governance.release.deny",
                status="denied",
                actor=actor,
                reason_code="approval_required",
                metadata={"proposal_status": proposal.status},
                now=released_at,
            )
            await self.db.flush()
            raise SkillEvolutionError("skill evolution proposal must be approved before gray release")
        if percentage < 1 or percentage > 100:
            self._audit(
                org_id=org_id,
                proposal=proposal,
                action="skill_governance.release.deny",
                status="denied",
                actor=actor,
                reason_code="invalid_gray_percentage",
                metadata={"percentage": str(percentage)},
                now=released_at,
            )
            await self.db.flush()
            raise SkillEvolutionError("gray release percentage must be between 1 and 100")

        proposal.status = SkillEvolutionStatus.GRAY_RELEASED.value
        proposal.gray_percentage = percentage
        proposal.released_at = released_at
        await self._upsert_enabled_version(
            org_id=org_id,
            skill_name=proposal.skill_name,
            version=proposal.proposed_version,
            proposal_id=proposal.id,
            now=released_at,
        )
        self._audit(
            org_id=org_id,
            proposal=proposal,
            action="skill_governance.release.gray",
            status="success",
            actor=actor,
            reason_code="gray_released",
            metadata={"percentage": str(percentage)},
            now=released_at,
        )
        await self.db.flush()
        return proposal

    async def rollback(
        self,
        *,
        org_id: str,
        proposal_id: str,
        reason: str,
        actor: str,
        now: datetime | None = None,
    ) -> SkillGovernanceProposal:
        proposal = await self._get_proposal(org_id=org_id, proposal_id=proposal_id)
        rolled_back_at = now or _now()
        if proposal.status not in {
            SkillEvolutionStatus.APPROVED.value,
            SkillEvolutionStatus.GRAY_RELEASED.value,
            SkillEvolutionStatus.ROLLED_BACK.value,
        }:
            self._audit(
                org_id=org_id,
                proposal=proposal,
                action="skill_governance.release.rollback_deny",
                status="denied",
                actor=actor,
                reason_code="rollback_not_allowed",
                metadata={"proposal_status": proposal.status},
                now=rolled_back_at,
            )
            await self.db.flush()
            raise SkillEvolutionError("only approved or released skill evolution proposals can be rolled back")

        proposal.status = SkillEvolutionStatus.ROLLED_BACK.value
        proposal.rolled_back_at = rolled_back_at
        proposal.rollback_reason = (reason or "").strip() or "rollback"
        if proposal.current_version:
            await self._upsert_enabled_version(
                org_id=org_id,
                skill_name=proposal.skill_name,
                version=proposal.current_version,
                proposal_id=proposal.id,
                now=rolled_back_at,
            )
        else:
            enabled = await self._get_enabled_record(org_id=org_id, skill_name=proposal.skill_name)
            if enabled is not None:
                await self.db.delete(enabled)
        self._audit(
            org_id=org_id,
            proposal=proposal,
            action="skill_governance.release.rollback",
            status="success",
            actor=actor,
            reason_code="rolled_back",
            metadata={"reason": proposal.rollback_reason},
            now=rolled_back_at,
        )
        await self.db.flush()
        return proposal

    async def is_skill_enabled(self, *, org_id: str, skill_name: str, version: str | None = None) -> bool:
        enabled_version = await self.get_enabled_version(org_id=org_id, skill_name=skill_name)
        if enabled_version is None:
            return False
        return version is None or enabled_version == (version or "").strip()

    async def get_enabled_version(self, *, org_id: str, skill_name: str) -> str | None:
        enabled = await self._get_enabled_record(org_id=org_id, skill_name=skill_name)
        if enabled is None or enabled.status != "enabled":
            return None
        return enabled.version

    async def get_audit_events(self, *, org_id: str, limit: int = 100) -> list[SkillGovernanceAuditEvent]:
        if limit <= 0:
            return []
        result = await self.db.execute(
            select(SkillGovernanceAuditEvent)
            .where(SkillGovernanceAuditEvent.org_id == org_id)
            .order_by(SkillGovernanceAuditEvent.created_at.desc(), SkillGovernanceAuditEvent.id.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def _get_proposal(self, *, org_id: str, proposal_id: str) -> SkillGovernanceProposal:
        result = await self.db.execute(
            select(SkillGovernanceProposal).where(
                SkillGovernanceProposal.org_id == org_id,
                SkillGovernanceProposal.id == proposal_id,
            )
        )
        proposal = result.scalar_one_or_none()
        if proposal is None:
            raise SkillEvolutionError("skill evolution proposal not found")
        return proposal

    async def _get_enabled_record(self, *, org_id: str, skill_name: str) -> SkillEnabledVersion | None:
        result = await self.db.execute(
            select(SkillEnabledVersion).where(
                SkillEnabledVersion.org_id == org_id,
                SkillEnabledVersion.skill_name == _normalize(skill_name),
            )
        )
        return result.scalar_one_or_none()

    async def _upsert_enabled_version(
        self,
        *,
        org_id: str,
        skill_name: str,
        version: str,
        proposal_id: str | None,
        now: datetime,
    ) -> SkillEnabledVersion:
        enabled = await self._get_enabled_record(org_id=org_id, skill_name=skill_name)
        if enabled is None:
            enabled = SkillEnabledVersion(
                org_id=org_id,
                skill_name=_normalize(skill_name),
                version=version,
                status="enabled",
                proposal_id=proposal_id,
                enabled_at=now,
            )
            self.db.add(enabled)
        else:
            enabled.version = version
            enabled.status = "enabled"
            enabled.proposal_id = proposal_id
            enabled.enabled_at = now
        await self.db.flush()
        return enabled

    def _audit(
        self,
        *,
        org_id: str,
        proposal: SkillGovernanceProposal,
        action: str,
        status: str,
        actor: str,
        reason_code: str,
        now: datetime,
        metadata: dict[str, str] | None = None,
    ) -> SkillGovernanceAuditEvent:
        event = SkillGovernanceAuditEvent(
            org_id=org_id,
            proposal_id=proposal.id,
            actor=(actor or "system").strip() or "system",
            action=action,
            status=status,
            reason_code=reason_code,
            resource_snapshot=_proposal_snapshot(proposal),
            metadata_json=metadata or {},
            created_at=now,
        )
        self.db.add(event)
        return event


def _eval_complete(proposal: SkillGovernanceProposal) -> bool:
    return REQUIRED_SKILL_EVAL_CHECKS.issubset(proposal.eval_results or {}) and all(
        proposal.eval_results[name] for name in REQUIRED_SKILL_EVAL_CHECKS
    )


def _proposal_snapshot(proposal: SkillGovernanceProposal) -> dict[str, str]:
    return {
        "proposal_id": proposal.id,
        "skill_name": proposal.skill_name,
        "current_version": proposal.current_version or "",
        "proposed_version": proposal.proposed_version,
        "status": proposal.status,
        "risk_level": proposal.risk_level,
    }


def _required(value: str | None, field: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise SkillEvolutionError(f"{field} is required")
    return normalized
