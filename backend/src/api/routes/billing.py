"""
计费系统 API 路由

方案管理 / 订阅 / 退款 / 报表
"""


from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import (
    Permission,
    get_current_user_required,
    require_permission,
)
from src.core.responses import UnifiedResponse
from src.models.user import User
from src.services.refund_service import RefundService
from src.services.subscription_service import SubscriptionService, SubscriptionStateError

router = APIRouter(prefix="/billing", tags=["计费系统"])


# ===== Pydantic 请求模型 =====


class CreatePlanRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="方案名称")
    code: str = Field(
        ..., min_length=1, max_length=50,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="方案代码（小写字母开头，仅含小写字母/数字/下划线）",
    )
    description: str | None = Field(None, max_length=1000, description="方案描述")
    billing_mode: str = Field(
        ...,
        pattern=r"^(per_consultation|monthly|yearly|hourly)$",
        description="计费模式",
    )
    base_price: float = Field(..., ge=0, description="基础价格")
    original_price: float | None = Field(None, ge=0, description="原价（划线价）")
    features: list[dict[str, Any]] = Field(default_factory=list, description="功能列表")
    ai_quota: int = Field(100, ge=0, description="AI对话次数/月")
    storage_gb: int = Field(5, ge=1, description="存储空间(GB)")
    max_team_members: int = Field(5, ge=1, description="团队成员上限")
    badge: str | None = Field(None, max_length=20, description="角标文字")
    highlight: bool = Field(False, description="是否高亮推荐")


class UpdatePlanRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = Field(None, max_length=1000)
    billing_mode: str | None = Field(
        None, pattern=r"^(per_consultation|monthly|yearly|hourly)$"
    )
    base_price: float | None = Field(None, ge=0)
    original_price: float | None = Field(None, ge=0)
    features: list[dict[str, Any]] | None = None
    ai_quota: int | None = Field(None, ge=0)
    storage_gb: int | None = Field(None, ge=1)
    max_team_members: int | None = Field(None, ge=1)
    badge: str | None = Field(None, max_length=20)
    highlight: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None


class CreateSubscriptionRequest(BaseModel):
    plan_id: str = Field(..., description="计费方案ID")
    org_id: str | None = Field(None, description="企业订阅关联组织ID")
    client_type: str = Field("needer", pattern=r"^(needer|provider)$", description="客户端类型")


class CancelSubscriptionRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=256, description="取消原因")
    immediate: bool = Field(False, description="是否立即生效")


class RequestRefundRequest(BaseModel):
    order_id: str = Field(..., description="支付订单ID")
    amount: float | None = Field(None, ge=0.01, description="退款金额（空=全额）")
    reason: str = Field(..., min_length=1, max_length=500, description="退款原因")
    idempotency_key: str | None = Field(
        None,
        max_length=128,
        description="退款幂等键；同一 key 的重复申请返回同一退款单",
    )


class RejectRefundRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=256, description="驳回原因")


# ===== 方案接口 =====


@router.get("/plans")
async def list_plans(
    billing_mode: str | None = Query(None, description="按计费模式筛选"),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取计费方案列表（公开接口）"""
    service = SubscriptionService(db)
    data = await service.list_plans(billing_mode=billing_mode)
    return UnifiedResponse.success(data)


@router.post("/plans")
async def create_plan(
    req: CreatePlanRequest,
    user: User = Depends(require_permission(Permission.MANAGE_PLANS)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
    """创建订阅"""
    service = SubscriptionService(db)
    target_org_id = req.org_id or user.org_id
    if req.org_id and str(req.org_id) != str(user.org_id) and user.role not in {"super_admin", "admin"}:
        return UnifiedResponse.error(403, "无权为其他组织创建订阅")
    try:
        data = await service.create_subscription(
            user_id=user.id,
            plan_id=req.plan_id,
            org_id=target_org_id,
            client_type=req.client_type,
        )
        return UnifiedResponse.success(data, message="订阅已创建")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))


@router.get("/subscriptions")
async def get_my_subscriptions(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取我的订阅列表"""
    service = SubscriptionService(db)
    data = await service.get_user_subscriptions(user_id=user.id)
    return UnifiedResponse.success(data)


@router.get("/subscriptions/status")
async def get_subscription_status(
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
) -> Any:
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
    except SubscriptionStateError as e:
        return JSONResponse(
            status_code=409,
            content=UnifiedResponse.error(409, str(e)),
        )
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
) -> dict[str, Any]:
    """申请退款"""
    service = RefundService(db)
    try:
        data = await service.request_refund(
            user_id=user.id,
            order_id=req.order_id,
            amount=req.amount,
            reason=req.reason,
            idempotency_key=req.idempotency_key,
        )
        return UnifiedResponse.success(data, message="退款申请已提交")
    except ValueError as e:
        return UnifiedResponse.error(400, str(e))
    except PermissionError as e:
        return UnifiedResponse.error(403, str(e))


