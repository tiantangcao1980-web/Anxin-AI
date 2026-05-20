"""
资产管理路由
"""

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import Permission, require_permission
from src.core.responses import UnifiedResponse
from src.core.schemas import CamelModel
from src.models.user import User
from src.services.asset_service import AssetService

router = APIRouter()


def _require_org_id(user: User) -> str:
    if not user.org_id:
        raise HTTPException(status_code=403, detail="Organization context is required")
    return user.org_id


def _as_date(value: Any) -> date | None:
    return cast(date | None, value)


class AssetCreate(CamelModel):
    name: str
    type: str
    original_value: float
    current_value: float
    acquisition_date: date | None = None


class AssetUpdate(CamelModel):
    name: str | None = None
    type: str | None = None
    original_value: float | None = None
    current_value: float | None = None
    acquisition_date: date | None = None


class AssetResponse(CamelModel):
    id: str
    name: str
    type: str
    original_value: float
    current_value: float
    acquisition_date: date | None = None


@router.get("/")
async def list_assets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.READ_ASSETS)),
) -> dict[str, Any]:
    service = AssetService(db)
    org_id = _require_org_id(user)
    assets = await service.list_assets(org_id)
    return UnifiedResponse.success(
        data=[
            AssetResponse(
                id=a.id,
                name=a.name,
                type=a.asset_type,
                original_value=a.original_value,
                current_value=a.current_value,
                acquisition_date=_as_date(a.acquisition_date),
            )
            for a in assets
        ]
    )


@router.post("/")
async def create_asset(
    data: AssetCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.WRITE_ASSETS)),
) -> dict[str, Any]:
    service = AssetService(db)
    org_id = _require_org_id(user)
    asset = await service.create_asset(
        name=data.name,
        asset_type=data.type,
        original_value=data.original_value,
        current_value=data.current_value,
        acquisition_date=data.acquisition_date,
        org_id=org_id,
        created_by=user.id,
    )
    return UnifiedResponse.success(
        data=AssetResponse(
            id=asset.id,
            name=asset.name,
            type=asset.asset_type,
            original_value=asset.original_value,
            current_value=asset.current_value,
            acquisition_date=_as_date(asset.acquisition_date),
        )
    )


@router.put("/{asset_id}")
async def update_asset(
    asset_id: str,
    data: AssetUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.WRITE_ASSETS)),
) -> dict[str, Any]:
    service = AssetService(db)
    org_id = _require_org_id(user)
    asset = await service.update_asset(
        asset_id,
        org_id=org_id,
        name=data.name,
        asset_type=data.type,
        original_value=data.original_value,
        current_value=data.current_value,
        acquisition_date=data.acquisition_date,
    )
    if not asset:
        return UnifiedResponse.error(code=404, message="资产不存在或无权限访问")

    return UnifiedResponse.success(
        data=AssetResponse(
            id=asset.id,
            name=asset.name,
            type=asset.asset_type,
            original_value=asset.original_value,
            current_value=asset.current_value,
            acquisition_date=_as_date(asset.acquisition_date),
        )
    )


@router.delete("/{asset_id}")
async def delete_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.DELETE_ASSETS)),
) -> dict[str, Any]:
    service = AssetService(db)
    org_id = _require_org_id(user)
    success = await service.delete_asset(asset_id, org_id=org_id)
    if not success:
        return UnifiedResponse.error(code=404, message="资产不存在或无权限访问")
    return UnifiedResponse.success(message="删除成功")
