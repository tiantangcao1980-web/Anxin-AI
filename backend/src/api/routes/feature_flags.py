# -*- coding: utf-8 -*-

from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required, require_role, UserRole
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.feature_flag_service import FeatureFlagService

router = APIRouter()


class FeatureFlagCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=100, pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    enabled: bool = False
    rollout_percentage: int = Field(default=10000, ge=0, le=10000)  # 万分比，10000=100%
    target_roles: Optional[List[str]] = None
    target_org_ids: Optional[List[str]] = None
    metadata: Optional[dict] = None
    expires_at: Optional[datetime] = None


class FeatureFlagUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(None, ge=0, le=10000)  # 万分比，10000=100%
    target_roles: Optional[List[str]] = None
    target_org_ids: Optional[List[str]] = None
    metadata: Optional[dict] = None
    expires_at: Optional[datetime] = None


def _flag_to_dict(flag) -> dict:
    return {
        "id": flag.id,
        "key": flag.key,
        "name": flag.name,
        "description": flag.description,
        "enabled": flag.enabled,
        "rollout_percentage": flag.rollout_percentage,
        "target_roles": flag.target_roles,
        "target_org_ids": flag.target_org_ids,
        "metadata": flag.metadata_,
        "expires_at": flag.expires_at.isoformat() if flag.expires_at else None,
        "created_at": flag.created_at.isoformat() if flag.created_at else None,
        "updated_at": flag.updated_at.isoformat() if flag.updated_at else None,
    }


@router.get("/feature-flags")
async def get_user_flags(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user_required),
):
    service = FeatureFlagService(db)
    flags = await service.get_flags_for_user(
        user_id=user.id,
        role=user.role,
        org_id=getattr(user, "org_id", None),
    )
    return UnifiedResponse.success(data=flags)


@router.get("/admin/feature-flags")
async def admin_list_flags(
    skip: int = Query(0, ge=0, description="跳过记录数"),
    limit: int = Query(50, ge=1, le=200, description="返回数量上限"),
    search: Optional[str] = Query(None, description="按 key 或 name 模糊搜索"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
):
    service = FeatureFlagService(db)
    flags = await service.list_all()
    # 搜索过滤
    if search:
        search_lower = search.lower()
        flags = [
            f for f in flags
            if search_lower in (f.key or "").lower()
            or search_lower in (f.name or "").lower()
        ]
    total = len(flags)
    flags = flags[skip: skip + limit]
    return UnifiedResponse.success(data={
        "items": [_flag_to_dict(f) for f in flags],
        "meta": {"total": total, "skip": skip, "limit": limit},
    })


@router.post("/admin/feature-flags")
async def admin_create_flag(
    data: FeatureFlagCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
):
    service = FeatureFlagService(db)
    existing = await service.get_by_key(data.key)
    if existing:
        return UnifiedResponse.error(code=409, message=f"功能标识 '{data.key}' 已存在")
    flag = await service.create({
        "key": data.key,
        "name": data.name,
        "description": data.description,
        "enabled": data.enabled,
        "rollout_percentage": data.rollout_percentage,
        "target_roles": data.target_roles,
        "target_org_ids": data.target_org_ids,
        "metadata_": data.metadata,
        "expires_at": data.expires_at,
    })
    return UnifiedResponse.success(data=_flag_to_dict(flag))


@router.put("/admin/feature-flags/{key}")
async def admin_update_flag(
    key: str,
    data: FeatureFlagUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
):
    service = FeatureFlagService(db)
    update_data = {}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.enabled is not None:
        update_data["enabled"] = data.enabled
    if data.rollout_percentage is not None:
        update_data["rollout_percentage"] = data.rollout_percentage
    if data.target_roles is not None:
        update_data["target_roles"] = data.target_roles
    if data.target_org_ids is not None:
        update_data["target_org_ids"] = data.target_org_ids
    if data.metadata is not None:
        update_data["metadata_"] = data.metadata
    if data.expires_at is not None:
        update_data["expires_at"] = data.expires_at

    flag = await service.update(key, update_data)
    if not flag:
        return UnifiedResponse.error(code=404, message="功能开关不存在")
    return UnifiedResponse.success(data=_flag_to_dict(flag))


@router.delete("/admin/feature-flags/{key}")
async def admin_delete_flag(
    key: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(UserRole.ADMIN, UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN)),
):
    service = FeatureFlagService(db)
    success = await service.delete(key)
    if not success:
        return UnifiedResponse.error(code=404, message="功能开关不存在")
    return UnifiedResponse.success(message="删除成功")
