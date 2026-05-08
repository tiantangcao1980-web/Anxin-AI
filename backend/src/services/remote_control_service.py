"""DB-backed mobile-to-desktop remote-control control plane.

This service only manages pairing, authorization, command queue state, and
audit. It does not claim that a desktop host has executed a queued command.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.sync import RemoteControlAuditEvent, RemoteControlCommand, RemoteControlPairing
from src.services.agent_governance_service import AgentGovernanceService

REMOTE_CONTROL_REQUIRED_SCOPE = "desktop:control"
REMOTE_CONTROL_ROUTE_KEY = "desktop-control"
REMOTE_CONTROL_ACTIVE_PAIRING_STATUSES = {"confirmed"}
REMOTE_CONTROL_PENDING_PAIRING_STATUSES = {"pending_desktop_confirmation"}
REMOTE_CONTROL_ACTIVE_COMMAND_STATUSES = {"queued", "claimed", "running"}
REMOTE_CONTROL_EXECUTION_UPDATE_STATUSES = {"running", "completed", "failed"}
REMOTE_CONTROL_TERMINAL_COMMAND_STATUSES = {"cancelled", "completed", "expired", "failed"}
REMOTE_CONTROL_SAFE_PROBE_COMMAND_TYPES = {
    "ping",
    "status_probe",
    "desktop.ping",
    "desktop.status_probe",
}


class RemoteControlError(ValueError):
    """Raised when a remote-control transition must fail closed."""

    def __init__(self, reason_code: str, human_message: str, status_code: int = 400) -> None:
        super().__init__(human_message)
        self.reason_code = reason_code
        self.human_message = human_message
        self.status_code = status_code


@dataclass(frozen=True)
class RemoteControlRouteToken:
    allowed: bool
    reason_code: str
    human_message: str
    token: str | None = None
    route_id: str | None = None
    pairing_id: str | None = None
    expires_at: datetime | None = None


class RemoteControlService:
    """Persists remote-control pairing, queue, and audit records."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def status(self, *, org_id: str, user_id: str, desktop_device_id: str | None = None) -> dict[str, Any]:
        query = select(RemoteControlPairing).where(
            RemoteControlPairing.org_id == org_id,
            RemoteControlPairing.user_id == user_id,
        )
        if desktop_device_id:
            query = query.where(RemoteControlPairing.desktop_device_id == desktop_device_id)
        rows = (await self.db.execute(query.order_by(RemoteControlPairing.created_at.desc()).limit(20))).scalars().all()
        confirmed = [row for row in rows if row.status in REMOTE_CONTROL_ACTIVE_PAIRING_STATUSES]
        pending = [row for row in rows if row.status in REMOTE_CONTROL_PENDING_PAIRING_STATUSES]
        queued_count = 0
        if confirmed:
            queued_count = await self._queued_command_count(org_id=org_id, pairing_ids=[row.id for row in confirmed])

        if confirmed:
            status = "queue_ready_execution_pending"
            message = "远控控制面已具备已确认配对和命令队列；仍需桌面 host 拉取、执行状态回传和真机证据。"
        elif pending:
            status = "pending_desktop_confirmation"
            message = "已有配对请求等待桌面端确认；确认前不会接受远控命令。"
        else:
            status = "not_configured"
            message = "移动远控桌面尚未创建持久化配对、命令队列和审计闭环；默认不可用。"

        return {
            "available": bool(confirmed),
            "status": status,
            "desktop_device_id": desktop_device_id or (rows[0].desktop_device_id if rows else None),
            "pairing_id": confirmed[0].id if confirmed else (pending[0].id if pending else None),
            "queued_command_count": queued_count,
            "required_controls": [
                "device_pairing",
                "desktop_confirmation",
                "capability_route_token",
                "second_confirmation_for_high_risk_commands",
                "command_expiry_and_revocation",
                "audit_log",
            ],
            "message": message,
        }

    async def create_pairing(
        self,
        *,
        org_id: str,
        user_id: str,
        mobile_device_id: str,
        desktop_device_id: str,
        requested_scopes: list[str],
        privacy_mode: str,
        expires_in_seconds: int,
        now: datetime | None = None,
    ) -> RemoteControlPairing:
        created_at = now or _now()
        pairing = RemoteControlPairing(
            org_id=org_id,
            user_id=user_id,
            mobile_device_id=_required(mobile_device_id, "mobile_device_id"),
            desktop_device_id=_required(desktop_device_id, "desktop_device_id"),
            requested_scopes=list(_normalize_values(requested_scopes)) or [REMOTE_CONTROL_REQUIRED_SCOPE],
            privacy_mode=(privacy_mode or "hybrid").strip().lower(),
            status="pending_desktop_confirmation",
            expires_at=created_at + timedelta(seconds=expires_in_seconds),
        )
        self.db.add(pairing)
        await self.db.flush()
        self._audit(
            org_id=org_id,
            user_id=user_id,
            pairing_id=pairing.id,
            action="remote_control.pairing.request",
            status="success",
            reason_code="pending_desktop_confirmation",
            resource_snapshot=_pairing_snapshot(pairing),
            now=created_at,
        )
        await self.db.flush()
        return pairing

    async def confirm_pairing(
        self,
        *,
        org_id: str,
        user_id: str,
        pairing_id: str,
        desktop_device_id: str,
        now: datetime | None = None,
    ) -> RemoteControlPairing:
        confirmed_at = now or _now()
        pairing = await self._get_pairing(org_id=org_id, user_id=user_id, pairing_id=pairing_id)
        if pairing is None:
            raise RemoteControlError("remote_control_pairing_not_found", "远控配对不存在或不属于当前组织。", 404)
        if pairing.desktop_device_id != desktop_device_id:
            self._audit_pairing_denial(pairing, user_id, "desktop_device_mismatch", confirmed_at)
            await self.db.flush()
            raise RemoteControlError("remote_control_desktop_device_mismatch", "桌面设备与配对请求不匹配。", 403)
        self._ensure_pairing_live(pairing, checked_at=confirmed_at)
        if pairing.status != "pending_desktop_confirmation":
            self._audit_pairing_denial(pairing, user_id, "pairing_transition_denied", confirmed_at)
            await self.db.flush()
            raise RemoteControlError("remote_control_pairing_transition_denied", "当前配对状态不能确认。", 409)

        pairing.status = "confirmed"
        pairing.confirmed_at = confirmed_at
        pairing.confirmed_by = user_id
        self._audit(
            org_id=org_id,
            user_id=user_id,
            pairing_id=pairing.id,
            action="remote_control.pairing.confirm",
            status="success",
            reason_code="confirmed",
            resource_snapshot=_pairing_snapshot(pairing),
            now=confirmed_at,
        )
        await self.db.flush()
        return pairing

    async def issue_route_token(
        self,
        *,
        org_id: str,
        user_id: str,
        pairing_id: str,
        ttl_seconds: int | None = None,
    ) -> RemoteControlRouteToken:
        pairing = await self._get_pairing(org_id=org_id, user_id=user_id, pairing_id=pairing_id)
        if pairing is None:
            return RemoteControlRouteToken(False, "remote_control_pairing_not_found", "远控配对不存在或不属于当前组织。")
        try:
            self._ensure_pairing_confirmed(pairing)
        except RemoteControlError as exc:
            self._audit_pairing_denial(pairing, user_id, exc.reason_code, _now())
            await self.db.flush()
            return RemoteControlRouteToken(False, exc.reason_code, exc.human_message, pairing_id=pairing.id)

        issued = await AgentGovernanceService(self.db).issue_route_token(
            org_id=org_id,
            route_key=REMOTE_CONTROL_ROUTE_KEY,
            consumer_id=pairing.id,
            requested_scopes=[REMOTE_CONTROL_REQUIRED_SCOPE],
            ttl_seconds=ttl_seconds,
            actor_user_id=user_id,
            actor_type="remote_control",
        )
        return RemoteControlRouteToken(
            allowed=issued.allowed,
            reason_code=issued.reason_code,
            human_message=issued.human_message,
            token=issued.token,
            route_id=issued.route_id,
            pairing_id=pairing.id,
            expires_at=issued.expires_at,
        )

    async def enqueue_command(
        self,
        *,
        org_id: str,
        user_id: str,
        desktop_device_id: str,
        command_type: str,
        payload: dict[str, Any],
        pairing_id: str,
        route_token: str,
        risk_level: str,
        second_confirmed: bool,
        expires_in_seconds: int = 300,
        now: datetime | None = None,
    ) -> RemoteControlCommand:
        queued_at = now or _now()
        pairing = await self._get_pairing(org_id=org_id, user_id=user_id, pairing_id=pairing_id)
        if pairing is None:
            raise RemoteControlError("remote_control_pairing_not_found", "远控配对不存在或不属于当前组织。", 404)
        if pairing.desktop_device_id != desktop_device_id:
            self._audit_pairing_denial(pairing, user_id, "desktop_device_mismatch", queued_at)
            await self.db.flush()
            raise RemoteControlError("remote_control_desktop_device_mismatch", "桌面设备与配对请求不匹配。", 403)
        self._ensure_pairing_confirmed(pairing, checked_at=queued_at)

        decision = await self._validate_pairing_route_token(
            org_id=org_id,
            user_id=user_id,
            pairing=pairing,
            route_token=route_token,
            action="remote_control.command.enqueue",
            resource_snapshot={"desktop_device_id": desktop_device_id, "command_type": command_type},
            now=queued_at,
        )
        normalized_command_type = _normalize_command_type(command_type)
        if normalized_command_type not in REMOTE_CONTROL_SAFE_PROBE_COMMAND_TYPES:
            self._audit(
                org_id=org_id,
                user_id=user_id,
                pairing_id=pairing.id,
                action="remote_control.command.enqueue",
                status="denied",
                reason_code="unsupported_command_type",
                resource_snapshot={
                    "desktop_device_id": desktop_device_id,
                    "command_type": normalized_command_type,
                    "supported_command_types": sorted(REMOTE_CONTROL_SAFE_PROBE_COMMAND_TYPES),
                },
                metadata={"route_audit_event_id": decision.audit_event_id},
                now=queued_at,
            )
            await self.db.flush()
            raise RemoteControlError(
                "remote_control_command_type_not_supported",
                "当前桌面远控运行时只允许 safe-probe 命令入队；高风险真实执行器尚未接入。",
                403,
            )

        command = RemoteControlCommand(
            org_id=org_id,
            user_id=user_id,
            pairing_id=pairing.id,
            desktop_device_id=desktop_device_id,
            command_type=normalized_command_type,
            payload=_scrub_payload(payload),
            risk_level=(risk_level or "l3").strip().lower(),
            status="queued",
            route_id=decision.route_id,
            route_consumer_id=decision.consumer_id,
            route_scopes=list(decision.scopes),
            second_confirmed=second_confirmed,
            expires_at=queued_at + timedelta(seconds=expires_in_seconds),
        )
        self.db.add(command)
        await self.db.flush()
        self._audit(
            org_id=org_id,
            user_id=user_id,
            pairing_id=pairing.id,
            command_id=command.id,
            action="remote_control.command.enqueue",
            status="success",
            reason_code="queued",
            resource_snapshot=_command_snapshot(command),
            metadata={"route_audit_event_id": decision.audit_event_id},
            now=queued_at,
        )
        await self.db.flush()
        return command

    async def claim_commands(
        self,
        *,
        org_id: str,
        user_id: str,
        desktop_device_id: str,
        pairing_id: str,
        route_token: str,
        host_instance_id: str,
        limit: int = 10,
        now: datetime | None = None,
    ) -> list[RemoteControlCommand]:
        claimed_at = now or _now()
        host_id = _required(host_instance_id, "host_instance_id")[:160]
        pairing = await self._get_pairing(org_id=org_id, user_id=user_id, pairing_id=pairing_id)
        if pairing is None:
            raise RemoteControlError("remote_control_pairing_not_found", "远控配对不存在或不属于当前组织。", 404)
        if pairing.desktop_device_id != desktop_device_id:
            self._audit_pairing_denial(pairing, user_id, "desktop_device_mismatch", claimed_at)
            await self.db.flush()
            raise RemoteControlError("remote_control_desktop_device_mismatch", "桌面设备与配对请求不匹配。", 403)
        self._ensure_pairing_confirmed(pairing, checked_at=claimed_at)
        await self._validate_pairing_route_token(
            org_id=org_id,
            user_id=user_id,
            pairing=pairing,
            route_token=route_token,
            action="remote_control.command.claim",
            resource_snapshot={"desktop_device_id": desktop_device_id, "host_instance_id": host_id},
            now=claimed_at,
        )
        await self._expire_stale_queued_commands(
            org_id=org_id,
            user_id=user_id,
            pairing=pairing,
            desktop_device_id=desktop_device_id,
            now=claimed_at,
        )
        commands = (
            await self.db.execute(
                select(RemoteControlCommand)
                .where(
                    RemoteControlCommand.org_id == org_id,
                    RemoteControlCommand.user_id == user_id,
                    RemoteControlCommand.pairing_id == pairing.id,
                    RemoteControlCommand.desktop_device_id == desktop_device_id,
                    RemoteControlCommand.status == "queued",
                    RemoteControlCommand.expires_at > claimed_at,
                )
                .order_by(RemoteControlCommand.created_at.asc())
                .limit(limit)
            )
        ).scalars().all()
        for command in commands:
            command.status = "claimed"
            command.claimed_at = claimed_at
            command.claimed_by_host = host_id
            self._audit(
                org_id=org_id,
                user_id=user_id,
                pairing_id=pairing.id,
                command_id=command.id,
                action="remote_control.command.claim",
                status="success",
                reason_code="claimed",
                resource_snapshot=_command_snapshot(command),
                metadata={"host_instance_id": host_id},
                now=claimed_at,
            )
        await self.db.flush()
        return list(commands)

    async def update_command_status(
        self,
        *,
        org_id: str,
        user_id: str,
        command_id: str,
        desktop_device_id: str,
        pairing_id: str,
        route_token: str,
        host_instance_id: str,
        status: str,
        result_summary: dict[str, Any] | None = None,
        failure_reason: str | None = None,
        now: datetime | None = None,
    ) -> RemoteControlCommand:
        updated_at = now or _now()
        next_status = (status or "").strip().lower()
        if next_status not in REMOTE_CONTROL_EXECUTION_UPDATE_STATUSES:
            raise RemoteControlError("remote_control_command_status_invalid", "远控命令状态回传值不受支持。", 400)
        host_id = _required(host_instance_id, "host_instance_id")[:160]
        pairing = await self._get_pairing(org_id=org_id, user_id=user_id, pairing_id=pairing_id)
        if pairing is None:
            raise RemoteControlError("remote_control_pairing_not_found", "远控配对不存在或不属于当前组织。", 404)
        command = await self._get_command(org_id=org_id, user_id=user_id, command_id=command_id)
        if command is None or command.pairing_id != pairing.id:
            raise RemoteControlError("remote_control_command_not_found", "远控命令不存在或不属于当前组织。", 404)
        if pairing.desktop_device_id != desktop_device_id or command.desktop_device_id != desktop_device_id:
            self._audit_pairing_denial(pairing, user_id, "desktop_device_mismatch", updated_at)
            await self.db.flush()
            raise RemoteControlError("remote_control_desktop_device_mismatch", "桌面设备与配对请求不匹配。", 403)
        self._ensure_pairing_confirmed(pairing, checked_at=updated_at)
        await self._validate_pairing_route_token(
            org_id=org_id,
            user_id=user_id,
            pairing=pairing,
            route_token=route_token,
            action="remote_control.command.status_update",
            resource_snapshot=_command_snapshot(command),
            now=updated_at,
        )
        if command.status in REMOTE_CONTROL_TERMINAL_COMMAND_STATUSES:
            raise RemoteControlError("remote_control_command_transition_denied", "终态远控命令不能继续回传执行状态。", 409)
        if _as_utc(command.expires_at) <= updated_at:
            command.status = "expired"
            self._audit(
                org_id=org_id,
                user_id=user_id,
                pairing_id=pairing.id,
                command_id=command.id,
                action="remote_control.command.expire",
                status="success",
                reason_code="expired",
                resource_snapshot=_command_snapshot(command),
                metadata={"host_instance_id": host_id},
                now=updated_at,
            )
            await self.db.flush()
            raise RemoteControlError("remote_control_command_expired", "远控命令已过期，不能继续回传执行状态。", 409)
        if command.claimed_by_host and command.claimed_by_host != host_id:
            raise RemoteControlError("remote_control_command_host_mismatch", "远控命令已被其他桌面 host 领取。", 403)
        if command.status == "queued":
            raise RemoteControlError("remote_control_command_not_claimed", "远控命令必须先被桌面 host 领取再回传状态。", 409)
        if next_status == "running" and command.status not in {"claimed", "running"}:
            raise RemoteControlError("remote_control_command_transition_denied", "当前远控命令状态不能进入 running。", 409)
        if next_status in {"completed", "failed"} and command.status not in {"claimed", "running"}:
            raise RemoteControlError("remote_control_command_transition_denied", "当前远控命令状态不能结束。", 409)

        command.status = next_status
        command.claimed_by_host = host_id
        if next_status == "running":
            command.started_at = command.started_at or updated_at
        elif next_status == "completed":
            command.completed_at = updated_at
            command.result_summary = _scrub_payload(result_summary or {})
        elif next_status == "failed":
            command.failed_at = updated_at
            command.failure_reason = (failure_reason or "").strip()[:1000] or "desktop_host_failed"
            command.result_summary = _scrub_payload(result_summary or {})
        self._audit(
            org_id=org_id,
            user_id=user_id,
            pairing_id=pairing.id,
            command_id=command.id,
            action="remote_control.command.status_update",
            status="success",
            reason_code=next_status,
            resource_snapshot=_command_snapshot(command),
            metadata={"host_instance_id": host_id, "result_summary": result_summary or {}},
            now=updated_at,
        )
        await self.db.flush()
        return command

    async def cancel_command(
        self,
        *,
        org_id: str,
        user_id: str,
        command_id: str,
        reason: str,
        now: datetime | None = None,
    ) -> RemoteControlCommand:
        cancelled_at = now or _now()
        command = await self._get_command(org_id=org_id, user_id=user_id, command_id=command_id)
        if command is None:
            raise RemoteControlError("remote_control_command_not_found", "远控命令不存在或不属于当前组织。", 404)
        if command.status not in {"queued", "claimed"}:
            raise RemoteControlError("remote_control_command_not_cancellable", "只有 queued/claimed 状态的远控命令可以取消。", 409)
        command.status = "cancelled"
        command.cancelled_at = cancelled_at
        command.cancel_reason = (reason or "").strip()[:500]
        self._audit(
            org_id=org_id,
            user_id=user_id,
            pairing_id=command.pairing_id,
            command_id=command.id,
            action="remote_control.command.cancel",
            status="success",
            reason_code="cancelled",
            resource_snapshot=_command_snapshot(command),
            now=cancelled_at,
        )
        await self.db.flush()
        return command

    async def get_command(self, *, org_id: str, user_id: str, command_id: str) -> RemoteControlCommand | None:
        return await self._get_command(org_id=org_id, user_id=user_id, command_id=command_id)

    async def audit_events(self, *, org_id: str, user_id: str, limit: int = 50) -> list[RemoteControlAuditEvent]:
        rows = (
            await self.db.execute(
                select(RemoteControlAuditEvent)
                .where(
                    RemoteControlAuditEvent.org_id == org_id,
                    RemoteControlAuditEvent.user_id == user_id,
                )
                .order_by(RemoteControlAuditEvent.created_at.desc())
                .limit(limit)
            )
        ).scalars().all()
        return list(rows)

    async def _queued_command_count(self, *, org_id: str, pairing_ids: list[str]) -> int:
        if not pairing_ids:
            return 0
        result = await self.db.execute(
            select(func.count()).select_from(RemoteControlCommand).where(
                RemoteControlCommand.org_id == org_id,
                RemoteControlCommand.pairing_id.in_(pairing_ids),
                RemoteControlCommand.status == "queued",
            )
        )
        return int(result.scalar_one())

    async def _validate_pairing_route_token(
        self,
        *,
        org_id: str,
        user_id: str,
        pairing: RemoteControlPairing,
        route_token: str,
        action: str,
        resource_snapshot: dict[str, Any],
        now: datetime,
    ) -> Any:
        decision = await AgentGovernanceService(self.db).validate_route_token(
            org_id=org_id,
            raw_token=route_token,
            required_scope=REMOTE_CONTROL_REQUIRED_SCOPE,
            consumer_id=pairing.id,
            actor_user_id=user_id,
            actor_type="remote_control",
        )
        if not decision.allowed:
            self._audit(
                org_id=org_id,
                user_id=user_id,
                pairing_id=pairing.id,
                action=action,
                status="denied",
                reason_code=decision.reason_code,
                resource_snapshot=resource_snapshot,
                metadata={"route_audit_event_id": decision.audit_event_id},
                now=now,
            )
            await self.db.flush()
            raise RemoteControlError(decision.reason_code, decision.human_message, 403)
        return decision

    async def _expire_stale_queued_commands(
        self,
        *,
        org_id: str,
        user_id: str,
        pairing: RemoteControlPairing,
        desktop_device_id: str,
        now: datetime,
    ) -> None:
        expired_commands = (
            await self.db.execute(
                select(RemoteControlCommand).where(
                    RemoteControlCommand.org_id == org_id,
                    RemoteControlCommand.user_id == user_id,
                    RemoteControlCommand.pairing_id == pairing.id,
                    RemoteControlCommand.desktop_device_id == desktop_device_id,
                    RemoteControlCommand.status == "queued",
                    RemoteControlCommand.expires_at <= now,
                )
            )
        ).scalars().all()
        for command in expired_commands:
            command.status = "expired"
            self._audit(
                org_id=org_id,
                user_id=user_id,
                pairing_id=pairing.id,
                command_id=command.id,
                action="remote_control.command.expire",
                status="success",
                reason_code="expired",
                resource_snapshot=_command_snapshot(command),
                now=now,
            )

    async def _get_pairing(self, *, org_id: str, user_id: str, pairing_id: str) -> RemoteControlPairing | None:
        if not _looks_like_uuid(pairing_id):
            return None
        return (
            await self.db.execute(
                select(RemoteControlPairing).where(
                    RemoteControlPairing.org_id == org_id,
                    RemoteControlPairing.user_id == user_id,
                    RemoteControlPairing.id == pairing_id,
                )
            )
        ).scalar_one_or_none()

    async def _get_command(self, *, org_id: str, user_id: str, command_id: str) -> RemoteControlCommand | None:
        if not _looks_like_uuid(command_id):
            return None
        return (
            await self.db.execute(
                select(RemoteControlCommand).where(
                    RemoteControlCommand.org_id == org_id,
                    RemoteControlCommand.user_id == user_id,
                    RemoteControlCommand.id == command_id,
                )
            )
        ).scalar_one_or_none()

    def _ensure_pairing_confirmed(self, pairing: RemoteControlPairing, checked_at: datetime | None = None) -> None:
        self._ensure_pairing_live(pairing, checked_at=checked_at)
        if pairing.status != "confirmed":
            raise RemoteControlError("remote_control_pairing_not_confirmed", "远控配对尚未完成桌面端确认。", 403)

    def _ensure_pairing_live(self, pairing: RemoteControlPairing, checked_at: datetime | None = None) -> None:
        now = _as_utc(checked_at or _now())
        if pairing.revoked_at or pairing.status == "revoked":
            raise RemoteControlError("remote_control_pairing_revoked", "远控配对已撤销。", 403)
        if _as_utc(pairing.expires_at) <= now:
            raise RemoteControlError("remote_control_pairing_expired", "远控配对已过期。", 403)

    def _audit_pairing_denial(
        self,
        pairing: RemoteControlPairing,
        user_id: str,
        reason_code: str,
        now: datetime,
    ) -> None:
        self._audit(
            org_id=pairing.org_id,
            user_id=user_id,
            pairing_id=pairing.id,
            action="remote_control.pairing.transition",
            status="denied",
            reason_code=reason_code,
            resource_snapshot=_pairing_snapshot(pairing),
            now=now,
        )

    def _audit(
        self,
        *,
        org_id: str,
        user_id: str | None,
        action: str,
        status: str,
        reason_code: str,
        pairing_id: str | None = None,
        command_id: str | None = None,
        resource_snapshot: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> RemoteControlAuditEvent:
        event = RemoteControlAuditEvent(
            org_id=org_id,
            user_id=user_id,
            pairing_id=pairing_id,
            command_id=command_id,
            actor_type="user",
            action=action,
            status=status,
            reason_code=reason_code,
            resource_snapshot=resource_snapshot,
            metadata_json=_scrub_payload(metadata or {}),
            created_at=now or _now(),
        )
        self.db.add(event)
        return event


def _now() -> datetime:
    return datetime.now(UTC)


def _required(value: str | None, field_name: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise RemoteControlError("remote_control_required_field_missing", f"{field_name} is required", 400)
    return normalized


def _normalize_command_type(value: str | None) -> str:
    return _required(value, "command_type").strip().lower()


def _normalize_values(values: list[str] | set[str] | tuple[str, ...] | None) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip().lower() for value in values or [] if str(value).strip()}))


