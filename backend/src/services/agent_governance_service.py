"""Database-backed agent governance service primitives."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_governance import (
    AgentAuditEvent,
    CapabilityRoute,
    CapabilityRouteTokenLease,
)

DEFAULT_AGENT_ROUTE_TOKEN_TTL_SECONDS = 15 * 60
MAX_AGENT_ROUTE_TOKEN_TTL_SECONDS = 60 * 60
ACTIVE_ROUTE_STATUSES = {"active", "enabled"}
SENSITIVE_METADATA_FRAGMENTS = ("token", "secret", "password", "credential", "api_key")


@dataclass(frozen=True)
class AgentRouteTokenIssue:
    allowed: bool
    reason_code: str
    human_message: str
    token: str | None = None
    route_id: str | None = None
    consumer_id: str | None = None
    scopes: tuple[str, ...] = ()
    expires_at: datetime | None = None
    audit_event_id: str | None = None


@dataclass(frozen=True)
class AgentCapabilityDecision:
    allowed: bool
    reason_code: str
    human_message: str
    route_id: str | None = None
    consumer_id: str | None = None
    scopes: tuple[str, ...] = ()
    audit_event_id: str | None = None


@dataclass(frozen=True)
class AgentRouteRevocation:
    revoked: bool
    reason_code: str
    human_message: str
    route_id: str | None = None
    revoked_lease_count: int = 0
    audit_event_id: str | None = None


class AgentGovernanceService:
    """Persists governed capability routes, leases, and audit decisions."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_capability_route(
        self,
        *,
        org_id: str,
        route_key: str,
        route_type: str,
        allowed_consumers: list[str] | set[str] | tuple[str, ...],
        allowed_scopes: list[str] | set[str] | tuple[str, ...],
        provider: str | None = None,
        risk_level: str = "l1",
        status: str = "enabled",
        token_ttl_seconds: int = DEFAULT_AGENT_ROUTE_TOKEN_TTL_SECONDS,
        policy: dict[str, Any] | None = None,
    ) -> CapabilityRoute:
        route = CapabilityRoute(
            org_id=org_id,
            route_key=_required(route_key, "route_key"),
            route_type=_required(route_type, "route_type"),
            provider=provider,
            risk_level=risk_level,
            status=status,
            allowed_consumers=list(_normalize_values(allowed_consumers)),
            allowed_scopes=list(_normalize_values(allowed_scopes)),
            token_ttl_seconds=_clamp_ttl(token_ttl_seconds),
            policy=policy,
        )
        self.db.add(route)
        await self.db.flush()
        return route

    async def issue_route_token(
        self,
        *,
        org_id: str,
        route_key: str,
        consumer_id: str,
        requested_scopes: list[str] | set[str] | tuple[str, ...],
        ttl_seconds: int | None = None,
        actor_user_id: str | None = None,
        actor_type: str = "agent_worker",
        now: datetime | None = None,
    ) -> AgentRouteTokenIssue:
        issued_at = now or _now()
        route = await self._get_route_by_key(org_id=org_id, route_key=route_key)
        normalized_scopes = _normalize_values(requested_scopes)
        if route is None:
            event = self._audit(
                org_id=org_id,
                action="capability_route.token.issue",
                status="denied",
                reason_code="unknown_capability_route",
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                metadata={"route_key": route_key},
                now=issued_at,
            )
            await self.db.flush()
            return AgentRouteTokenIssue(
                allowed=False,
                reason_code="unknown_capability_route",
                human_message="能力路由不存在或不属于当前组织",
                audit_event_id=event.id,
            )

        denial = self._route_denial(route)
        if denial:
            event = self._audit_route_decision(
                route=route,
                action="capability_route.token.issue",
                status="denied",
                reason_code=denial,
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                metadata={"consumer_id": consumer_id},
                now=issued_at,
            )
            await self.db.flush()
            return AgentRouteTokenIssue(False, denial, _reason_message(denial), route_id=route.id, audit_event_id=event.id)

        normalized_consumer = _required(consumer_id, "consumer_id")
        if not _consumer_allowed(normalized_consumer, route.allowed_consumers or []):
            event = self._audit_route_decision(
                route=route,
                action="capability_route.token.issue",
                status="denied",
                reason_code="consumer_not_allowed",
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                metadata={"consumer_id": normalized_consumer},
                now=issued_at,
            )
            await self.db.flush()
            return AgentRouteTokenIssue(
                False,
                "consumer_not_allowed",
                "该 Agent/Worker 不在能力路由允许列表内",
                route_id=route.id,
                consumer_id=normalized_consumer,
                audit_event_id=event.id,
            )

        missing_scopes = set(normalized_scopes) - set(route.allowed_scopes or [])
        if not normalized_scopes or missing_scopes:
            event = self._audit_route_decision(
                route=route,
                action="capability_route.token.issue",
                status="denied",
                reason_code="missing_route_scope",
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                metadata={"scope_count": str(len(normalized_scopes))},
                now=issued_at,
            )
            await self.db.flush()
            return AgentRouteTokenIssue(
                False,
                "missing_route_scope",
                "能力路由未授权请求的 scope",
                route_id=route.id,
                consumer_id=normalized_consumer,
                audit_event_id=event.id,
            )

        ttl = _clamp_ttl(ttl_seconds or route.token_ttl_seconds)
        raw_token = f"anxin_route_{secrets.token_urlsafe(32)}"
        lease = CapabilityRouteTokenLease(
            org_id=org_id,
            route_id=route.id,
            consumer_id=normalized_consumer,
            token_hash=_hash_token(raw_token),
            scopes=list(normalized_scopes),
            expires_at=issued_at + timedelta(seconds=ttl),
        )
        self.db.add(lease)
        event = self._audit_route_decision(
            route=route,
            action="capability_route.token.issue",
            status="success",
            reason_code="issued",
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            metadata={"consumer_id": normalized_consumer, "scope_count": str(len(normalized_scopes))},
            now=issued_at,
        )
        await self.db.flush()
        return AgentRouteTokenIssue(
            allowed=True,
            reason_code="issued",
            human_message="能力路由 token 已签发",
            token=raw_token,
            route_id=route.id,
            consumer_id=normalized_consumer,
            scopes=normalized_scopes,
            expires_at=lease.expires_at,
            audit_event_id=event.id,
        )

    async def validate_route_token(
        self,
        *,
        org_id: str,
        raw_token: str | None,
        required_scope: str | None = None,
        actor_user_id: str | None = None,
        actor_type: str = "agent_worker",
        now: datetime | None = None,
    ) -> AgentCapabilityDecision:
        checked_at = now or _now()
        if not raw_token:
            event = self._audit(
                org_id=org_id,
                action="capability_route.token.validate",
                status="denied",
                reason_code="missing_route_token",
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                now=checked_at,
            )
            await self.db.flush()
            return AgentCapabilityDecision(False, "missing_route_token", "缺少能力路由 token", audit_event_id=event.id)

        lease_route = await self._get_lease_and_route(org_id=org_id, raw_token=raw_token)
        if lease_route is None:
            event = self._audit(
                org_id=org_id,
                action="capability_route.token.validate",
                status="denied",
                reason_code="unknown_route_token",
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                now=checked_at,
            )
            await self.db.flush()
            return AgentCapabilityDecision(False, "unknown_route_token", "能力路由 token 无效", audit_event_id=event.id)

        lease, route = lease_route
        denial = self._lease_denial(lease=lease, route=route, required_scope=required_scope, now=checked_at)
        if denial:
            event = self._audit_route_decision(
                route=route,
                action="capability_route.token.validate",
                status="denied",
                reason_code=denial,
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                metadata={"consumer_id": lease.consumer_id},
                now=checked_at,
            )
            await self.db.flush()
            return AgentCapabilityDecision(
                False,
                denial,
                _reason_message(denial),
                route_id=route.id,
                consumer_id=lease.consumer_id,
                scopes=tuple(lease.scopes or []),
                audit_event_id=event.id,
            )

        lease.last_validated_at = checked_at
        event = self._audit_route_decision(
            route=route,
            action="capability_route.token.validate",
            status="success",
            reason_code="allowed",
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            metadata={"consumer_id": lease.consumer_id, "required_scope": (required_scope or "").strip().lower()},
            now=checked_at,
        )
        await self.db.flush()
        return AgentCapabilityDecision(
            True,
            "allowed",
            "能力路由已授权",
            route_id=route.id,
            consumer_id=lease.consumer_id,
            scopes=tuple(lease.scopes or []),
            audit_event_id=event.id,
        )

    async def revoke_capability_route(
        self,
        *,
        org_id: str,
        route_key: str,
        reason: str = "revoked",
        actor_user_id: str | None = None,
        actor_type: str = "user",
        now: datetime | None = None,
    ) -> AgentRouteRevocation:
        revoked_at = now or _now()
        route = await self._get_route_by_key(org_id=org_id, route_key=route_key)
        if route is None:
            event = self._audit(
                org_id=org_id,
                action="capability_route.revoke",
                status="denied",
                reason_code="unknown_capability_route",
                actor_user_id=actor_user_id,
                actor_type=actor_type,
                metadata={"route_key": route_key, "reason": reason},
                now=revoked_at,
            )
            await self.db.flush()
            return AgentRouteRevocation(False, "unknown_capability_route", "能力路由不存在", audit_event_id=event.id)

        route.status = "disabled"
        route.revoked_at = revoked_at
        route.revoked_reason = reason
        leases = (
            await self.db.execute(
                select(CapabilityRouteTokenLease).where(
                    CapabilityRouteTokenLease.org_id == org_id,
                    CapabilityRouteTokenLease.route_id == route.id,
                    CapabilityRouteTokenLease.revoked_at.is_(None),
                )
            )
        ).scalars().all()
        for lease in leases:
            lease.revoked_at = revoked_at
            lease.revoked_reason = reason

        event = self._audit_route_decision(
            route=route,
            action="capability_route.revoke",
            status="success",
            reason_code="revoked",
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            metadata={"reason": reason, "revoked_lease_count": str(len(leases))},
            now=revoked_at,
        )
        await self.db.flush()
        return AgentRouteRevocation(
            True,
            "revoked",
            "能力路由已撤销",
            route_id=route.id,
            revoked_lease_count=len(leases),
            audit_event_id=event.id,
        )

    async def _get_route_by_key(self, *, org_id: str, route_key: str) -> CapabilityRoute | None:
        return (
            await self.db.execute(
                select(CapabilityRoute).where(
                    CapabilityRoute.org_id == org_id,
                    CapabilityRoute.route_key == route_key,
                )
            )
        ).scalar_one_or_none()

    async def _get_lease_and_route(
        self,
        *,
        org_id: str,
        raw_token: str,
    ) -> tuple[CapabilityRouteTokenLease, CapabilityRoute] | None:
        result = await self.db.execute(
            select(CapabilityRouteTokenLease, CapabilityRoute)
            .join(
                CapabilityRoute,
                and_(
                    CapabilityRouteTokenLease.org_id == CapabilityRoute.org_id,
                    CapabilityRouteTokenLease.route_id == CapabilityRoute.id,
                ),
            )
            .where(
                CapabilityRouteTokenLease.org_id == org_id,
                CapabilityRouteTokenLease.token_hash == _hash_token(raw_token),
            )
        )
        row = result.one_or_none()
        if row is None:
            return None
        return row[0], row[1]

    def _route_denial(self, route: CapabilityRoute) -> str | None:
        if route.revoked_at is not None:
            return "capability_route_revoked"
        if route.status not in ACTIVE_ROUTE_STATUSES:
            return "capability_route_disabled"
        return None

    def _lease_denial(
        self,
        *,
        lease: CapabilityRouteTokenLease,
        route: CapabilityRoute,
        required_scope: str | None,
        now: datetime,
    ) -> str | None:
        route_denial = self._route_denial(route)
        if route_denial:
            return route_denial
        if lease.revoked_at is not None:
            return "route_token_revoked"
        if _ensure_aware(lease.expires_at) <= now:
            return "route_token_expired"
        normalized_scope = (required_scope or "").strip().lower()
        if normalized_scope and normalized_scope not in (lease.scopes or []):
            return "missing_route_scope"
        return None

    def _audit_route_decision(
        self,
        *,
        route: CapabilityRoute,
        action: str,
        status: str,
        reason_code: str,
        actor_user_id: str | None,
        actor_type: str,
        metadata: dict[str, Any] | None = None,
        now: datetime,
    ) -> AgentAuditEvent:
        return self._audit(
            org_id=route.org_id,
            action=action,
            status=status,
            reason_code=reason_code,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            route_id=route.id,
            resource_type="capability_route",
            resource_id=route.id,
            resource_snapshot={
                "route_key": route.route_key,
                "route_type": route.route_type,
                "risk_level": route.risk_level,
                "status": route.status,
            },
            metadata=metadata,
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
            metadata_json=_sanitize_metadata(metadata),
            created_at=now,
        )
        self.db.add(event)
        return event


