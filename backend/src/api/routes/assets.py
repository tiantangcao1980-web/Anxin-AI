"""
资产管理路由
"""

from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required, require_permission, Permission
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.asset_service import AssetService

router = APIRouter()

class AssetCreate(BaseModel):
    name: str
    type: str
    originalValue: float
    currentValue: float
    acquisitionDate: Optional[date] = None

class AssetUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    originalValue: Optional[float] = None
    currentValue: Optional[float] = None
    acquisitionDate: Optional[date] = None

class AssetResponse(BaseModel):
    id: str
    name: str
    type: str
    originalValue: float
    currentValue: float
    acquisitionDate: Optional[date] = None

@router.get("/")
async def list_assets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.READ_ASSETS))
):
    service = AssetService(db)
    assets = await service.list_assets(user.org_id)
    return UnifiedResponse.success(data=[
        AssetResponse(
            id=a.id,
            name=a.name,
            type=a.asset_type,
            originalValue=a.original_value,
            currentValue=a.current_value,
            acquisitionDate=a.acquisition_date
        ) for a in assets
    ])

@router.post("/")
async def create_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.WRITE_ASSETS))
):
    service = AssetService(db)
    asset = await service.create_asset(
        name=data.name,
        asset_type=data.type,
        original_value=data.originalValue,
        current_value=data.currentValue,
        acquisition_date=data.acquisitionDate,
        org_id=user.org_id,
        created_by=user.id
    )
    return UnifiedResponse.success(data=AssetResponse(
        id=asset.id,
        name=asset.name,
        type=asset.asset_type,
        originalValue=asset.original_value,
        currentValue=asset.current_value,
        acquisitionDate=asset.acquisition_date
    ))

@router.put("/{asset_id}")
async def update_asset(
    asset_id: str,
    data: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.WRITE_ASSETS))
):
    service = AssetService(db)
    asset = await service.update_asset(
        asset_id,
        org_id=user.org_id,
        name=data.name,
        asset_type=data.type,
        original_value=data.originalValue,
        current_value=data.currentValue,
        acquisition_date=data.acquisitionDate
    )
    if not asset:
        return UnifiedResponse.error(code=404, message="资产不存在或无权限访问")
        
    return UnifiedResponse.success(data=AssetResponse(
        id=asset.id,
        name=asset.name,
        type=asset.asset_type,
        originalValue=asset.original_value,
        currentValue=asset.current_value,
        acquisitionDate=asset.acquisition_date
    ))

@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.DELETE_ASSETS))
):
    service = AssetService(db)
    success = await service.delete_asset(asset_id, org_id=user.org_id)
    if not success:
        return UnifiedResponse.error(code=404, message="资产不存在或无权限访问")
    return UnifiedResponse.success(message="删除成功")