def _pairing_snapshot(pairing: RemoteControlPairing) -> dict[str, Any]:
    return {
        "pairing_id": pairing.id,
        "mobile_device_id": pairing.mobile_device_id,
        "desktop_device_id": pairing.desktop_device_id,
        "requested_scopes": pairing.requested_scopes,
        "privacy_mode": pairing.privacy_mode,
        "status": pairing.status,
        "expires_at": _iso(pairing.expires_at),
        "confirmed_at": _iso(pairing.confirmed_at),
    }


def _command_snapshot(command: RemoteControlCommand) -> dict[str, Any]:
    return {
        "command_id": command.id,
        "pairing_id": command.pairing_id,
        "desktop_device_id": command.desktop_device_id,
        "command_type": command.command_type,
        "risk_level": command.risk_level,
        "status": command.status,
        "route_id": command.route_id,
        "route_consumer_id": command.route_consumer_id,
        "route_scopes": command.route_scopes,
        "second_confirmed": command.second_confirmed,
        "expires_at": _iso(command.expires_at),
        "claimed_at": _iso(command.claimed_at),
        "claimed_by_host": command.claimed_by_host,
        "started_at": _iso(command.started_at),
        "completed_at": _iso(command.completed_at),
        "failed_at": _iso(command.failed_at),
    }


def _iso(value: datetime | None) -> str | None:
    return _as_utc(value).isoformat() if value else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _scrub_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: _scrub_value(key, value) for key, value in payload.items()}


def _scrub_value(key: str, value: Any) -> Any:
    lowered = key.lower()
    if any(fragment in lowered for fragment in ("token", "secret", "password", "credential", "api_key")):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(child_key): _scrub_value(str(child_key), child_value) for child_key, child_value in value.items()}
    if isinstance(value, list):
        return [_scrub_value(key, item) for item in value]
    return value


def _looks_like_uuid(value: str | None) -> bool:
    try:
        UUID(str(value))
        return True
    except (TypeError, ValueError):
        return False
