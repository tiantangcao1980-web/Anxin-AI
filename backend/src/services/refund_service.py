# -*- coding: utf-8 -*-
"""
退款服务

管理退款申请、审批、执行全流程。
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from src.models.billing import Refund
from src.models.payment import PaymentOrder
from src.services.payment_service import get_payment_provider


class RefundService:
    """退款服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # 申请退款
    # ------------------------------------------------------------------

    async def request_refund(
        self,
        user_id: str,
        order_id: str,
        amount: Optional[float] = None,
        reason: str = "用户申请",
    ) -> dict:
        """
        申请退款:
        1. 查找订单，验证是 paid 状态
        2. amount 默认全额退款，不能超过订单金额
        3. 创建 Refund 记录
        """

        order = await self.db.get(PaymentOrder, order_id)
        if not order:
            raise ValueError("订单不存在")
        if order.user_id != user_id:
            raise PermissionError("无权操作此订单")
        if order.status != "paid":
            raise ValueError(f"订单状态为 {order.status}，无法退款")

        # 检查是否已有退款单
        existing = await self.db.execute(
            select(Refund).where(
                and_(
                    Refund.order_id == order_id,
                    Refund.status.in_(["pending", "approved"]),
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("该订单已有待处理的退款申请")

        # 退款金额
        refund_amount = amount or order.amount
        if refund_amount > order.amount:
            raise ValueError(f"退款金额不能超过订单金额 {order.amount}")
        if refund_amount <= 0:
            raise ValueError("退款金额必须大于 0")

        refund = Refund(
            order_id=order_id,
            user_id=user_id,
            amount=refund_amount,
            reason=reason,
            status="pending",
        )
        self.db.add(refund)
        await self.db.commit()
        await self.db.refresh(refund)

        logger.info(
            f"创建退款申请: refund={refund.id}, order={order_id}, "
            f"amount={refund_amount}"
        )
        return refund.to_dict()

    # ------------------------------------------------------------------
    # 退款列表
    # ------------------------------------------------------------------

    async def list_refunds(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """退款列表（用户端或管理端）"""

        query = select(Refund)
        if user_id:
            query = query.where(Refund.user_id == user_id)
        if status:
            query = query.where(Refund.status == status)
        query = query.order_by(Refund.created_at.desc())

        # 总数
        count_q = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_q)).scalar() or 0

        # 分页
        result = await self.db.execute(
            query.offset((page - 1) * page_size).limit(page_size)
        )
        refunds = result.scalars().all()

        items = []
        for r in refunds:
            item = r.to_dict()
            # 附加订单信息
            order = await self.db.get(PaymentOrder, r.order_id)
            if order:
                item["order_description"] = order.description
                item["order_amount"] = order.amount
                item["order_status"] = order.status
            items.append(item)

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ------------------------------------------------------------------
    # 审批
    # ------------------------------------------------------------------

    async def approve_refund(self, refund_id: str, approver_id: str) -> dict:
        """审批通过"""

        refund = await self.db.get(Refund, refund_id)
        if not refund:
            raise ValueError("退款记录不存在")
        if refund.status != "pending":
            raise ValueError(f"退款状态为 {refund.status}，无法审批")

        refund.status = "approved"
        refund.approved_by = approver_id
        refund.approved_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(refund)

        logger.info(f"退款审批通过: refund={refund_id}, approver={approver_id}")
        return refund.to_dict()

    async def reject_refund(
        self, refund_id: str, approver_id: str, reason: str
    ) -> dict:
        """驳回退款"""

        refund = await self.db.get(Refund, refund_id)
        if not refund:
            raise ValueError("退款记录不存在")
        if refund.status != "pending":
            raise ValueError(f"退款状态为 {refund.status}，无法驳回")

        refund.status = "rejected"
        refund.approved_by = approver_id
        refund.approved_at = datetime.now(timezone.utc)
        refund.rejection_reason = reason

        await self.db.commit()
        await self.db.refresh(refund)

        logger.info(f"退款驳回: refund={refund_id}, reason={reason}")
        return refund.to_dict()

    # ------------------------------------------------------------------
    # 执行退款
    # ------------------------------------------------------------------

    async def process_refund(self, refund_id: str) -> dict:
        """执行退款（调用支付渠道 API）"""

        refund = await self.db.get(Refund, refund_id)
        if not refund:
            raise ValueError("退款记录不存在")
        if refund.status != "approved":
            raise ValueError(f"退款状态为 {refund.status}，仅 approved 可执行")

        order = await self.db.get(PaymentOrder, refund.order_id)
        if not order:
            raise ValueError("关联订单不存在")

        # 调用支付渠道退款
        provider = get_payment_provider()
        try:
            result = await provider.refund(
                order_id=order.id,
                amount=refund.amount,
                reason=refund.reason,
            )
        except NotImplementedError as e:
            raise ValueError(f"支付渠道退款失败: {e}")

        # 更新退款单
        refund.status = "processed"
        refund.processed_at = datetime.now(timezone.utc)
        refund.processor_transaction_id = result.refund_id

        # 更新订单状态
        order.status = "refunded"
        order.refunded_at = datetime.now(timezone.utc)
        order.refund_reason = refund.reason

        await self.db.commit()
        await self.db.refresh(refund)

        logger.info(
            f"退款执行完成: refund={refund_id}, "
            f"txn={result.refund_id}"
        )
        return refund.to_dict()

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------

    async def get_refund_stats(
        self, org_id: Optional[str] = None, days: int = 30
    ) -> dict:
        """退款统计"""

        since = datetime.now(timezone.utc) - timedelta(days=days)

        base = select(Refund).where(Refund.created_at >= since)

        # 总数
        total_q = select(func.count()).select_from(base.subquery())
        total_count = (await self.db.execute(total_q)).scalar() or 0

        # 总金额
        amount_q = select(func.coalesce(func.sum(Refund.amount), 0)).where(
            Refund.created_at >= since
        )
        total_amount = float((await self.db.execute(amount_q)).scalar() or 0)

        # 待处理数
        pending_q = select(func.count()).select_from(
            base.where(Refund.status == "pending").subquery()
        )
        pending_count = (await self.db.execute(pending_q)).scalar() or 0

        # 平均处理天数
        avg_q = select(
            func.avg(
                func.extract(
                    "epoch",
                    Refund.processed_at - Refund.created_at,
                ) / 86400
            )
        ).where(
            and_(
                Refund.created_at >= since,
                Refund.processed_at.isnot(None),
            )
        )
        avg_days = (await self.db.execute(avg_q)).scalar()
        avg_processing_days = round(float(avg_days), 1) if avg_days else 0

        return {
            "total_count": total_count,
            "total_amount": total_amount,
            "pending_count": pending_count,
            "avg_processing_days": avg_processing_days,
            "period_days": days,
        }
