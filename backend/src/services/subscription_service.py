# -*- coding: utf-8 -*-
"""
订阅与计费服务

管理计费方案（BillingPlan）、用户订阅（Subscription）及订阅访问控制。
"""

import uuid
from datetime import datetime, timezone, date, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.models.billing import BillingPlan, Subscription
from src.models.payment import PaymentOrder


class SubscriptionService:
    """订阅与计费服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 方案管理
    # ------------------------------------------------------------------

    async def list_plans(
        self,
        billing_mode: Optional[str] = None,
        active_only: bool = True,
    ) -> list[dict]:
        """获取计费方案列表，按 sort_order 排序"""

        query = select(BillingPlan)
        if active_only:
            query = query.where(BillingPlan.is_active == True)
        if billing_mode:
            query = query.where(BillingPlan.billing_mode == billing_mode)
        query = query.order_by(BillingPlan.sort_order.asc())

        result = await self.db.execute(query)
        plans = result.scalars().all()

        return [p.to_dict() for p in plans]

    async def create_plan(self, data: dict) -> dict:
        """管理员创建方案"""

        # 检查 code 唯一
        existing = await self.db.execute(
            select(BillingPlan).where(BillingPlan.code == data["code"])
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"方案代码 {data['code']} 已存在")

        plan = BillingPlan(
            name=data["name"],
            code=data["code"],
            description=data.get("description"),
            billing_mode=data["billing_mode"],
            base_price=data["base_price"],
            original_price=data.get("original_price"),
            features=data.get("features", []),
            ai_quota=data.get("ai_quota", 100),
            storage_gb=data.get("storage_gb", 5),
            max_team_members=data.get("max_team_members", 5),
            badge=data.get("badge"),
            highlight=data.get("highlight", False),
        )
        self.db.add(plan)
        await self.db.commit()
        await self.db.refresh(plan)

        logger.info(f"创建计费方案: {plan.code} ({plan.name})")
        return plan.to_dict()

    async def update_plan(self, plan_id: str, data: dict) -> dict:
        """管理员更新方案"""

        plan = await self.db.get(BillingPlan, plan_id)
        if not plan:
            raise ValueError("方案不存在")

        updatable = [
            "name", "description", "billing_mode", "base_price",
            "original_price", "features", "ai_quota", "storage_gb",
            "max_team_members", "badge", "highlight", "is_active", "sort_order",
        ]
        for field in updatable:
            if field in data:
                setattr(plan, field, data[field])

        await self.db.commit()
        await self.db.refresh(plan)

        return plan.to_dict()

    # ------------------------------------------------------------------
    # 订阅管理
    # ------------------------------------------------------------------

    async def create_subscription(
        self,
        user_id: str,
        plan_id: str,
        org_id: Optional[str] = None,
    ) -> dict:
        """
        创建订阅:
        1. 查找方案
        2. 计算周期
        3. 创建 Subscription
        4. 创建首期 PaymentOrder
        """

        plan = await self.db.get(BillingPlan, plan_id)
        if not plan:
            raise ValueError("计费方案不存在")
        if not plan.is_active:
            raise ValueError("该方案已下架")

        # 计算周期
        today = date.today()
        if plan.billing_mode == "monthly":
            period_end = today + timedelta(days=30)
        elif plan.billing_mode == "yearly":
            period_end = today + timedelta(days=365)
        else:
            # per_consultation / hourly 按需计费，设一个较长的周期
            period_end = today + timedelta(days=30)

        subscription = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            org_id=org_id,
            status="active",
            current_period_start=today,
            current_period_end=period_end,
            auto_renew=True,
            next_billing_date=period_end,
        )
        self.db.add(subscription)

        # 创建首期支付订单
        payment_order = PaymentOrder(
            user_id=user_id,
            order_type="subscription",
            amount=plan.base_price,
            status="pending",
            description=f"订阅 {plan.name} ({plan.billing_mode})",
            related_id=None,  # 提交后再关联
            payment_provider="mock",
        )
        self.db.add(payment_order)

        await self.db.flush()

        # 回填关联
        subscription.last_payment_id = payment_order.id
        payment_order.related_id = subscription.id

        await self.db.commit()
        await self.db.refresh(subscription)
        await self.db.refresh(payment_order)

        logger.info(
            f"创建订阅: user={user_id}, plan={plan.code}, "
            f"sub={subscription.id}, order={payment_order.id}"
        )

        return {
            "subscription": subscription.to_dict(),
            "payment_order": payment_order.to_dict(),
        }

    async def get_user_subscriptions(self, user_id: str) -> list[dict]:
        """获取用户的订阅列表（含方案详情）"""

        result = await self.db.execute(
            select(Subscription, BillingPlan)
            .join(BillingPlan, Subscription.plan_id == BillingPlan.id)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc())
        )
        rows = result.all()

        items = []
        for sub, plan in rows:
            item = sub.to_dict()
            item["plan"] = plan.to_dict()
            items.append(item)

        return items

    async def cancel_subscription(
        self,
        sub_id: str,
        user_id: str,
        reason: str,
        immediate: bool = False,
    ) -> dict:
        """
        取消订阅:
        - immediate=True: 立即失效
        - immediate=False: 当前周期结束后失效
        """

        sub = await self.db.get(Subscription, sub_id)
        if not sub:
            raise ValueError("订阅不存在")
        if sub.user_id != user_id:
            raise PermissionError("无权操作此订阅")
        if sub.status not in ("active", "past_due"):
            raise ValueError(f"订阅状态为 {sub.status}，无法取消")

        now = datetime.now(timezone.utc)

        if immediate:
            sub.status = "cancelled"
        else:
            # 标记为取消中，到期后自然失效
            sub.auto_renew = False

        sub.cancelled_at = now
        sub.cancellation_reason = reason

        await self.db.commit()
        await self.db.refresh(sub)

        logger.info(f"取消订阅: sub={sub_id}, immediate={immediate}")
        return sub.to_dict()

    async def check_subscription_access(self, user_id: str) -> dict:
        """检查用户是否有有效订阅"""

        today = date.today()

        result = await self.db.execute(
            select(Subscription, BillingPlan)
            .join(BillingPlan, Subscription.plan_id == BillingPlan.id)
            .where(
                and_(
                    Subscription.user_id == user_id,
                    Subscription.status == "active",
                    Subscription.current_period_end >= today,
                )
            )
            .order_by(Subscription.current_period_end.desc())
            .limit(1)
        )
        row = result.first()

        if not row:
            return {
                "has_active": False,
                "plan_name": None,
                "expires_at": None,
                "ai_quota_remaining": 0,
            }

        sub, plan = row
        return {
            "has_active": True,
            "plan_name": plan.name,
            "plan_code": plan.code,
            "expires_at": sub.current_period_end.isoformat(),
            "ai_quota_remaining": plan.ai_quota,  # 简化实现：需要实际用量扣减
            "auto_renew": sub.auto_renew,
        }

    async def get_subscription_stats(self, org_id: Optional[str] = None) -> dict:
        """订阅统计: active_count, cancelled_count, mrr"""

        base = select(Subscription)
        if org_id:
            base = base.where(Subscription.org_id == org_id)

        # 活跃数
        active_q = select(func.count()).select_from(
            base.where(Subscription.status == "active").subquery()
        )
        active_count = (await self.db.execute(active_q)).scalar() or 0

        # 已取消数
        cancelled_q = select(func.count()).select_from(
            base.where(Subscription.status == "cancelled").subquery()
        )
        cancelled_count = (await self.db.execute(cancelled_q)).scalar() or 0

        # MRR（月经常性收入）= 所有活跃订阅对应方案的 base_price 之和
        mrr_q = (
            select(func.coalesce(func.sum(BillingPlan.base_price), 0))
            .select_from(
                Subscription.__table__
                .join(BillingPlan.__table__, Subscription.plan_id == BillingPlan.id)
            )
            .where(Subscription.status == "active")
        )
        if org_id:
            mrr_q = mrr_q.where(Subscription.org_id == org_id)
        mrr = float((await self.db.execute(mrr_q)).scalar() or 0)

        return {
            "active_count": active_count,
            "cancelled_count": cancelled_count,
            "mrr": mrr,
        }
