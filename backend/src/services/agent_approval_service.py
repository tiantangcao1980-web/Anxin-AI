"""DB-backed approvals for high-risk agent capability execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, cast

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
LOCAL_RUNTIME_REHEARSAL_MODE = "local_rehearsal"
WORKSPACE_RUNTIME_ACTIONS = ("pause", "takeover", "terminate")


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
    workspace_snapshot: dict[str, Any] | None = None


@dataclass(frozen=True)
class AgentWorkspaceArtifact:
    id: str
    approval_id: str
    artifact_type: str
    title: str
    content: dict[str, Any]
    metadata: dict[str, Any]
    created_at: datetime
    created_by: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None
    revision: int = 0


@dataclass(frozen=True)
class AgentWorkspaceArtifactChange:
    allowed: bool
    reason_code: str
    human_message: str
    artifact: AgentWorkspaceArtifact | None = None
    approval_id: str | None = None
    status: str | None = None
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

    async def control_workspace(
        self,
        *,
        org_id: str,
        approval_id: str,
        action: Literal["observe", "pause", "takeover", "terminate"],
        actor_user_id: str,
        actor_role: str,
        reason: str | None = None,
        now: datetime | None = None,
    ) -> AgentApprovalDecision:
        controlled_at = now or _now()
        approval = await self._get_approval(org_id=org_id, approval_id=approval_id)
        control_action = f"agent_workspace.{action}"
        if approval is None:
            event = self._audit_unknown_approval(
                org_id=org_id,
                approval_id=approval_id,
                action=control_action,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                now=controlled_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(False, "unknown_agent_approval", "Approval does not exist.", audit_event_id=event.id)

        normalized_role = actor_role.strip().lower()
        if normalized_role not in AUTHORIZED_APPROVER_ROLES:
            event = self._audit_approval(
                approval=approval,
                action=control_action,
                status="denied",
                reason_code="approver_role_not_allowed",
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={"reason_present": str(bool(reason)).lower()},
                now=controlled_at,
            )
            await self.db.flush()
            return AgentApprovalDecision(
                False,
                "approver_role_not_allowed",
                "Current user role cannot control high-risk agent workspaces.",
                approval_id=approval.id,
                route_id=approval.route_id,
                status=approval.status,
                audit_event_id=event.id,
            )

        denial = self._approval_workspace_control_denial(approval=approval, now=controlled_at)
        if denial:
            event = self._audit_approval(
                approval=approval,
                action=control_action,
                status="denied",
                reason_code=denial,
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={
                    "workspace_control": action,
                    "reason_present": str(bool(reason)).lower(),
                },
                now=controlled_at,
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

        if action == "observe":
            snapshot = await self._workspace_observe_snapshot(approval=approval, observed_at=controlled_at)
            event = self._audit_approval(
                approval=approval,
                action=control_action,
                status="success",
                reason_code="observe_snapshot_ready",
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={
                    "workspace_control": action,
                    "reason_present": str(bool(reason)).lower(),
                    "artifact_count": len(snapshot["artifacts"]),
                    "audit_event_count": len(snapshot["audit_events"]) + 1,
                    "runtime_control_state": "read_only_snapshot",
                },
                now=controlled_at,
            )
            await self.db.flush()
            snapshot = {
                **snapshot,
                "observe_audit_event_id": event.id,
                "audit_events": [_audit_event_snapshot(event), *snapshot["audit_events"]],
            }
            return AgentApprovalDecision(
                True,
                "observe_snapshot_ready",
                "Agent workspace observe snapshot prepared.",
                approval_id=approval.id,
                route_id=approval.route_id,
                status=approval.status,
                expires_at=approval.expires_at,
                audit_event_id=event.id,
                workspace_snapshot=snapshot,
            )

        if _local_runtime_rehearsal_enabled(approval):
            snapshot = _workspace_runtime_control_snapshot(
                approval=approval,
                action=action,
                controlled_at=controlled_at,
                reason=reason,
            )
            event = self._audit_approval(
                approval=approval,
                action=control_action,
                status="success",
                reason_code=f"{action}_accepted",
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={
                    "workspace_control": action,
                    "reason_present": str(bool(reason)).lower(),
                    "runtime_control_state": LOCAL_RUNTIME_REHEARSAL_MODE,
                    "runtime_control_id": snapshot["runtime_control"]["id"],
                },
                now=controlled_at,
            )
            await self.db.flush()
            snapshot = {
                **snapshot,
                "runtime_control": {
                    **snapshot["runtime_control"],
                    "audit_event_id": event.id,
                },
                "audit_events": [_audit_event_snapshot(event)],
            }
            return AgentApprovalDecision(
                True,
                f"{action}_accepted",
                f"Agent workspace {action} accepted by local runtime rehearsal.",
                approval_id=approval.id,
                route_id=approval.route_id,
                status=approval.status,
                expires_at=approval.expires_at,
                audit_event_id=event.id,
                workspace_snapshot=snapshot,
            )

        event = self._audit_approval(
            approval=approval,
            action=control_action,
            status="denied",
            reason_code="runtime_not_integrated",
            actor_user_id=actor_user_id,
            actor_role=normalized_role,
            metadata={
                "workspace_control": action,
                "reason_present": str(bool(reason)).lower(),
            },
            now=controlled_at,
        )
        await self.db.flush()
        return AgentApprovalDecision(
            False,
            "runtime_not_integrated",
            "Agent runtime control is not integrated yet; the control action was rejected fail-closed.",
            approval_id=approval.id,
            route_id=approval.route_id,
            status=approval.status,
            audit_event_id=event.id,
        )

    async def list_workspace_artifacts(
        self,
        *,
        org_id: str,
        approval_id: str,
        limit: int = 50,
    ) -> list[AgentWorkspaceArtifact]:
        approval = await self._get_approval(org_id=org_id, approval_id=approval_id)
        if approval is None:
            return []
        rows = (
            await self.db.execute(
                select(AgentAuditEvent)
                .where(
                    AgentAuditEvent.org_id == org_id,
                    AgentAuditEvent.resource_type == "agent_workspace_artifact",
                    AgentAuditEvent.resource_id == approval.id,
                    AgentAuditEvent.action.in_(["agent_workspace.artifact.add", "agent_workspace.artifact.update"]),
                    AgentAuditEvent.status == "success",
                )
                .order_by(AgentAuditEvent.created_at.asc())
                .limit(1000)
            )
        ).scalars().all()
        artifacts = _fold_workspace_artifact_events(list(rows))
        artifacts.sort(key=lambda artifact: artifact.updated_at or artifact.created_at, reverse=True)
        return artifacts[:limit]

    async def add_workspace_artifact(
        self,
        *,
        org_id: str,
        approval_id: str,
        artifact_type: str,
        title: str,
        content: dict[str, Any],
        actor_user_id: str,
        actor_role: str,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> AgentWorkspaceArtifactChange:
        created_at = now or _now()
        approval = await self._get_approval(org_id=org_id, approval_id=approval_id)
        if approval is None:
            event = self._audit_unknown_approval(
                org_id=org_id,
                approval_id=approval_id,
                action="agent_workspace.artifact.add",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                now=created_at,
            )
            await self.db.flush()
            return AgentWorkspaceArtifactChange(
                allowed=False,
                reason_code="unknown_agent_approval",
                human_message="Approval does not exist.",
                audit_event_id=event.id,
            )

        normalized_role = actor_role.strip().lower()
        if normalized_role not in AUTHORIZED_APPROVER_ROLES:
            event = self._audit_approval(
                approval=approval,
                action="agent_workspace.artifact.add",
                status="denied",
                reason_code="approver_role_not_allowed",
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={"artifact_type": artifact_type},
                now=created_at,
            )
            await self.db.flush()
            return AgentWorkspaceArtifactChange(
                allowed=False,
                reason_code="approver_role_not_allowed",
                human_message="Current user role cannot add high-risk agent workspace artifacts.",
                approval_id=approval.id,
                status=approval.status,
                audit_event_id=event.id,
            )

        denial = self._approval_workspace_control_denial(approval=approval, now=created_at)
        if denial:
            event = self._audit_approval(
                approval=approval,
                action="agent_workspace.artifact.add",
                status="denied",
                reason_code=denial,
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={"artifact_type": artifact_type},
                now=created_at,
            )
            await self.db.flush()
            return AgentWorkspaceArtifactChange(
                allowed=False,
                reason_code=denial,
                human_message=_reason_message(denial),
                approval_id=approval.id,
                status=approval.status,
                audit_event_id=event.id,
            )

        snapshot = {
            "approval_id": approval.id,
            "artifact_type": _required(artifact_type, "artifact_type").lower(),
            "title": _required(title, "title"),
            "content": _sanitize_payload(content) or {},
            "metadata": _sanitize_payload(metadata) or {},
        }
        event = self._audit_approval(
            approval=approval,
            action="agent_workspace.artifact.add",
            status="success",
            reason_code="artifact_recorded",
            actor_user_id=actor_user_id,
            actor_role=normalized_role,
            metadata={
                "artifact_type": snapshot["artifact_type"],
                "title": snapshot["title"],
            },
            now=created_at,
        )
        event.resource_type = "agent_workspace_artifact"
        event.resource_id = approval.id
        event.resource_snapshot = snapshot
        await self.db.flush()
        artifact = _artifact_from_event(event)
        return AgentWorkspaceArtifactChange(
            allowed=True,
            reason_code="artifact_recorded",
            human_message="Agent workspace artifact recorded.",
            artifact=artifact,
            approval_id=approval.id,
            status=approval.status,
            audit_event_id=event.id,
        )

    async def update_workspace_artifact(
        self,
        *,
        org_id: str,
        approval_id: str,
        artifact_id: str,
        actor_user_id: str,
        actor_role: str,
        artifact_type: str | None = None,
        title: str | None = None,
        content: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> AgentWorkspaceArtifactChange:
        updated_at = now or _now()
        approval = await self._get_approval(org_id=org_id, approval_id=approval_id)
        normalized_role = actor_role.strip().lower()
        if approval is None:
            event = self._audit_unknown_approval(
                org_id=org_id,
                approval_id=approval_id,
                action="agent_workspace.artifact.update",
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                now=updated_at,
            )
            await self.db.flush()
            return AgentWorkspaceArtifactChange(
                allowed=False,
                reason_code="unknown_agent_approval",
                human_message="Approval does not exist.",
                audit_event_id=event.id,
            )

        if normalized_role not in AUTHORIZED_APPROVER_ROLES:
            event = self._audit_approval(
                approval=approval,
                action="agent_workspace.artifact.update",
                status="denied",
                reason_code="approver_role_not_allowed",
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={"artifact_id": artifact_id},
                now=updated_at,
            )
            await self.db.flush()
            return AgentWorkspaceArtifactChange(
                allowed=False,
                reason_code="approver_role_not_allowed",
                human_message="Current user role cannot edit high-risk agent workspace artifacts.",
                approval_id=approval.id,
                status=approval.status,
                audit_event_id=event.id,
            )

        denial = self._approval_workspace_control_denial(approval=approval, now=updated_at)
        if denial:
            event = self._audit_approval(
                approval=approval,
                action="agent_workspace.artifact.update",
                status="denied",
                reason_code=denial,
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={"artifact_id": artifact_id},
                now=updated_at,
            )
            await self.db.flush()
            return AgentWorkspaceArtifactChange(
                allowed=False,
                reason_code=denial,
                human_message=_reason_message(denial),
                approval_id=approval.id,
                status=approval.status,
                audit_event_id=event.id,
            )

        existing = next(
            (
                artifact
                for artifact in await self.list_workspace_artifacts(
                    org_id=org_id,
                    approval_id=approval.id,
                    limit=1000,
                )
                if artifact.id == artifact_id
            ),
            None,
        )
        if existing is None:
            event = self._audit_approval(
                approval=approval,
                action="agent_workspace.artifact.update",
                status="denied",
                reason_code="unknown_workspace_artifact",
                actor_user_id=actor_user_id,
                actor_role=normalized_role,
                metadata={"artifact_id": artifact_id},
                now=updated_at,
            )
            await self.db.flush()
            return AgentWorkspaceArtifactChange(
                allowed=False,
                reason_code="unknown_workspace_artifact",
                human_message="Workspace artifact does not exist.",
                approval_id=approval.id,
                status=approval.status,
                audit_event_id=event.id,
            )

        snapshot = {
            "approval_id": approval.id,
            "artifact_id": existing.id,
            "artifact_type": _required(artifact_type or existing.artifact_type, "artifact_type").lower(),
            "title": _required(title or existing.title, "title"),
            "content": _sanitize_payload(content if content is not None else existing.content) or {},
            "metadata": _sanitize_payload(metadata if metadata is not None else existing.metadata) or {},
        }
        event = self._audit_approval(
            approval=approval,
            action="agent_workspace.artifact.update",
            status="success",
            reason_code="artifact_updated",
            actor_user_id=actor_user_id,
            actor_role=normalized_role,
            metadata={
                "artifact_id": existing.id,
                "artifact_type": snapshot["artifact_type"],
                "title": snapshot["title"],
            },
            now=updated_at,
        )
        event.resource_type = "agent_workspace_artifact"
        event.resource_id = approval.id
        event.resource_snapshot = snapshot
        await self.db.flush()
        artifact = _merge_workspace_artifact_update(existing, event)
        return AgentWorkspaceArtifactChange(
            allowed=True,
            reason_code="artifact_updated",
            human_message="Agent workspace artifact updated.",
            artifact=artifact,
            approval_id=approval.id,
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

    async def _workspace_observe_snapshot(
        self,
        *,
        approval: AgentApproval,
        observed_at: datetime,
    ) -> dict[str, Any]:
        artifacts = await self.list_workspace_artifacts(
            org_id=approval.org_id,
            approval_id=approval.id,
            limit=20,
        )
        audit_events = (
            await self.db.execute(
                select(AgentAuditEvent)
                .where(
                    AgentAuditEvent.org_id == approval.org_id,
                    AgentAuditEvent.resource_id == approval.id,
                    AgentAuditEvent.resource_type.in_(["agent_approval", "agent_workspace_artifact"]),
                )
                .order_by(AgentAuditEvent.created_at.desc())
                .limit(50)
            )
        ).scalars().all()
        return {
            "observed_at": observed_at.isoformat(),
            "approval": _approval_snapshot(approval),
            "artifacts": [_workspace_artifact_snapshot(artifact) for artifact in artifacts],
            "audit_events": [_audit_event_snapshot(event) for event in audit_events],
            "runtime_controls": _workspace_runtime_controls(approval),
        }

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

    def _approval_workspace_control_denial(self, *, approval: AgentApproval, now: datetime) -> str | None:
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


def _local_runtime_rehearsal_enabled(approval: AgentApproval) -> bool:
    runtime_config = _workspace_runtime_config(approval)
    mode = str(runtime_config.get("mode") or runtime_config.get("control_mode") or "").strip().lower()
    return mode == LOCAL_RUNTIME_REHEARSAL_MODE


def _workspace_runtime_config(approval: AgentApproval) -> dict[str, Any]:
    payload = approval.payload if isinstance(approval.payload, dict) else {}
    for key in ("workspace_runtime", "agent_runtime", "runtime"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    for key in ("workspace_runtime_mode", "runtime_mode"):
        value = payload.get(key)
        if isinstance(value, str):
            return {"mode": value}
    return {}


def _workspace_runtime_controls(approval: AgentApproval) -> dict[str, str]:
    runtime_state = "available_local_rehearsal" if _local_runtime_rehearsal_enabled(approval) else "runtime_not_integrated"
    return {"observe": "available", **dict.fromkeys(WORKSPACE_RUNTIME_ACTIONS, runtime_state)}


def _workspace_runtime_control_snapshot(
    *,
    approval: AgentApproval,
    action: str,
    controlled_at: datetime,
    reason: str | None,
) -> dict[str, Any]:
    return {
        "observed_at": controlled_at.isoformat(),
        "approval": _approval_snapshot(approval),
        "runtime_controls": _workspace_runtime_controls(approval),
        "runtime_control": {
            "id": f"{approval.id}:{action}:{controlled_at.isoformat()}",
            "action": action,
            "mode": LOCAL_RUNTIME_REHEARSAL_MODE,
            "status": "accepted",
            "reason_present": bool(reason),
            "accepted_at": controlled_at.isoformat(),
            "external_side_effects": False,
            "note": "Local runtime rehearsal accepted the control action without external side effects.",
        },
        "audit_events": [],
        "artifacts": [],
    }


def _artifact_from_event(event: AgentAuditEvent) -> AgentWorkspaceArtifact:
    snapshot = event.resource_snapshot or {}
    metadata = event.metadata_json or {}
    content_value = snapshot.get("content")
    metadata_value = snapshot.get("metadata")
    content = cast(dict[str, Any], content_value) if isinstance(content_value, dict) else {}
    artifact_metadata = cast(dict[str, Any], metadata_value) if isinstance(metadata_value, dict) else {}
    return AgentWorkspaceArtifact(
        id=event.id,
        approval_id=str(snapshot.get("approval_id") or event.resource_id or ""),
        artifact_type=str(snapshot.get("artifact_type") or metadata.get("artifact_type") or ""),
        title=str(snapshot.get("title") or metadata.get("title") or ""),
        content=content,
        metadata=artifact_metadata,
        created_at=event.created_at,
        created_by=event.actor_user_id,
    )


def _merge_workspace_artifact_update(
    artifact: AgentWorkspaceArtifact,
    event: AgentAuditEvent,
) -> AgentWorkspaceArtifact:
    snapshot = event.resource_snapshot or {}
    metadata_value = snapshot.get("metadata")
    content_value = snapshot.get("content")
    content = cast(dict[str, Any], content_value) if isinstance(content_value, dict) else artifact.content
    artifact_metadata = cast(dict[str, Any], metadata_value) if isinstance(metadata_value, dict) else artifact.metadata
    return AgentWorkspaceArtifact(
        id=artifact.id,
        approval_id=artifact.approval_id,
        artifact_type=str(snapshot.get("artifact_type") or artifact.artifact_type),
        title=str(snapshot.get("title") or artifact.title),
        content=content,
        metadata=artifact_metadata,
        created_at=artifact.created_at,
        created_by=artifact.created_by,
        updated_at=event.created_at,
        updated_by=event.actor_user_id,
        revision=artifact.revision + 1,
    )


def _fold_workspace_artifact_events(events: list[AgentAuditEvent]) -> list[AgentWorkspaceArtifact]:
    artifacts: dict[str, AgentWorkspaceArtifact] = {}
    for event in events:
        if event.action == "agent_workspace.artifact.add":
            artifact = _artifact_from_event(event)
            artifacts[artifact.id] = artifact
            continue
        if event.action == "agent_workspace.artifact.update":
            snapshot = event.resource_snapshot or {}
            metadata = event.metadata_json or {}
            artifact_id = str(snapshot.get("artifact_id") or metadata.get("artifact_id") or "")
            if artifact_id and artifact_id in artifacts:
                artifacts[artifact_id] = _merge_workspace_artifact_update(artifacts[artifact_id], event)
    return list(artifacts.values())


def _workspace_artifact_snapshot(artifact: AgentWorkspaceArtifact) -> dict[str, Any]:
    return {
        "id": artifact.id,
        "approval_id": artifact.approval_id,
        "artifact_type": artifact.artifact_type,
        "title": artifact.title,
        "content": artifact.content,
        "metadata": artifact.metadata,
        "created_by": artifact.created_by,
        "created_at": artifact.created_at.isoformat(),
        "updated_by": artifact.updated_by,
        "updated_at": artifact.updated_at.isoformat() if artifact.updated_at else None,
        "revision": artifact.revision,
    }


def _audit_event_snapshot(event: AgentAuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "org_id": event.org_id,
        "route_id": event.route_id,
        "actor_user_id": event.actor_user_id,
        "actor_type": event.actor_type,
        "action": event.action,
        "status": event.status,
        "reason_code": event.reason_code,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "resource_snapshot": event.resource_snapshot,
        "metadata": event.metadata_json,
        "created_at": event.created_at.isoformat() if event.created_at else None,
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
        "observe_snapshot_ready": "Agent workspace observe snapshot prepared.",
        "pause_accepted": "Agent workspace pause accepted by local runtime rehearsal.",
        "takeover_accepted": "Agent workspace takeover accepted by local runtime rehearsal.",
        "terminate_accepted": "Agent workspace terminate accepted by local runtime rehearsal.",
        "unknown_workspace_artifact": "Workspace artifact does not exist.",
        "artifact_recorded": "Agent workspace artifact recorded.",
        "artifact_updated": "Agent workspace artifact updated.",
    }.get(reason_code, "Agent approval request was denied.")
