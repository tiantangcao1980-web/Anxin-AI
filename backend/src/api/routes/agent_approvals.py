"""Agent approval routes for governed high-risk AI capability execution."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.agent_governance import AgentApproval
from src.models.user import User
from src.services.agent_approval_service import (
    AUTHORIZED_APPROVER_ROLES,
    PENDING_STATUS,
    AgentApprovalDecision,
    AgentApprovalService,
)

router = APIRouter()

RouteResponse = dict[str, Any]


class AgentApprovalRequestBody(BaseModel):
    """Create a high-risk agent approval request."""

    action_type: str = Field(..., min_length=1, max_length=80)
    risk_level: str = Field(default="l3", min_length=1, max_length=20)
    route_key: str | None = Field(default=None, max_length=160)
    route_id: str | None = None
    payload: dict[str, Any] | None = None
    expires_at: datetime | None = None


class AgentApprovalDecisionBody(BaseModel):
    """Approve or reject a high-risk agent approval."""

    note: str | None = Field(default=None, max_length=2000)


class AgentApprovalRevokeBody(BaseModel):
    """Revoke a previously approved high-risk agent approval."""

    reason: str = Field(..., min_length=1, max_length=2000)


class AgentApprovalValidateBody(BaseModel):
    """Validate an approval before high-risk execution."""

    approval_id: str | None = None
    action_type: str = Field(..., min_length=1, max_length=80)
    route_key: str | None = Field(default=None, max_length=160)
    route_id: str | None = None


def _org_id_for(user: User) -> str | None:
    return str(user.org_id) if user.org_id else None


def _role_for(user: User) -> str:
    return (user.role or "").strip().lower()


def _can_view_all_org_approvals(user: User) -> bool:
    return _role_for(user) in AUTHORIZED_APPROVER_ROLES


def _decision_to_payload(decision: AgentApprovalDecision) -> dict[str, Any]:
    return {
        "allowed": decision.allowed,
        "reason_code": decision.reason_code,
        "human_message": decision.human_message,
        "approval_id": decision.approval_id,
        "route_id": decision.route_id,
        "status": decision.status,
        "expires_at": decision.expires_at.isoformat() if decision.expires_at else None,
        "audit_event_id": decision.audit_event_id,
    }


def _approval_to_payload(approval: AgentApproval) -> dict[str, Any]:
    return {
        "id": approval.id,
        "org_id": approval.org_id,
        "route_id": approval.route_id,
        "requested_by": approval.requested_by,
        "decided_by": approval.decided_by,
        "action_type": approval.action_type,
        "risk_level": approval.risk_level,
        "status": approval.status,
        "payload": approval.payload,
        "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
        "resolved_at": approval.resolved_at.isoformat() if approval.resolved_at else None,
        "created_at": approval.created_at.isoformat() if approval.created_at else None,
        "updated_at": approval.updated_at.isoformat() if approval.updated_at else None,
    }


def _approval_scope_query(user: User) -> Any:
    org_id = _org_id_for(user)
    query = select(AgentApproval)
    if _role_for(user) == "super_admin":
        return query
    if _can_view_all_org_approvals(user):
        return query.where(AgentApproval.org_id == org_id)
    return query.where(
        AgentApproval.org_id == org_id,
        AgentApproval.requested_by == str(user.id),
    )


async def _get_scoped_approval(db: AsyncSession, *, approval_id: str, user: User) -> AgentApproval | None:
    query = _approval_scope_query(user).where(AgentApproval.id == approval_id)
    return (await db.execute(query)).scalar_one_or_none()


def _response_for_decision(decision: AgentApprovalDecision, *, success_message: str) -> RouteResponse:
    payload = _decision_to_payload(decision)
    if decision.allowed:
        return UnifiedResponse.success(data=payload, message=success_message)
    return UnifiedResponse.error(
        code=_error_code_for_reason(decision.reason_code),
        message=decision.human_message,
        data=payload,
    )


def _error_code_for_reason(reason_code: str) -> int:
    if reason_code in {"unknown_agent_approval", "unknown_capability_route"}:
        return 404
    if reason_code in {"approver_role_not_allowed", "approval_route_mismatch"}:
        return 403
    return 400


@router.post("", response_model=UnifiedResponse, summary="Create high-risk agent approval")
async def create_agent_approval(
    body: AgentApprovalRequestBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    org_id = _org_id_for(user)
    if not org_id:
        return UnifiedResponse.error(code=403, message="Current user is not attached to an organization.")

    service = AgentApprovalService(db)
    decision = await service.request_approval(
        org_id=org_id,
        action_type=body.action_type,
        risk_level=body.risk_level,
        requested_by=str(user.id),
        route_key=body.route_key,
        route_id=body.route_id,
        payload=body.payload,
        expires_at=body.expires_at,
    )
    await db.commit()
    return _response_for_decision(decision, success_message="Agent approval request created.")


@router.get("", response_model=UnifiedResponse, summary="List agent approvals")
async def list_agent_approvals(
    status: str | None = Query(default=None, max_length=30),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    scoped = _approval_scope_query(user)
    if status:
        scoped = scoped.where(AgentApproval.status == status)
    total_query = select(func.count()).select_from(scoped.subquery())
    total = (await db.execute(total_query)).scalar_one()
    rows = (
        await db.execute(
            scoped.order_by(AgentApproval.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
    ).scalars().all()
    return UnifiedResponse.success(
        data={
            "items": [_approval_to_payload(approval) for approval in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/pending/count", response_model=UnifiedResponse, summary="Count pending agent approvals")
async def count_pending_agent_approvals(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    query = _approval_scope_query(user).where(AgentApproval.status == PENDING_STATUS)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar_one()
    return UnifiedResponse.success(data={"pending": total})


@router.get("/{approval_id}", response_model=UnifiedResponse, summary="Get agent approval")
async def get_agent_approval(
    approval_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    approval = await _get_scoped_approval(db, approval_id=approval_id, user=user)
    if approval is None:
        return UnifiedResponse.error(code=404, message="Agent approval does not exist or is not visible.")
    return UnifiedResponse.success(data=_approval_to_payload(approval))


@router.post("/{approval_id}/approve", response_model=UnifiedResponse, summary="Approve agent approval")
async def approve_agent_approval(
    approval_id: str,
    body: AgentApprovalDecisionBody | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    return await _decide_agent_approval(
        approval_id=approval_id,
        decision="approve",
        body=body,
        db=db,
        user=user,
    )


@router.post("/{approval_id}/reject", response_model=UnifiedResponse, summary="Reject agent approval")
async def reject_agent_approval(
    approval_id: str,
    body: AgentApprovalDecisionBody | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    return await _decide_agent_approval(
        approval_id=approval_id,
        decision="reject",
        body=body,
        db=db,
        user=user,
    )


async def _decide_agent_approval(
    *,
    approval_id: str,
    decision: Literal["approve", "reject"],
    body: AgentApprovalDecisionBody | None,
    db: AsyncSession,
    user: User,
) -> RouteResponse:
    org_id = _org_id_for(user)
    if not org_id:
        return UnifiedResponse.error(code=403, message="Current user is not attached to an organization.")
    service = AgentApprovalService(db)
    result = await service.decide_approval(
        org_id=org_id,
        approval_id=approval_id,
        decision=decision,
        decided_by=str(user.id),
        decider_role=_role_for(user),
        note=body.note if body else None,
    )
    await db.commit()
    return _response_for_decision(result, success_message=f"Agent approval {result.status}.")


@router.post("/{approval_id}/revoke", response_model=UnifiedResponse, summary="Revoke agent approval")
async def revoke_agent_approval(
    approval_id: str,
    body: AgentApprovalRevokeBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    org_id = _org_id_for(user)
    if not org_id:
        return UnifiedResponse.error(code=403, message="Current user is not attached to an organization.")
    service = AgentApprovalService(db)
    result = await service.revoke_approval(
        org_id=org_id,
        approval_id=approval_id,
        revoked_by=str(user.id),
        revoker_role=_role_for(user),
        reason=body.reason,
    )
    await db.commit()
    return _response_for_decision(result, success_message="Agent approval revoked.")


@router.post("/validate", response_model=UnifiedResponse, summary="Validate high-risk agent approval")
async def validate_agent_approval(
    body: AgentApprovalValidateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    org_id = _org_id_for(user)
    if not org_id:
        return UnifiedResponse.error(code=403, message="Current user is not attached to an organization.")
    service = AgentApprovalService(db)
    result = await service.validate_approval(
        org_id=org_id,
        approval_id=body.approval_id,
        action_type=body.action_type,
        route_key=body.route_key,
        route_id=body.route_id,
        actor_user_id=str(user.id),
        actor_type="api_user",
    )
    await db.commit()
    return _response_for_decision(
        result,
        success_message="High-risk agent approval is valid.",
    )
