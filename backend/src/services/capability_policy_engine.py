"""Unified capability policy decisions for governed agent execution."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.agent_governance import AgentAuditEvent, CapabilityRoute
from src.services.agent_approval_service import AgentApprovalService

ACTIVE_ROUTE_STATUSES = {"active", "enabled"}
HIGH_RISK_LEVEL = 3
NETWORKED_ROUTE_TYPES = {
    "browser",
    "cli",
    "cloud-llm",
    "desktop-control",
    "external-api",
    "llm",
    "mcp",
    "web",
}
LOCAL_ONLY_MODES = {"top_secret", "top-secret", "local", "local_only", "offline"}
SENSITIVE_METADATA_FRAGMENTS = ("token", "secret", "password", "credential", "api_key")


@dataclass(frozen=True)
class CapabilityPolicyDecision:
    """Result returned by the unified capability policy engine."""

    allowed: bool
    reason_code: str
    human_message: str
    required_action: str | None = None
    route_id: str | None = None
    approval_id: str | None = None
    audit_event_id: str | None = None


class CapabilityPolicyEngine:
    """Checks subscription, role, permission, privacy, device, channel, and approval gates."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def can_execute_capability(
        self,
        *,
        org_id: str,
        capability_key: str,
        actor_user_id: str | None,
        actor_role: str | None,
        permissions: Iterable[str] | None = None,
        subscription_features: Mapping[str, Any] | Iterable[str] | None = None,
        risk_level: str = "l1",
        data_scope: str = "internal",
        privacy_mode: str = "hybrid",
        device_trusted: bool = True,
        channel_policy: Mapping[str, Any] | None = None,
        route_key: str | None = None,
        route_id: str | None = None,
        required_feature: str | None = None,
        required_permissions: Iterable[str] | None = None,
        allowed_roles: Iterable[str] | None = None,
        approval_id: str | None = None,
        action: str = "execute",
        now: datetime | None = None,
    ) -> CapabilityPolicyDecision:
        checked_at = now or _now()
        normalized_capability = _required(capability_key, "capability_key")
        route = await self._resolve_route(org_id=org_id, route_key=route_key, route_id=route_id)
        if (route_key or route_id) and route is None:
            return await self._deny(
                org_id=org_id,
                capability_key=normalized_capability,
                reason_code="unknown_capability_route",
                human_message="Capability route does not exist for this organization.",
                required_action="contact_admin",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                metadata={"route_key": route_key or "", "route_id": route_id or ""},
                now=checked_at,
            )

        if route is not None:
            route_denial = _route_denial(route)
            if route_denial:
                return await self._deny(
                    org_id=org_id,
                    capability_key=normalized_capability,
                    reason_code=route_denial,
                    human_message=_reason_message(route_denial),
                    required_action="contact_admin",
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    route_id=route.id,
                    now=checked_at,
                )

        route_policy = route.policy if route is not None and isinstance(route.policy, dict) else {}
        route_type = (route.route_type if route is not None else "").strip().lower()
        effective_risk = max(_risk_rank(risk_level), _risk_rank(route.risk_level if route else "l1"))
        required_feature = required_feature or _string_policy(route_policy, "required_feature")
        required_permissions = tuple(required_permissions or route_policy.get("required_permissions") or ())
        allowed_roles = tuple(allowed_roles or route_policy.get("allowed_roles") or ())

        feature_denial = _feature_denial(
            subscription_features=subscription_features,
            required_feature=required_feature,
        )
        if feature_denial:
            return await self._deny(
                org_id=org_id,
                capability_key=normalized_capability,
                reason_code=feature_denial,
                human_message="Current subscription does not include this capability.",
                required_action="subscribe",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                route_id=route.id if route else None,
                now=checked_at,
            )

        role_denial = _role_denial(actor_role=actor_role, allowed_roles=allowed_roles)
        if role_denial:
            return await self._deny(
                org_id=org_id,
                capability_key=normalized_capability,
                reason_code=role_denial,
                human_message="Current role cannot execute this capability.",
                required_action="contact_admin",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                route_id=route.id if route else None,
                now=checked_at,
            )

        missing_permissions = _missing_permissions(
            permissions=permissions,
            required_permissions=required_permissions,
        )
        if missing_permissions:
            return await self._deny(
                org_id=org_id,
                capability_key=normalized_capability,
                reason_code="missing_permission",
                human_message=f"Current actor lacks permissions: {', '.join(missing_permissions)}.",
                required_action="contact_admin",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                route_id=route.id if route else None,
                metadata={"missing_permission_count": str(len(missing_permissions))},
                now=checked_at,
            )

        privacy_denial = _privacy_denial(
            privacy_mode=privacy_mode,
            data_scope=data_scope,
            route_type=route_type,
            risk_rank=effective_risk,
        )
        if privacy_denial:
            return await self._deny(
                org_id=org_id,
                capability_key=normalized_capability,
                reason_code=privacy_denial,
                human_message="Current privacy mode does not allow this capability.",
                required_action="switch_mode",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                route_id=route.id if route else None,
                now=checked_at,
            )

        if _requires_trusted_device(route_policy=route_policy, route_type=route_type, risk_rank=effective_risk):
            if not device_trusted:
                return await self._deny(
                    org_id=org_id,
                    capability_key=normalized_capability,
                    reason_code="untrusted_device",
                    human_message="This capability requires a trusted device.",
                    required_action="pair_device",
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    route_id=route.id if route else None,
                    now=checked_at,
                )

        if not _channel_allows(channel_policy=channel_policy, action=action, capability_key=normalized_capability):
            return await self._deny(
                org_id=org_id,
                capability_key=normalized_capability,
                reason_code="channel_policy_denied",
                human_message="Current channel policy does not allow this action.",
                required_action="contact_admin",
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                route_id=route.id if route else None,
                now=checked_at,
            )

        requires_approval = effective_risk >= HIGH_RISK_LEVEL or bool(route_policy.get("requires_approval"))
        if requires_approval:
            if not approval_id:
                return await self._deny(
                    org_id=org_id,
                    capability_key=normalized_capability,
                    reason_code="approval_required",
                    human_message="This high-risk capability requires human approval.",
                    required_action="request_approval",
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    route_id=route.id if route else None,
                    now=checked_at,
                )

            approval = await AgentApprovalService(self.db).validate_approval(
                org_id=org_id,
                approval_id=approval_id,
                action_type=normalized_capability,
                route_key=route.route_key if route is not None else route_key,
                route_id=route.id if route is not None else route_id,
                actor_user_id=actor_user_id,
                actor_type="capability_policy_engine",
                now=checked_at,
            )
            if not approval.allowed:
                return await self._deny(
                    org_id=org_id,
                    capability_key=normalized_capability,
                    reason_code=approval.reason_code,
                    human_message=approval.human_message,
                    required_action="request_approval",
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    route_id=route.id if route else approval.route_id,
                    approval_id=approval_id,
                    metadata={"approval_audit_event_id": approval.audit_event_id or ""},
                    now=checked_at,
                )

        return await self._allow(
            org_id=org_id,
            capability_key=normalized_capability,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            route_id=route.id if route else None,
            approval_id=approval_id,
            metadata={"risk_rank": str(effective_risk), "route_type": route_type},
            now=checked_at,
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

    async def _allow(
        self,
        *,
        org_id: str,
        capability_key: str,
        actor_user_id: str | None,
        actor_role: str | None,
        route_id: str | None = None,
        approval_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime,
    ) -> CapabilityPolicyDecision:
        event = self._audit(
            org_id=org_id,
            capability_key=capability_key,
            status="success",
            reason_code="allowed",
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            route_id=route_id,
            approval_id=approval_id,
            metadata=metadata,
            now=now,
        )
        await self.db.flush()
        return CapabilityPolicyDecision(
            allowed=True,
            reason_code="allowed",
            human_message="Capability execution is allowed.",
            route_id=route_id,
            approval_id=approval_id,
            audit_event_id=event.id,
        )

    async def _deny(
        self,
        *,
        org_id: str,
        capability_key: str,
        reason_code: str,
        human_message: str,
        required_action: str,
        actor_user_id: str | None,
        actor_role: str | None,
        route_id: str | None = None,
        approval_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime,
    ) -> CapabilityPolicyDecision:
        event = self._audit(
            org_id=org_id,
            capability_key=capability_key,
            status="denied",
            reason_code=reason_code,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            route_id=route_id,
            approval_id=approval_id,
            metadata=metadata,
            now=now,
        )
        await self.db.flush()
        return CapabilityPolicyDecision(
            allowed=False,
            reason_code=reason_code,
            human_message=human_message,
            required_action=required_action,
            route_id=route_id,
            approval_id=approval_id,
            audit_event_id=event.id,
        )

    def _audit(
        self,
        *,
        org_id: str,
        capability_key: str,
        status: str,
        reason_code: str,
        actor_user_id: str | None,
        actor_role: str | None,
        route_id: str | None,
        approval_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        now: datetime,
    ) -> AgentAuditEvent:
        event = AgentAuditEvent(
            org_id=org_id,
            route_id=route_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            actor_snapshot={"role": (actor_role or "").strip().lower()},
            action="capability_policy.evaluate",
            status=status,
            reason_code=reason_code,
            resource_type="capability",
            resource_id=capability_key,
            resource_snapshot={"capability_key": capability_key, "approval_id": approval_id},
            metadata_json=_sanitize_metadata(metadata),
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


def _route_denial(route: CapabilityRoute) -> str | None:
    if route.revoked_at is not None:
        return "capability_route_revoked"
    if route.status not in ACTIVE_ROUTE_STATUSES:
        return "capability_route_disabled"
    return None


def _risk_rank(value: str | None) -> int:
    normalized = (value or "").strip().lower().replace("-", "_")
    aliases = {
        "l0": 0,
        "none": 0,
        "read": 1,
        "read_only": 1,
        "readonly": 1,
        "low": 1,
        "l1": 1,
        "write": 2,
        "medium": 2,
        "l2": 2,
        "execute": 3,
        "high": 3,
        "l3": 3,
        "external": 3,
        "external_send": 3,
        "critical": 4,
        "high_risk": 4,
        "l4": 4,
        "forbidden": 5,
        "l5": 5,
    }
    return aliases.get(normalized, 4)


def _active_features(features: Mapping[str, Any] | Iterable[str] | None) -> set[str]:
    if features is None:
        return set()
    if isinstance(features, Mapping):
        active: set[str] = set()
        for key, value in features.items():
            if value is True or (isinstance(value, int) and value > 0):
                active.add(str(key).strip().lower())
            elif isinstance(value, str) and value.strip():
                active.add(str(key).strip().lower())
            elif isinstance(value, Iterable) and not isinstance(value, str) and list(value):
                active.add(str(key).strip().lower())
        return active
    return {str(item).strip().lower() for item in features if str(item).strip()}


def _feature_denial(
    *,
    subscription_features: Mapping[str, Any] | Iterable[str] | None,
    required_feature: str | None,
) -> str | None:
    required = (required_feature or "").strip().lower()
    if not required:
        return None
    active = _active_features(subscription_features)
    if "*" in active or "all" in active or required in active:
        return None
    return "missing_subscription_feature"


def _role_denial(*, actor_role: str | None, allowed_roles: Iterable[str] | None) -> str | None:
    allowed = _normalized_set(allowed_roles)
    if not allowed:
        return None
    role = (actor_role or "").strip().lower()
    if role in allowed:
        return None
    return "role_not_allowed"


def _missing_permissions(
    *,
    permissions: Iterable[str] | None,
    required_permissions: Iterable[str] | None,
) -> list[str]:
    required = _normalized_set(required_permissions)
    if not required:
        return []
    current = _normalized_set(permissions)
    return sorted(required - current)


def _privacy_denial(
    *,
    privacy_mode: str,
    data_scope: str,
    route_type: str,
    risk_rank: int,
) -> str | None:
    mode = privacy_mode.strip().lower().replace("-", "_")
    scope = data_scope.strip().lower().replace("-", "_")
    if mode not in LOCAL_ONLY_MODES:
        return None
    if risk_rank >= HIGH_RISK_LEVEL:
        return "privacy_mode_denied"
    if route_type in NETWORKED_ROUTE_TYPES:
        return "privacy_mode_denied"
    if scope in {"external", "cloud", "public_network", "third_party"}:
        return "privacy_mode_denied"
    return None


def _requires_trusted_device(
    *,
    route_policy: Mapping[str, Any],
    route_type: str,
    risk_rank: int,
) -> bool:
    if "requires_trusted_device" in route_policy:
        return bool(route_policy["requires_trusted_device"])
    return risk_rank >= HIGH_RISK_LEVEL or route_type in {"browser", "cli", "desktop-control"}


def _channel_allows(
    *,
    channel_policy: Mapping[str, Any] | None,
    action: str,
    capability_key: str,
) -> bool:
    if not channel_policy:
        return True
    if channel_policy.get("allowed") is False or channel_policy.get("allow_execute") is False:
        return False
    normalized_action = action.strip().lower()
    normalized_capability = capability_key.strip().lower()
    denied_actions = _normalized_set(channel_policy.get("denied_actions"))
    if normalized_action in denied_actions or normalized_capability in denied_actions:
        return False
    allowed_actions = _normalized_set(channel_policy.get("allowed_actions"))
    if allowed_actions and normalized_action not in allowed_actions and normalized_capability not in allowed_actions:
        return False
    return True


def _string_policy(policy: Mapping[str, Any], key: str) -> str | None:
    value = policy.get(key)
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalized_set(values: Iterable[str] | Any | None) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        return {values.strip().lower()} if values.strip() else set()
    if not isinstance(values, Iterable):
        return {str(values).strip().lower()} if str(values).strip() else set()
    return {str(value).strip().lower() for value in values if str(value).strip()}


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
        "capability_route_disabled": "Capability route is disabled.",
        "capability_route_revoked": "Capability route has been revoked.",
    }.get(reason_code, "Capability execution was denied.")
