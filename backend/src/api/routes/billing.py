# -*- coding: utf-8 -*-
"""
计费系统 API 路由

方案管理 / 订阅 / 退款 / 报表
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.core.database import get_db
from src.core.deps import (
    get_current_user_required,
    get_current_user,
    require_permission,
    Permission,
)
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.subscription_service import SubscriptionService
from src.services.refund_service import RefundService


router = APIRouter(prefix="/billing", tags=["计费系统"])


# ===== Pydantic 请求模型 =====


class CreatePlanRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="方案名称")
    code: str = Field(
        ..., min_length=1, max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="方案代码（小写字母开头，仅含小写字母/数字/下划线）",
    )
    description: Optional[str] = Field(None, max_length=1000, description="方案描述")
    billing_mode: str = Field(
        ...,
        pattern=r"^(per_consultation|monthly|yearly|hourly)$",
        description="计费模式",
    )
    base_price: float = Field(..., ge=0, description="基础价格")
    original_price: Optional[float] = Field(None, ge=0, description="原价（划线价）")
    features: List[dict] = Field(default_factory=list, description="功能列表")
    ai_quota: int = Field(100, ge=0, description="AI对话次数/月")
    storage_gb: int = Field(5, ge=1, description="存储空间(GB)")
    max_team_members: int = Field(5, ge=1, description="团队成员上限")
    badge: Optional[str] = Field(None, max_length=20, description="角标文字")
    highlight: bool = Field(False, description="是否高亮推荐")


class UpdatePlanRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=1000)
    billing_mode: Optional[str] = Field(
        None, pattern=r"^(per_consultation|monthly|yearly|hourly)$"
    )
    base_price: Optional[float] = Field(None, ge=0)
    original_price: Optional[float] = Field(None, ge=0)
    features: Optional[List[dict]] = None
    ai_quota: Optional[int] = Field(None, ge=0)
    storage_gb: Optional[int] = Field(None, ge=1)
    max_team_members: Optional[int] = Field(None, ge=1)
    badge: Optional[str] = Field(None, max_length=20)
    highlight: Optional[bool] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class CreateSubscriptionRequest(BaseModel):
    plan_id: str = Field(..., description="计费方案ID")
    org_id: Optional[str] = Field(None, description="企业订阅关联组织ID")


class CancelSubscriptionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=256, description="取消原因")
    immediate: bool = Field(False, description="是否立即生效")


class RequestRefundRequest(BaseModel):
    order_id: str = Field(..., description="支付订单ID")
    amount: Optional[float] = Field(None, ge=0.01, description="退款金额（空=全额）")
    reason: str = Field(..., min_length=1, max_length=500, description="退款原因")


class RejectRefundRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=256, description="驳回原因")


# ===== 方案接口 =====


@router.get("/plans")
async def list_plans(
    billing_mode: Optional[str] = Query(None, description="按计费模式筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取计费方案列表（公开接口）"""
    service = SubscriptionService(db)
    data = await service.list_plans(billing_mode=billing_mode)
    return UnifiedResponse.success(data)


@router.post("/plans")
async def create_plan(
    req: CreatePlanRequest,
    user: User = Depends(require_permission(Permission.MANAGE_PLANS)),
    db: AsyncSession = Depends(get_db),
):
    """创建计费方案（管理员）"""
    service = SubscriptionService(db)
    try:
        data = await service.create_plan(req.model_dump())
        return UnifiedResponse.success(data, message="方案已创建")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: str,
    req: UpdatePlanRequest,
    user: User = Depends(require_permission(Permission.MANAGE_PLANS)),
    db: AsyncSession = Depends(get_db),
):
    """更新计费方案（管理员）"""
    service = SubscriptionService(db)
    try:
        data = await service.update_plan(
            plan_id=plan_id,
            data=req.model_dump(exclude_none=True),
        )
        return UnifiedResponse.success(data, message="方案已更新")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


# ===== 订阅接口 =====


