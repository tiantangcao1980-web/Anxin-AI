"""DB-backed approvals for high-risk agent capability execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_governance import AgentApproval, AgentAuditEvent, CapabilityRoute

AUTHORIZED_APPROVER_ROLES = {"owner", "boss", "super_admin", "org_admin", "admin"}
ACTIVE_ROUTE_STATUSES = {"active", "enabled"}
PENDING_STATUS = "pending"
APPROVED_STATUS = "approved"
REJECTED_STATUS = "rejected"
REVOKED_STATUS = "revoked"
EXPIRED_STATUS = "expired"
SENSITIVE_PAYLOAD_FRAGMENTS = ("token", "secret", "password", "credential", "api_key", "private_key")


@dataclass(frozen=True)
class AgentApprovalDecision:
    allowed: bool
    reason_code: str
    human_message: str
    approval_id: str | None = None
    route_id: str | None = None
    status: str | None = None
    expires_at: datetime | None = None
    audit_event_id: str | None = None


class AgentApprovalService:
    """Creates, decides, revokes, and validates high-risk agent approvals."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def request_approval(
        self,
        *,
        org_id: str,
        action_type: str,
        risk_level: str,
        requested_by: str | None,
        route_key: str | None = None,
        route_id: str | None = None,
        payload: dict[str, Any] | None = None,
        expires_at: datetime | None = None,
        now: datetime | None = None,
    ) -> AgentApprovalDecision:
        requested_at = now or _now()
        route = await self._resolve_route(org_id=org_id, route_key=route_key, route_id=route_id)
        if route_key or route_id:
            if route is None:
                event = self._audit(
                    org_id=org_id,
                    action="agent_approval.request",
                    status="denied",
                    reason_code="unknown_capability_route",
                    actor_user_id=requested_by,
                    actor_type="user",
                    metadata={"route_key": route_key or "", "route_id": route_id or ""},
                    now=requested_at,
                )
                await self.db.flush()
                return AgentApprovalDecision(
                    False,
                    "unknown_capability_route",
                    "Capability route does not exist for this organization.",
                    audit_event_id=event.id,
                )

            route_denial = _route_denial(route)
            if route_denial:
                event = self._audit_route(
                    route=route,
                    action="agent_approval.request",
                    status="denied",
                    reason_code=route_denial,
                    actor_user_id=requested_by,
                    metadata={"action_type": action_type},
                    now=requested_at,
                )
                await self.db.flush()
                return AgentApprovalDecision(
                    False,
                    route_denial,
                    _reason_message(route_denial),
                    route_id=route.id,
                    audit_event_id=event.id,
                )

        approval = AgentApproval(
            org_id=org_id,
            route_id=route.id if route else None,
            requested_by=requested_by,
            action_type=_required(action_type, "action_type"),
            risk_level=_required(risk_level, "risk_level"),
            status=PENDING_STATUS,
            payload=_sanitize_payload(payload),
            expires_at=expires_at,
        )
        self.db.add(approval)
        await self.db.flush()
        event = self._audit(
            org_id=org_id,
            route_id=approval.route_id,
            action="agent_approval.request",
            status="success",
            reason_code="requested",
            actor_user_id=requested_by,
            actor_type="user",
            resource_type="agent_approval",
            resource_id=approval.id,
            resource_snapshot=_approval_snapshot(approval),
            metadata={"action_type": approval.action_type, "risk_level": approval.risk_level},
            now=requested_at,
        )
        await self.db.flush()
        return AgentApprovalDecision(
            True,
            "requested",
            "Agent approval request created.",
            approval_id=approval.id,
            route_id=approval.route_id,
            status=approval.status,
            expires_at=approval.expires_at,
            audit_event_id=event.id,
        )

    async def decide_approval(
        self,
        *,
        org_id: str,
        approval_id: str,
        decision: Literal["approve", "reject"],
        decided_by: str,
        decider_role: str,
        note: str | None = None,
        now: datetime | None = None,
    ) -> AgentApprovalDecision:
        decided_at = now or _now()
        approval = await self._get_approval(org_id=org_id, approval_id=approval_id)
        if approval is None:
            event = self._audit_unknown_approval(
                org_id=org_id,
                approval_id=approval_id,
                action=f"agent_approval.{decision}",
                actor_user_id=decided_by,
                actor_role=decider_role,
                now=decided_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(False, "unknown_agent_approval", "Approval does not exist.", audit_event_id=event.id)

        normalized_role = decider_role.strip().lower()
        if normalized_role not in AUTHORIZED_APPROVER_ROLES:
            event = self._audit_approval(
                approval=approval,
                action=f"agent_approval.{decision}",
                status="denied",
                reason_code="approver_role_not_allowed",
                actor_user_id=decided_by,
                actor_role=normalized_role,
                now=decided_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(
                False,
                "approver_role_not_allowed",
                "Current user role cannot decide high-risk agent approvals.",
                approval_id=approval.id,
                route_id=approval.route_id,
                status=approval.status,
                audit_event_id=event.id,
            )

        denial = self._approval_decision_denial(approval=approval, now=decided_at)
        if denial:
            event = self._audit_approval(
                approval=approval,
                action=f"agent_approval.{decision}",
                status="denied",
                reason_code=denial,
                actor_user_id=decided_by,
                actor_role=normalized_role,
                now=decided_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(
                False,
                denial,
                _reason_message(denial),
                approval_id=approval.id,
                route_id=approval.route_id,
                status=approval.status,
                audit_event_id=event.id,
            )

        approval.status = APPROVED_STATUS if decision == "approve" else REJECTED_STATUS
        approval.decided_by = decided_by
        approval.resolved_at = decided_at
        approval.decision_note = note
        event = self._audit_approval(
            approval=approval,
            action=f"agent_approval.{decision}",
            status="success",
            reason_code=approval.status,
            actor_user_id=decided_by,
            actor_role=normalized_role,
            metadata={"note_present": str(bool(note)).lower()},
            now=decided_at,
        )
        await self.db.flush()
        return AgentApprovalDecision(
            True,
            approval.status,
            f"Agent approval {approval.status}.",
            approval_id=approval.id,
            route_id=approval.route_id,
            status=approval.status,
            expires_at=approval.expires_at,
            audit_event_id=event.id,
        )

    async def revoke_approval(
        self,
        *,
        org_id: str,
        approval_id: str,
        revoked_by: str,
        revoker_role: str,
        reason: str,
        now: datetime | None = None,
    ) -> AgentApprovalDecision:
        revoked_at = now or _now()
        approval = await self._get_approval(org_id=org_id, approval_id=approval_id)
        if approval is None:
            event = self._audit_unknown_approval(
                org_id=org_id,
                approval_id=approval_id,
                action="agent_approval.revoke",
                actor_user_id=revoked_by,
                actor_role=revoker_role,
                now=revoked_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(False, "unknown_agent_approval", "Approval does not exist.", audit_event_id=event.id)

        normalized_role = revoker_role.strip().lower()
        if normalized_role not in AUTHORIZED_APPROVER_ROLES:
            event = self._audit_approval(
                approval=approval,
                action="agent_approval.revoke",
                status="denied",
                reason_code="approver_role_not_allowed",
                actor_user_id=revoked_by,
                actor_role=normalized_role,
                now=revoked_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(
                False,
                "approver_role_not_allowed",
                "Current user role cannot revoke high-risk agent approvals.",
                approval_id=approval.id,
                route_id=approval.route_id,
                status=approval.status,
                audit_event_id=event.id,
            )

        if approval.status in {REVOKED_STATUS, EXPIRED_STATUS}:
            event = self._audit_approval(
                approval=approval,
                action="agent_approval.revoke",
                status="denied",
                reason_code="approval_not_active",
                actor_user_id=revoked_by,
                actor_role=normalized_role,
                now=revoked_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(
                False,
                "approval_not_active",
                "Approval is no longer active.",
                approval_id=approval.id,
                route_id=approval.route_id,
                status=approval.status,
                audit_event_id=event.id,
            )

        approval.status = REVOKED_STATUS
        approval.decided_by = revoked_by
        approval.resolved_at = revoked_at
        approval.decision_note = reason
        event = self._audit_approval(
            approval=approval,
            action="agent_approval.revoke",
            status="success",
            reason_code="revoked",
            actor_user_id=revoked_by,
            actor_role=normalized_role,
            metadata={"reason": reason},
            now=revoked_at,
        )
        await self.db.flush()
        return AgentApprovalDecision(
            True,
            "revoked",
            "Agent approval revoked.",
            approval_id=approval.id,
            route_id=approval.route_id,
            status=approval.status,
            audit_event_id=event.id,
        )

    async def validate_approval(
        self,
        *,
        org_id: str,
        approval_id: str | None,
        action_type: str,
        route_key: str | None = None,
        route_id: str | None = None,
        actor_user_id: str | None = None,
        actor_type: str = "agent_worker",
        now: datetime | None = None,
    ) -> AgentApprovalDecision:
        checked_at = now or _now()
        if not approval_id:
            event = self._audit(
                org_id=org_id,
                action="agent_approval.validate",
                status="denied",
                reason_code="missing_agent_approval",
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                metadata={"action_type": action_type},
                now=checked_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(False, "missing_agent_approval", "Missing high-risk action approval.", audit_event_id=event.id)

        approval = await self._get_approval(org_id=org_id, approval_id=approval_id)
        if approval is None:
            event = self._audit_unknown_approval(
                org_id=org_id,
                approval_id=approval_id,
                action="agent_approval.validate",
                actor_user_id=actor_user_id,
                actor_role=actor_type,
                now=checked_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(False, "unknown_agent_approval", "Approval does not exist.", audit_event_id=event.id)

        route = await self._resolve_route(org_id=org_id, route_key=route_key, route_id=route_id)
        denial = self._approval_execution_denial(
            approval=approval,
            action_type=action_type,
            route=route,
            route_requested=bool(route_key or route_id),
            now=checked_at,
        )
        status = "denied" if denial else "success"
        reason_code = denial or "allowed"
        event = self._audit_approval(
            approval=approval,
            action="agent_approval.validate",
            status=status,
            reason_code=reason_code,
            actor_user_id=actor_user_id,
            actor_role=actor_type,
            metadata={"action_type": action_type, "route_key": route_key or ""},
            now=checked_at,
        )
        await self.db.flush()
        return AgentApprovalDecision(
            denial is None,
            reason_code,
            _reason_message(reason_code),
            approval_id=approval.id,
            route_id=approval.route_id,
            status=approval.status,
            expires_at=approval.expires_at,
            audit_event_id=event.id,
        )

    async def _resolve_route(
        self,
        *,
        org_id: str,
        route_key: str | None,
        route_id: str | None,
    ) -> CapabilityRoute | None:
        if route_id:
            return (
                await self.db.execute(
                    select(CapabilityRoute).where(
                        CapabilityRoute.org_id == org_id,
                        CapabilityRoute.id == route_id,
                    )
                )
            ).scalar_one_or_none()
        if route_key:
            return (
                await self.db.execute(
                    select(CapabilityRoute).where(
                        CapabilityRoute.org_id == org_id,
                        CapabilityRoute.route_key == route_key,
                    )
                )
            ).scalar_one_or_none()
        return None

    async def _get_approval(self, *, org_id: str, approval_id: str) -> AgentApproval | None:
        return (
            await self.db.execute(
                select(AgentApproval).where(
                    AgentApproval.org_id == org_id,
                    AgentApproval.id == approval_id,
                )
            )
        ).scalar_one_or_none()

    def _approval_decision_denial(self, *, approval: AgentApproval, now: datetime) -> str | None:
        if approval.status != PENDING_STATUS:
            return "approval_not_pending"
        if _approval_expired(approval, now):
            approval.status = EXPIRED_STATUS
            approval.resolved_at = now
            return "approval_expired"
        return None

    def _approval_execution_denial(
        self,
        *,
        approval: AgentApproval,
        action_type: str,
        route: CapabilityRoute | None,
        route_requested: bool,
        now: datetime,
    ) -> str | None:
        if _approval_expired(approval, now):
            approval.status = EXPIRED_STATUS
            approval.resolved_at = now
            return "approval_expired"
        if approval.status == REVOKED_STATUS:
            return "approval_revoked"
        if approval.status == REJECTED_STATUS:
            return "approval_rejected"
        if approval.status != APPROVED_STATUS:
            return "approval_not_approved"
        if approval.action_type != action_type:
            return "approval_action_mismatch"
        if route_requested and route is None:
            return "unknown_capability_route"
        if route is not None:
            route_denial = _route_denial(route)
            if route_denial:
                return route_denial
            if approval.route_id != route.id:
                return "approval_route_mismatch"
        return None

    def _audit_unknown_approval(
        self,
        *,
        org_id: str,
        approval_id: str,
        action: str,
        actor_user_id: str | None,
        actor_role: str,
        now: datetime,
    ) -> AgentAuditEvent:
        return self._audit(
            org_id=org_id,
            action=action,
            status="denied",
            reason_code="unknown_agent_approval",
            actor_user_id=actor_user_id,
            actor_type="user",
            metadata={"approval_id": approval_id, "actor_role": actor_role},
            now=now,
        )

    def _audit_route(
        self,
        *,
        route: CapabilityRoute,
        action: str,
        status: str,
        reason_code: str,
        actor_user_id: str | None,
        metadata: dict[str, Any] | None,
        now: datetime,
    ) -> AgentAuditEvent:
        return self._audit(
            org_id=route.org_id,
            route_id=route.id,
            action=action,
            status=status,
            reason_code=reason_code,
            actor_user_id=actor_user_id,
            actor_type="user",
            resource_type="capability_route",
            resource_id=route.id,
            resource_snapshot=_route_snapshot(route),
            metadata=metadata,
            now=now,
        )

    def _audit_approval(
        self,
        *,
        approval: AgentApproval,
        action: str,
        status: str,
        reason_code: str,
        actor_user_id: str | None,
        actor_role: str,
        metadata: dict[str, Any] | None = None,
        now: datetime,
    ) -> AgentAuditEvent:
        next_metadata = {"actor_role": actor_role}
        if metadata:
            next_metadata.update(metadata)
        return self._audit(
            org_id=approval.org_id,
            route_id=approval.route_id,
            action=action,
            status=status,
            reason_code=reason_code,
            actor_user_id=actor_user_id,
            actor_type="user",
            resource_type="agent_approval",
            resource_id=approval.id,
            resource_snapshot=_approval_snapshot(approval),
            metadata=next_metadata,
            now=now,
        )

    def _audit(
        self,
        *,
        org_id: str,
        action: str,
        status: str,
        reason_code: str,
        actor_user_id: str | None,
        actor_type: str,
        route_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        resource_snapshot: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime,
    ) -> AgentAuditEvent:
        event = AgentAuditEvent(
            org_id=org_id,
            route_id=route_id,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            action=action,
            status=status,
            reason_code=reason_code,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_snapshot=resource_snapshot,
            metadata_json=_sanitize_flat_metadata(metadata),
            created_at=now,
        )
        self.db.add(event)
        return event


def _now() -> datetime:
    return datetime.now(UTC)


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _approval_expired(approval: AgentApproval, now: datetime) -> bool:
    if approval.expires_at is None:
        return False
    return _ensure_aware(approval.expires_at) <= now


def _route_denial(route: CapabilityRoute) -> str | None:
    if route.revoked_at is not None:
        return "capability_route_revoked"
    if route.status not in ACTIVE_ROUTE_STATUSES:
        return "capability_route_disabled"
    return None


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _approval_snapshot(approval: AgentApproval) -> dict[str, str]:
    return {
        "approval_id": approval.id,
        "action_type": approval.action_type,
        "risk_level": approval.risk_level,
        "status": approval.status,
        "route_id": approval.route_id or "",
    }


def _route_snapshot(route: CapabilityRoute) -> dict[str, str]:
    return {
        "route_id": route.id,
        "route_key": route.route_key,
        "route_type": route.route_type,
        "risk_level": route.risk_level,
        "status": route.status,
    }


def _sanitize_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not payload:
        return None
    return {str(key): _sanitize_value(str(key), value) for key, value in payload.items()}


def _sanitize_value(key: str, value: Any) -> Any:
    if _is_sensitive_key(key):
        return "[redacted]"
    if isinstance(value, dict):
        return {str(child_key): _sanitize_value(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(key, item) for item in value]
    return value


def _sanitize_flat_metadata(metadata: dict[str, Any] | None) -> dict[str, str] | None:
    if not metadata:
        return None
    return {
        str(key): "[redacted]" if _is_sensitive_key(str(key)) else str(value)
        for key, value in metadata.items()
    }


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(fragment in normalized for fragment in SENSITIVE_PAYLOAD_FRAGMENTS)


def _reason_message(reason_code: str) -> str:
    return {
        "allowed": "High-risk agent approval is valid.",
        "requested": "Agent approval request created.",
        "approved": "Agent approval approved.",
        "rejected": "Agent approval rejected.",
        "revoked": "Agent approval revoked.",
        "unknown_agent_approval": "Approval does not exist.",
        "missing_agent_approval": "Missing high-risk action approval.",
        "approval_not_pending": "Approval is no longer pending.",
        "approval_not_approved": "Approval is not approved.",
        "approval_action_mismatch": "Approval does not match the requested action.",
        "approval_route_mismatch": "Approval does not match the requested capability route.",
        "approval_expired": "Approval has expired.",
        "approval_revoked": "Approval has been revoked.",
        "approval_rejected": "Approval has been rejected.",
        "approval_not_active": "Approval is no longer active.",
        "approver_role_not_allowed": "Current role cannot decide this approval.",
        "unknown_capability_route": "Capability route does not exist for this organization.",
        "capability_route_disabled": "Capability route is disabled.",
        "capability_route_revoked": "Capability route has been revoked.",
    }.get(reason_code, "Agent approval request was denied.")
