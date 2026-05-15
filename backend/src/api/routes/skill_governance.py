"""Skill governance routes for durable Skill evolution lifecycle control."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.core.responses import UnifiedResponse
from src.models.agent_governance import (
    SkillConnectorConfig,
    SkillGovernanceAuditEvent,
    SkillGovernanceProposal,
)
from src.models.user import User
from src.services.skill_evolution_service import (
    AUTHORIZED_SKILL_APPROVER_ROLES,
    SkillEvolutionError,
)
from src.services.skill_governance_service import SkillGovernanceService, connector_credential_keys

router = APIRouter()

RouteResponse = dict[str, Any]


class SkillGovernanceProposalBody(BaseModel):
    """Create a governed Skill evolution proposal."""

    skill_name: str = Field(..., min_length=1, max_length=160)
    proposed_version: str = Field(..., min_length=1, max_length=80)
    source: str = Field(..., min_length=1, max_length=200)
    current_version: str | None = Field(default=None, max_length=80)
    risk_level: str = Field(default="medium", min_length=1, max_length=20)


class SkillGovernanceEvalBody(BaseModel):
    """Record required eval results for a Skill proposal."""

    checks: dict[str, bool] = Field(..., min_length=1)


class SkillGovernanceGrayReleaseBody(BaseModel):
    """Release an approved Skill proposal to an org-scoped enabled version."""

    percentage: int = Field(..., ge=1, le=100)


class SkillGovernanceRollbackBody(BaseModel):
    """Rollback a released or approved Skill proposal."""

    reason: str = Field(..., min_length=1, max_length=2000)


class SkillConnectorConfigBody(BaseModel):
    """Create a governed Skill connector credential config."""

    skill_name: str = Field(..., min_length=1, max_length=160)
    connector_name: str = Field(..., min_length=1, max_length=120)
    connector_type: str = Field(default="http_api", min_length=1, max_length=60)
    endpoint_url: str | None = Field(default=None, max_length=500)
    auth_type: str = Field(default="api_key", min_length=1, max_length=40)
    credentials: dict[str, str] | None = Field(default=None)
    is_enabled: bool = Field(default=True)


class SkillConnectorConfigUpdateBody(BaseModel):
    """Update a governed Skill connector credential config."""

    skill_name: str | None = Field(default=None, min_length=1, max_length=160)
    connector_name: str | None = Field(default=None, min_length=1, max_length=120)
    connector_type: str | None = Field(default=None, min_length=1, max_length=60)
    endpoint_url: str | None = Field(default=None, max_length=500)
    auth_type: str | None = Field(default=None, min_length=1, max_length=40)
    credentials: dict[str, str] | None = Field(default=None)
    is_enabled: bool | None = Field(default=None)


def _org_id_for(user: User) -> str | None:
    return str(user.org_id) if user.org_id else None


def _role_for(user: User) -> str:
    return (user.role or "").strip().lower()


def _can_administer_skill_governance(user: User) -> bool:
    return _role_for(user) in AUTHORIZED_SKILL_APPROVER_ROLES


def _proposal_scope_query(user: User) -> Any:
    query = select(SkillGovernanceProposal)
    if _role_for(user) == "super_admin":
        return query
    org_id = _org_id_for(user)
    if _can_administer_skill_governance(user):
        return query.where(SkillGovernanceProposal.org_id == org_id)
    return query.where(
        SkillGovernanceProposal.org_id == org_id,
        SkillGovernanceProposal.created_by == str(user.id),
    )


async def _get_scoped_proposal(
    db: AsyncSession,
    *,
    proposal_id: str,
    user: User,
) -> SkillGovernanceProposal | None:
    query = _proposal_scope_query(user).where(SkillGovernanceProposal.id == proposal_id)
    return (await db.execute(query)).scalar_one_or_none()


def _require_org(user: User) -> str | None:
    return _org_id_for(user)


def _require_admin(user: User) -> RouteResponse | None:
    if _can_administer_skill_governance(user):
        return None
    return UnifiedResponse.error(
        code=403,
        message="Only owner, boss, super admin, org admin, or admin can administer Skill governance.",
    )


def _proposal_to_payload(proposal: SkillGovernanceProposal) -> dict[str, Any]:
    return {
        "id": proposal.id,
        "org_id": proposal.org_id,
        "skill_name": proposal.skill_name,
        "current_version": proposal.current_version,
        "proposed_version": proposal.proposed_version,
        "source": proposal.source,
        "created_by": proposal.created_by,
        "created_by_role": proposal.created_by_role,
        "risk_level": proposal.risk_level,
        "status": proposal.status,
        "eval_results": proposal.eval_results,
        "approved_by": proposal.approved_by,
        "approver_role": proposal.approver_role,
        "approved_at": _loaded_isoformat(proposal, "approved_at"),
        "gray_percentage": proposal.gray_percentage,
        "released_at": _loaded_isoformat(proposal, "released_at"),
        "rolled_back_at": _loaded_isoformat(proposal, "rolled_back_at"),
        "rollback_reason": proposal.rollback_reason,
        "created_at": _loaded_isoformat(proposal, "created_at"),
        "updated_at": _loaded_isoformat(proposal, "updated_at"),
    }


def _audit_event_to_payload(event: SkillGovernanceAuditEvent) -> dict[str, Any]:
    return {
        "id": event.id,
        "org_id": event.org_id,
        "proposal_id": event.proposal_id,
        "actor": event.actor,
        "action": event.action,
        "status": event.status,
        "reason_code": event.reason_code,
        "resource_snapshot": event.resource_snapshot,
        "metadata": event.metadata_json,
        "created_at": _loaded_isoformat(event, "created_at"),
    }


def _connector_to_payload(config: SkillConnectorConfig) -> dict[str, Any]:
    return {
        "id": config.id,
        "org_id": config.org_id,
        "skill_name": config.skill_name,
        "connector_name": config.connector_name,
        "connector_type": config.connector_type,
        "endpoint_url": config.endpoint_url,
        "auth_type": config.auth_type,
        "credential_keys": connector_credential_keys(config),
        "is_enabled": config.is_enabled,
        "created_by": config.created_by,
        "updated_by": config.updated_by,
        "created_at": _loaded_isoformat(config, "created_at"),
        "updated_at": _loaded_isoformat(config, "updated_at"),
    }


def _loaded_isoformat(model: Any, field_name: str) -> str | None:
    value = getattr(model, "__dict__", {}).get(field_name)
    return value.isoformat() if value else None


def _error_response(error: SkillEvolutionError) -> RouteResponse:
    message = str(error)
    code = 403 if "not authorized" in message or "not found" in message else 400
    return UnifiedResponse.error(code=code, message=message)


@router.post(
    "/proposals", response_model=UnifiedResponse, summary="Create Skill governance proposal"
)
async def create_skill_governance_proposal(
    body: SkillGovernanceProposalBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        proposal = await SkillGovernanceService(db).create_proposal(
            org_id=org_id,
            skill_name=body.skill_name,
            proposed_version=body.proposed_version,
            source=body.source,
            created_by=str(user.id),
            created_by_role=_role_for(user) or "employee",
            current_version=body.current_version,
            risk_level=body.risk_level,
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    payload = _proposal_to_payload(proposal)
    await db.commit()
    return UnifiedResponse.success(data=payload, message="Skill proposal created.")


@router.get("/proposals", response_model=UnifiedResponse, summary="List Skill governance proposals")
async def list_skill_governance_proposals(
    status: str | None = Query(default=None, max_length=30),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    scoped = _proposal_scope_query(user)
    if status:
        scoped = scoped.where(SkillGovernanceProposal.status == status)
    total = (await db.execute(select(func.count()).select_from(scoped.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                scoped.order_by(SkillGovernanceProposal.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return UnifiedResponse.success(
        data={
            "items": [_proposal_to_payload(proposal) for proposal in rows],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.get("/enabled", response_model=UnifiedResponse, summary="Get enabled Skill version")
async def get_enabled_skill_version(
    skill_name: str = Query(..., min_length=1, max_length=160),
    version: str | None = Query(default=None, max_length=80),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    service = SkillGovernanceService(db)
    enabled_version = await service.get_enabled_version(org_id=org_id, skill_name=skill_name)
    return UnifiedResponse.success(
        data={
            "skill_name": skill_name,
            "enabled_version": enabled_version,
            "enabled": enabled_version is not None
            and (version is None or enabled_version == version),
        }
    )


@router.get(
    "/connectors", response_model=UnifiedResponse, summary="List governed Skill connector configs"
)
async def list_skill_connector_configs(
    skill_name: str | None = Query(default=None, max_length=160),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    rows = await SkillGovernanceService(db).list_connector_configs(
        org_id=org_id, skill_name=skill_name
    )
    return UnifiedResponse.success(
        data={
            "items": [_connector_to_payload(config) for config in rows],
            "total": len(rows),
        }
    )


@router.post(
    "/connectors", response_model=UnifiedResponse, summary="Create governed Skill connector config"
)
async def create_skill_connector_config(
    body: SkillConnectorConfigBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        config = await SkillGovernanceService(db).create_connector_config(
            org_id=org_id,
            skill_name=body.skill_name,
            connector_name=body.connector_name,
            connector_type=body.connector_type,
            endpoint_url=body.endpoint_url,
            auth_type=body.auth_type,
            credentials=body.credentials,
            is_enabled=body.is_enabled,
            actor=str(user.id),
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    payload = _connector_to_payload(config)
    await db.commit()
    return UnifiedResponse.success(data=payload, message="Skill connector config created.")


@router.put(
    "/connectors/{connector_id}",
    response_model=UnifiedResponse,
    summary="Update governed Skill connector config",
)
async def update_skill_connector_config(
    connector_id: str,
    body: SkillConnectorConfigUpdateBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        config = await SkillGovernanceService(db).update_connector_config(
            org_id=org_id,
            connector_id=connector_id,
            actor=str(user.id),
            skill_name=body.skill_name,
            connector_name=body.connector_name,
            connector_type=body.connector_type,
            endpoint_url=body.endpoint_url,
            replace_endpoint_url="endpoint_url" in body.model_fields_set,
            auth_type=body.auth_type,
            credentials=body.credentials,
            replace_credentials="credentials" in body.model_fields_set,
            is_enabled=body.is_enabled,
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    payload = _connector_to_payload(config)
    await db.commit()
    return UnifiedResponse.success(data=payload, message="Skill connector config updated.")


@router.delete(
    "/connectors/{connector_id}",
    response_model=UnifiedResponse,
    summary="Delete governed Skill connector config",
)
async def delete_skill_connector_config(
    connector_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        await SkillGovernanceService(db).delete_connector_config(
            org_id=org_id,
            connector_id=connector_id,
            actor=str(user.id),
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    await db.commit()
    return UnifiedResponse.success(
        data={"deleted": True}, message="Skill connector config deleted."
    )


@router.get(
    "/proposals/{proposal_id}",
    response_model=UnifiedResponse,
    summary="Get Skill governance proposal",
)
async def get_skill_governance_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    proposal = await _get_scoped_proposal(db, proposal_id=proposal_id, user=user)
    if proposal is None:
        return UnifiedResponse.error(
            code=404, message="Skill proposal does not exist or is not visible."
        )
    return UnifiedResponse.success(data=_proposal_to_payload(proposal))


@router.get(
    "/proposals/{proposal_id}/audit-events",
    response_model=UnifiedResponse,
    summary="List Skill governance audit events",
)
async def list_skill_governance_audit_events(
    proposal_id: str,
    limit: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    proposal = await _get_scoped_proposal(db, proposal_id=proposal_id, user=user)
    if proposal is None:
        return UnifiedResponse.error(
            code=404, message="Skill proposal does not exist or is not visible."
        )
    rows = await SkillGovernanceService(db).get_audit_events(org_id=proposal.org_id, limit=limit)
    proposal_rows = [event for event in rows if event.proposal_id == proposal.id]
    return UnifiedResponse.success(
        data={
            "items": [_audit_event_to_payload(event) for event in proposal_rows],
            "total": len(proposal_rows),
        }
    )


@router.get(
    "/proposals/{proposal_id}/audit-export",
    response_model=UnifiedResponse,
    summary="Export Skill governance audit artifact",
)
async def export_skill_governance_audit_artifact(
    proposal_id: str,
    limit: int = Query(default=500, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    proposal = await _get_scoped_proposal(db, proposal_id=proposal_id, user=user)
    if proposal is None:
        return UnifiedResponse.error(
            code=404, message="Skill proposal does not exist or is not visible."
        )
    rows = await SkillGovernanceService(db).get_audit_events(org_id=proposal.org_id, limit=limit)
    proposal_rows = [event for event in rows if event.proposal_id == proposal.id]
    return UnifiedResponse.success(
        data={
            "schema_version": "skill_governance_audit_export.v1",
            "generated_at": datetime.now(UTC).isoformat(),
            "proposal": _proposal_to_payload(proposal),
            "audit_events": [_audit_event_to_payload(event) for event in proposal_rows],
            "total": len(proposal_rows),
            "limit": limit,
        }
    )


@router.post(
    "/proposals/{proposal_id}/eval",
    response_model=UnifiedResponse,
    summary="Record Skill proposal eval",
)
async def record_skill_governance_eval(
    proposal_id: str,
    body: SkillGovernanceEvalBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        proposal = await SkillGovernanceService(db).record_eval(
            org_id=org_id,
            proposal_id=proposal_id,
            checks=body.checks,
            actor=str(user.id),
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    payload = _proposal_to_payload(proposal)
    await db.commit()
    return UnifiedResponse.success(data=payload, message="Skill proposal eval recorded.")


@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=UnifiedResponse,
    summary="Approve Skill proposal",
)
async def approve_skill_governance_proposal(
    proposal_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        proposal = await SkillGovernanceService(db).approve(
            org_id=org_id,
            proposal_id=proposal_id,
            approver=str(user.id),
            approver_role=_role_for(user),
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    payload = _proposal_to_payload(proposal)
    await db.commit()
    return UnifiedResponse.success(data=payload, message="Skill proposal approved.")


@router.post(
    "/proposals/{proposal_id}/gray-release",
    response_model=UnifiedResponse,
    summary="Gray release Skill proposal",
)
async def gray_release_skill_governance_proposal(
    proposal_id: str,
    body: SkillGovernanceGrayReleaseBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        proposal = await SkillGovernanceService(db).gray_release(
            org_id=org_id,
            proposal_id=proposal_id,
            percentage=body.percentage,
            actor=str(user.id),
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    payload = _proposal_to_payload(proposal)
    await db.commit()
    return UnifiedResponse.success(data=payload, message="Skill proposal gray released.")


@router.post(
    "/proposals/{proposal_id}/rollback",
    response_model=UnifiedResponse,
    summary="Rollback Skill proposal",
)
async def rollback_skill_governance_proposal(
    proposal_id: str,
    body: SkillGovernanceRollbackBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
) -> RouteResponse:
    if error := _require_admin(user):
        return error
    org_id = _require_org(user)
    if not org_id:
        return UnifiedResponse.error(
            code=403, message="Current user is not attached to an organization."
        )
    try:
        proposal = await SkillGovernanceService(db).rollback(
            org_id=org_id,
            proposal_id=proposal_id,
            reason=body.reason,
            actor=str(user.id),
        )
    except SkillEvolutionError as exc:
        return _error_response(exc)
    payload = _proposal_to_payload(proposal)
    await db.commit()
    return UnifiedResponse.success(data=payload, message="Skill proposal rolled back.")