@router.post("/subscriptions")
async def create_subscription(
    req: CreateSubscriptionRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """创建订阅"""
    service = SubscriptionService(db)
    try:
        data = await service.create_subscription(
            user_id=user.id,
            plan_id=req.plan_id,
            org_id=req.org_id,
        )
        return UnifiedResponse.success(data, message="订阅已创建")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


@router.get("/subscriptions")
async def get_my_subscriptions(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """获取我的订阅列表"""
    service = SubscriptionService(db)
    data = await service.get_user_subscriptions(user_id=user.id)
    return UnifiedResponse.success(data)


@router.get("/subscriptions/status")
async def get_subscription_status(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """查询当前订阅状态"""
    service = SubscriptionService(db)
    data = await service.check_subscription_access(user_id=user.id)
    return UnifiedResponse.success(data)


@router.post("/subscriptions/{sub_id}/cancel")
async def cancel_subscription(
    sub_id: str,
    req: CancelSubscriptionRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """取消订阅"""
    service = SubscriptionService(db)
    try:
        data = await service.cancel_subscription(
            sub_id=sub_id,
            user_id=user.id,
            reason=req.reason,
            immediate=req.immediate,
        )
        return UnifiedResponse.success(data, message="订阅已取消")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))
    except PermissionError as e:
        return UnifiedResponse.error(403, str(e))


# ===== 退款接口 =====


@router.post("/refunds")
async def request_refund(
    req: RequestRefundRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """申请退款"""
    service = RefundService(db)
    try:
        data = await service.request_refund(
            user_id=user.id,
            order_id=req.order_id,
            amount=req.amount,
            reason=req.reason,
        )
        return UnifiedResponse.success(data, message="退款申请已提交")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))
    except PermissionError as e:
        return UnifiedResponse.error(403, str(e))


@router.get("/refunds")
async def list_refunds(
    status: Optional[str] = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """退款列表（用户端看自己的，管理端看全部）"""
    service = RefundService(db)

    # 管理员可看全部，普通用户只看自己的
    from src.core.deps import has_permission
    is_admin = has_permission(user.role, Permission.MANAGE_REFUNDS)
    user_id = None if is_admin else user.id

    data = await service.list_refunds(
        user_id=user_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return UnifiedResponse.success(data)


@router.post("/admin/refunds/{refund_id}/approve")
async def approve_refund(
    refund_id: str,
    user: User = Depends(require_permission(Permission.MANAGE_REFUNDS)),
    db: AsyncSession = Depends(get_db),
):
    """审批退款"""
    service = RefundService(db)
    try:
        data = await service.approve_refund(
            refund_id=refund_id,
            approver_id=user.id,
        )
        # 自动执行退款
        data = await service.process_refund(refund_id=refund_id)
        return UnifiedResponse.success(data, message="退款已审批并处理")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


@router.post("/admin/refunds/{refund_id}/reject")
async def reject_refund(
    refund_id: str,
    req: RejectRefundRequest,
    user: User = Depends(require_permission(Permission.MANAGE_REFUNDS)),
    db: AsyncSession = Depends(get_db),
):
    """驳回退款"""
    service = RefundService(db)
    try:
        data = await service.reject_refund(
            refund_id=refund_id,
            approver_id=user.id,
            reason=req.reason,
        )
        return UnifiedResponse.success(data, message="退款已驳回")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


# ===== 报表接口 =====


@router.get("/reports/revenue")
async def get_revenue_report(
    days: int = Query(30, ge=1, le=365, description="统计天数"),
    user: User = Depends(require_permission(Permission.VIEW_REPORTS)),
    db: AsyncSession = Depends(get_db),
):
    """收入报表"""
    refund_service = RefundService(db)
    refund_stats = await refund_service.get_refund_stats(days=days)

    sub_service = SubscriptionService(db)
    sub_stats = await sub_service.get_subscription_stats()

    return UnifiedResponse.success({
        "subscription_stats": sub_stats,
        "refund_stats": refund_stats,
    })


@router.get("/reports/subscriptions")
async def get_subscription_report(
    org_id: Optional[str] = Query(None, description="组织ID筛选"),
    user: User = Depends(require_permission(Permission.VIEW_REPORTS)),
    db: AsyncSession = Depends(get_db),
):
    """订阅报表"""
    service = SubscriptionService(db)
    data = await service.get_subscription_stats(org_id=org_id)
    return UnifiedResponse.success(data)
