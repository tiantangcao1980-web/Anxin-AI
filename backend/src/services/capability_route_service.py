"""Capability route token broker for governed agent execution.

This module intentionally keeps the first implementation local and small: it
does not store provider credentials, and it never persists raw route tokens.
The durable DB-backed CapabilityRoute model from TASK-12 can replace the in
memory store later while preserving these semantics.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

DEFAULT_ROUTE_TOKEN_TTL_SECONDS = 15 * 60
MAX_ROUTE_TOKEN_TTL_SECONDS = 60 * 60


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CapabilityRouteTokenIssue:
    route_id: str
    consumer_id: str
    token: str
    scopes: tuple[str, ...]
    expires_at: datetime


@dataclass(frozen=True)
class CapabilityRouteDecision:
    allowed: bool
    reason_code: str
    human_message: str
    route_id: str | None = None
    consumer_id: str | None = None
    scopes: tuple[str, ...] = ()
    audit_event_id: str | None = None


@dataclass
class CapabilityRouteRecord:
    route_id: str
    consumer_id: str
    token_hash: str
    scopes: tuple[str, ...]
    expires_at: datetime
    created_at: datetime
    revoked_at: datetime | None = None
    revoked_reason: str | None = None

    @property
    def active(self) -> bool:
        return self.revoked_at is None and self.expires_at > _now()


@dataclass(frozen=True)
class CapabilityRouteAuditEvent:
    event_id: str
    action: str
    route_id: str | None
    consumer_id: str | None
    reason_code: str
    created_at: datetime
    metadata: dict[str, str] = field(default_factory=dict)


class CapabilityRouteService:
    """Issues and validates short-lived route tokens for Agent/Worker calls."""

    def __init__(self) -> None:
        self._records: dict[str, CapabilityRouteRecord] = {}
        self._audit_log: list[CapabilityRouteAuditEvent] = []
        self._max_audit = 3000

    def issue_route_token(
        self,
        *,
        route_id: str,
        consumer_id: str,
        scopes: set[str] | list[str] | tuple[str, ...],
        ttl_seconds: int = DEFAULT_ROUTE_TOKEN_TTL_SECONDS,
        now: datetime | None = None,
    ) -> CapabilityRouteTokenIssue:
        normalized_scopes = self._normalize_scopes(scopes)
        if not route_id.strip():
            raise ValueError("route_id is required")
        if not consumer_id.strip():
            raise ValueError("consumer_id is required")
        if not normalized_scopes:
            raise ValueError("at least one route scope is required")

        issued_at = now or _now()
        ttl = max(1, min(ttl_seconds, MAX_ROUTE_TOKEN_TTL_SECONDS))
        raw_token = f"anxin_route_{secrets.token_urlsafe(32)}"
        token_hash = _hash_token(raw_token)
        record = CapabilityRouteRecord(
            route_id=route_id,
            consumer_id=consumer_id,
            token_hash=token_hash,
            scopes=normalized_scopes,
            expires_at=issued_at + timedelta(seconds=ttl),
            created_at=issued_at,
        )
        self._records[token_hash] = record
        self._audit(
            action="capability_route.token.issue",
            record=record,
            reason_code="issued",
            metadata={"scope_count": str(len(normalized_scopes))},
            now=issued_at,
        )
        return CapabilityRouteTokenIssue(
            route_id=route_id,
            consumer_id=consumer_id,
            token=raw_token,
            scopes=normalized_scopes,
            expires_at=record.expires_at,
        )

    def validate_route_token(
        self,
        raw_token: str | None,
        *,
        required_scope: str | None = None,
        now: datetime | None = None,
    ) -> CapabilityRouteDecision:
        checked_at = now or _now()
        if not raw_token:
            return self._deny(
                "missing_route_token",
                "缺少能力路由 token，Agent/Worker 不能直接调用该能力",
                now=checked_at,
            )

        record = self._records.get(_hash_token(raw_token))
        if record is None:
            return self._deny(
                "unknown_route_token",
                "能力路由 token 无效或已被清理",
                now=checked_at,
            )

        if record.revoked_at is not None:
            return self._deny(
                "route_token_revoked",
                "能力路由已撤销，请重新申请授权",
                record=record,
                now=checked_at,
            )

        if record.expires_at <= checked_at:
            return self._deny(
                "route_token_expired",
                "能力路由 token 已过期，请重新申请授权",
                record=record,
                now=checked_at,
            )

        normalized_scope = (required_scope or "").strip().lower()
        if normalized_scope and normalized_scope not in record.scopes:
            return self._deny(
                "missing_route_scope",
                f"能力路由缺少 scope: {normalized_scope}",
                record=record,
                now=checked_at,
            )

        audit_event_id = self._audit(
            action="capability_route.token.validate",
            record=record,
            reason_code="allowed",
            metadata={"required_scope": normalized_scope},
            now=checked_at,
        )
        return CapabilityRouteDecision(
            allowed=True,
            reason_code="allowed",
            human_message="能力路由已授权",
            route_id=record.route_id,
            consumer_id=record.consumer_id,
            scopes=record.scopes,
            audit_event_id=audit_event_id,
        )

    def revoke_route_token(
        self,
        raw_token: str,
        *,
        reason: str = "revoked",
        now: datetime | None = None,
    ) -> bool:
        revoked_at = now or _now()
        record = self._records.get(_hash_token(raw_token))
        if record is None:
            self._audit(
                action="capability_route.token.revoke",
                record=None,
                reason_code="unknown_route_token",
                metadata={"reason": reason},
                now=revoked_at,
            )
            return False

        record.revoked_at = revoked_at
        record.revoked_reason = reason
        self._audit(
            action="capability_route.token.revoke",
            record=record,
            reason_code="revoked",
            metadata={"reason": reason},
            now=revoked_at,
        )
        return True

    def get_audit_events(self, limit: int = 100) -> list[CapabilityRouteAuditEvent]:
        if limit <= 0:
            return []
        return list(self._audit_log[-limit:])

    def get_record_for_token(self, raw_token: str) -> CapabilityRouteRecord | None:
        return self._records.get(_hash_token(raw_token))

    def clear(self) -> None:
        self._records.clear()
        self._audit_log.clear()

    @staticmethod
    def _normalize_scopes(scopes: set[str] | list[str] | tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted({str(scope).strip().lower() for scope in scopes if str(scope).strip()}))

    def _deny(
        self,
        reason_code: str,
        human_message: str,
        *,
        record: CapabilityRouteRecord | None = None,
        now: datetime,
    ) -> CapabilityRouteDecision:
        audit_event_id = self._audit(
            action="capability_route.token.validate",
            record=record,
            reason_code=reason_code,
            now=now,
        )
        return CapabilityRouteDecision(
            allowed=False,
            reason_code=reason_code,
            human_message=human_message,
            route_id=record.route_id if record else None,
            consumer_id=record.consumer_id if record else None,
            scopes=record.scopes if record else (),
            audit_event_id=audit_event_id,
        )

    def _audit(
        self,
        *,
        action: str,
        record: CapabilityRouteRecord | None,
        reason_code: str,
        now: datetime,
        metadata: dict[str, str] | None = None,
    ) -> str:
        event_id = uuid.uuid4().hex
        self._audit_log.append(CapabilityRouteAuditEvent(
            event_id=event_id,
            action=action,
            route_id=record.route_id if record else None,
            consumer_id=record.consumer_id if record else None,
            reason_code=reason_code,
            created_at=now,
            metadata=metadata or {},
        ))
        if len(self._audit_log) > self._max_audit:
            self._audit_log = self._audit_log[-self._max_audit:]
        return event_id


capability_route_service = CapabilityRouteService()
