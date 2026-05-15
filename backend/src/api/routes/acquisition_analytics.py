"""
获客分析 API 路由
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import Permission, require_permission
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.acquisition_analytics_service import AcquisitionAnalyticsService

router = APIRouter(prefix="/acquisition", tags=["获客分析"])


def _resolve_org_scope(user: User, requested_org_id: str | None) -> str | None:
    """仅平台管理员可跨组织查询，其他用户固定到自身组织。"""
    if user.role in {"super_admin", "admin"}:
        return requested_org_id
    return str(user.org_id) if getattr(user, "org_id", None) else None


@router.get("/funnel")
async def get_lead_funnel(
    days: int = Query(30, ge=1, le=365),
    org_id: str | None = None,
    user: User = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取线索漏斗数据"""
    service = AcquisitionAnalyticsService(db)
    data = await service.get_lead_funnel(org_id=_resolve_org_scope(user, org_id), days=days)
    return UnifiedResponse.success(data=data)


@router.get("/conversion")
async def get_conversion_rates(
    days: int = Query(30, ge=1, le=365),
    org_id: str | None = None,
    user: User = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取各阶段转化率"""
    service = AcquisitionAnalyticsService(db)
    data = await service.get_conversion_rates(org_id=_resolve_org_scope(user, org_id), days=days)
    return UnifiedResponse.success(data=data)


@router.get("/sources")
async def get_lead_sources(
    days: int = Query(30, ge=1, le=365),
    org_id: str | None = None,
    user: User = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取线索来源分布"""
    service = AcquisitionAnalyticsService(db)
    data = await service.get_lead_sources(org_id=_resolve_org_scope(user, org_id), days=days)
    return UnifiedResponse.success(data=data)


@router.get("/lawyer-performance")
async def get_lawyer_performance(
    days: int = Query(30, ge=1, le=365),
    org_id: str | None = None,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    user: User = Depends(require_permission(Permission.VIEW_ANALYTICS)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取律师业绩排名"""
    service = AcquisitionAnalyticsService(db)
    data = await service.get_lawyer_performance(org_id=_resolve_org_scope(user, org_id), days=days)
    # 按 total_delegations 降序排列
    if isinstance(data, list):
        data.sort(key=lambda x: x.get("total_delegations", 0), reverse=True)
    total = len(data) if isinstance(data, list) else 0
    start = (page - 1) * page_size
    items = data[start : start + page_size] if isinstance(data, list) else data
    return UnifiedResponse.success(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )
