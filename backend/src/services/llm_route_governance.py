"""DB-backed route-token guard for LLM runtime calls."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings

LLM_ROUTE_SCOPE = "llm:chat"
DEFAULT_LLM_ROUTE_KEY = "llm-chat"
DEFAULT_LLM_ROUTE_TYPE = "llm"
COMMERCIAL_ENVIRONMENTS = {"staging", "production"}


class LLMRouteAuthorizationError(PermissionError):
    """Raised when a real LLM call lacks a valid governed route token."""


def llm_route_governance_required() -> bool:
    return bool(
        settings.LLM_ROUTE_TOKEN_REQUIRED or settings.ENVIRONMENT.lower() in COMMERCIAL_ENVIRONMENTS
    )


def llm_route_consumer_for_user(user_id: str) -> str:
    return f"user:{user_id}"


def build_llm_route_context(
    *,
    db: AsyncSession,
    org_id: str | None,
    route_token: str | None,
    consumer_id: str | None,
    actor_user_id: str | None,
) -> dict[str, Any]:
    return {
        "db": db,
        "org_id": org_id,
        "route_token": route_token,
        "consumer_id": consumer_id,
        "actor_user_id": actor_user_id,
    }


async def authorize_llm_route_context(route_context: dict[str, Any] | None) -> None:
    context = route_context or {}
    db = context.get("db")
    try:
        await authorize_llm_route(
            org_id=context.get("org_id"),
            route_token=context.get("route_token"),
            consumer_id=context.get("consumer_id"),
            actor_user_id=context.get("actor_user_id"),
            db=db,
        )
    finally:
        if context.get("commit_after_authorize") and db is not None:
            await db.commit()


async def authorize_llm_route(
    *,
    org_id: str | None,
    route_token: str | None,
    consumer_id: str | None,
    actor_user_id: str | None = None,
    db: AsyncSession | None,
    required_scope: str = LLM_ROUTE_SCOPE,
) -> None:
    if not llm_route_governance_required():
        return

    missing = [
        name
        for name, value in {
            "org_id": org_id,
            "consumer_id": consumer_id,
            "route_token": route_token,
            "db": db,
        }.items()
        if value is None or (isinstance(value, str) and not value.strip())
    ]
    if missing:
        raise LLMRouteAuthorizationError(
            "LLM route token required before model call; missing " + ", ".join(sorted(missing))
        )

    from src.services.agent_governance_service import AgentGovernanceService

    assert db is not None
    assert org_id is not None
    assert route_token is not None
    assert consumer_id is not None
    decision = await AgentGovernanceService(db).validate_route_token(
        org_id=org_id,
        raw_token=route_token,
        required_scope=required_scope,
        consumer_id=consumer_id,
        actor_user_id=actor_user_id,
        actor_type="agent_worker",
    )
    if not decision.allowed:
        raise LLMRouteAuthorizationError(
            f"LLM route token denied before model call: {decision.reason_code}"
        )