@router.get("/refunds")
async def list_refunds(
    status: str | None = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
    org_id: str | None = Query(None, description="组织ID筛选"),
    user: User = Depends(require_permission(Permission.VIEW_REPORTS)),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """订阅报表"""
    service = SubscriptionService(db)
    scoped_org_id = org_id if user.role in {"super_admin", "admin"} else user.org_id
    data = await service.get_subscription_stats(org_id=scoped_org_id)
    return UnifiedResponse.success(data)


# ===== V2 架构：运行模式与功能鉴权 API =====


@router.get("/v2/features")
async def get_my_features(
    client_type: str = Query("needer", description="客户端类型: needer/provider"),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """获取当前用户的有效功能权限（V2 架构）"""
    service = SubscriptionService(db)
    features = await service.get_effective_features(user.id, client_type)
    sub = await service.get_active_by_client(user.id, client_type)
    return UnifiedResponse.success({
        "features": features,
        "subscription_status": sub.status if sub else "free",
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub and sub.trial_ends_at else None,
        "client_type": client_type,
    })


@router.get("/v2/can-access")
async def check_feature_access(
    feature: str = Query(..., description="功能标识: sentiment_monitoring/lawyer_matching 等"),
    client_type: str = Query("needer", description="客户端类型"),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """检查用户是否可访问某功能"""
    service = SubscriptionService(db)
    allowed = await service.can_access_feature(user.id, feature, client_type)
    return UnifiedResponse.success({"feature": feature, "allowed": allowed})


@router.get("/v2/can-use-mode")
async def check_mode_access(
    mode: str = Query(..., description="运行模式: local/hybrid/cloud"),
    client_type: str = Query("needer"),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """检查用户是否可使用指定运行模式"""
    service = SubscriptionService(db)
    allowed = await service.can_use_mode(user.id, mode, client_type)
    return UnifiedResponse.success({"mode": mode, "allowed": allowed})


@router.post("/v2/trial")
async def create_trial_subscription(
    client_type: str = Query("needer"),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建试用订阅（3天云端体验）"""
    service = SubscriptionService(db)
    sub = await service.create_trial(user.id, client_type)
    if not sub:
        return UnifiedResponse.error(code=409, message="您已有活跃订阅或试用计划未配置")
    await db.commit()
    return UnifiedResponse.success({
        "message": "试用订阅已创建，享受 3 天云端体验！",
        "trial_ends_at": sub.trial_ends_at.isoformat() if sub.trial_ends_at else None,
    })


class V2SubscribeRequest(BaseModel):
    plan_id: str = Field(..., description="计费方案 ID")
    client_type: str = Field("needer", pattern=r"^(needer|provider)$")
    payment_method: str = Field("wechat", pattern=r"^(wechat|alipay)$")
    billing_cycle: str = Field("monthly", pattern=r"^(monthly|yearly)$")


@router.post("/v2/subscribe")
async def create_v2_subscription(
    body: V2SubscribeRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    V2 创建付费订阅（连接支付系统）

    1. 查找方案并校验 client_type 匹配
    2. 创建订阅记录
    3. 创建支付订单
    4. 返回支付链接/二维码
    """
    service = SubscriptionService(db)

    # 检查是否已有活跃订阅
    existing = await service.get_active_by_client(user.id, body.client_type)
    if existing and existing.status == "active":
        return UnifiedResponse.error(code=409, message="您在该客户端已有活跃订阅，请先取消或等待到期")

    # 查找方案
    from src.models.billing import BillingPlan
    plan = await db.get(BillingPlan, body.plan_id)
    if not plan or not plan.is_active:
        return UnifiedResponse.error(code=404, message="方案不存在或已下架")

    # 校验 client_type 匹配
    plan_client = getattr(plan, 'client_type', 'needer') or 'needer'
    if plan_client != 'both' and plan_client != body.client_type:
        return UnifiedResponse.error(code=400, message="该方案不适用于您选择的客户端类型")

    # 计算金额
    if body.billing_cycle == "yearly":
        amount = (getattr(plan, 'base_price', 0) or 0) * 12 * 0.8  # 年付 8 折
    else:
        amount = getattr(plan, 'base_price', 0) or 0

    # 创建订阅
    result = await service.create_subscription(
        user_id=user.id,
        plan_id=body.plan_id,
        org_id=getattr(user, 'org_id', None),
        client_type=body.client_type,
    )

    sub_data = result.get("subscription", {})
    sub_id = sub_data.get("id")

    return UnifiedResponse.success(data={
        "subscription_id": sub_id,
        "payment_order": result.get("payment_order"),
        "amount": amount,
        "message": f"订阅创建成功，请完成 ¥{amount:.0f} 的支付",
    })