def _now() -> datetime:
    return datetime.now(UTC)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _required(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} is required")
    return normalized


def _normalize_values(values: list[str] | set[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip().lower() for value in values if str(value).strip()}))


def _consumer_allowed(consumer_id: str, allowed_consumers: list[str]) -> bool:
    normalized = consumer_id.strip().lower()
    allowed = {str(consumer).strip().lower() for consumer in allowed_consumers}
    return "*" in allowed or normalized in allowed


def _clamp_ttl(ttl_seconds: int) -> int:
    return max(1, min(int(ttl_seconds), MAX_AGENT_ROUTE_TOKEN_TTL_SECONDS))


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, str] | None:
    if not metadata:
        return None
    sanitized: dict[str, str] = {}
    for key, value in metadata.items():
        normalized_key = str(key)
        if any(fragment in normalized_key.lower() for fragment in SENSITIVE_METADATA_FRAGMENTS):
            sanitized[normalized_key] = "[redacted]"
        else:
            sanitized[normalized_key] = str(value)
    return sanitized


def _reason_message(reason_code: str) -> str:
    return {
        "capability_route_disabled": "能力路由未启用",
        "capability_route_revoked": "能力路由已撤销",
        "route_token_revoked": "能力路由 token 已撤销",
        "route_token_expired": "能力路由 token 已过期",
        "missing_route_scope": "能力路由缺少所需 scope",
    }.get(reason_code, "能力路由请求被拒绝")
