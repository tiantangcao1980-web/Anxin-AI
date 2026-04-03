# -*- coding: utf-8 -*-
"""
支付管理 API 路由

提供订单创建、查询、退款、关闭以及支付回调接口。
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from loguru import logger

from src.core.database import get_db
from src.core.config import settings
from src.core.deps import get_current_user_required, require_permission, Permission
from src.models.user import User
from src.models.payment import PaymentOrder as PaymentOrderModel
from src.services.webhook_security import WebhookSecurity
from src.services.payment_service import (
    CreateOrderRequest,
    RefundRequest,
    PaymentStatusEnum,
    PaymentProviderType,
    OrderType,
    get_payment_provider,
)

router = APIRouter()


# ========== 响应模型 ==========


class OrderResponse(BaseModel):
    """订单响应"""
    id: str
    order_type: str
    amount: float
    status: str
    description: str
    related_id: Optional[str] = None
    payment_provider: str
    payment_url: Optional[str] = None
    qr_code: Optional[str] = None
    transaction_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    """订单列表响应"""
    items: List[OrderResponse]
    total: int


# ========== 工具函数 ==========


def _model_to_response(order: PaymentOrderModel) -> OrderResponse:
    return OrderResponse(
        id=order.id,
        order_type=order.order_type,
        amount=order.amount,
        status=order.status,
        description=order.description,
        related_id=order.related_id,
        payment_provider=order.payment_provider,
        payment_url=order.payment_url,
        qr_code=order.qr_code,
        transaction_id=order.transaction_id,
        paid_at=order.paid_at,
        refunded_at=order.refunded_at,
        expires_at=order.expires_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )

# ========== 接口 ==========


@router.post("/orders", response_model=OrderResponse, summary="创建支付订单")
async def create_order(
    body: CreateOrderRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """
    创建支付订单。

    - **type**: 订单类型（consultation_fee / delegation_deposit / subscription / contract_signing）
    - **amount**: 金额（元）
    - **description**: 订单描述
    - **related_id**: 关联的业务 ID（可选）
    - **provider**: 支付渠道（默认 mock）
    """
    order_id = str(uuid.uuid4())
    provider = get_payment_provider()

    try:
        pay_result = await provider.create_order(
            order_id=order_id,
            amount=body.amount,
            description=body.description,
            notify_url=f"/api/v1/payments/webhook/{body.provider.value}",
        )
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))

    # 持久化到数据库
    db_order = PaymentOrderModel(
        id=order_id,
        user_id=user.id,
        order_type=body.type.value,
        amount=body.amount,
        status=PaymentStatusEnum.PENDING.value,
        description=body.description,
        related_id=body.related_id,
        payment_provider=body.provider.value,
        payment_url=pay_result.payment_url,
        qr_code=pay_result.qr_code,
        expires_at=pay_result.expires_at,
    )
    db.add(db_order)
    await db.commit()
    await db.refresh(db_order)

    logger.info(f"订单已创建: {order_id}, 用户: {user.id}, 金额: {body.amount}")
    return _model_to_response(db_order)


@router.get("/orders", response_model=OrderListResponse, summary="查询当前用户订单列表")
async def list_orders(
    status_filter: Optional[str] = Query(None, alias="status", description="按状态筛选"),
    order_type: Optional[str] = Query(None, description="按订单类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """查询当前用户的支付订单列表，支持状态和类型筛选。"""
    query = select(PaymentOrderModel).where(PaymentOrderModel.user_id == user.id)

    if status_filter:
        query = query.where(PaymentOrderModel.status == status_filter)
    if order_type:
        query = query.where(PaymentOrderModel.order_type == order_type)

    # 总数
    count_query = select(PaymentOrderModel.id).where(PaymentOrderModel.user_id == user.id)
    if status_filter:
        count_query = count_query.where(PaymentOrderModel.status == status_filter)
    if order_type:
        count_query = count_query.where(PaymentOrderModel.order_type == order_type)
    count_result = await db.execute(count_query)
    total = len(count_result.all())

    # 分页
    query = query.order_by(desc(PaymentOrderModel.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    orders = result.scalars().all()

    return OrderListResponse(
        items=[_model_to_response(o) for o in orders],
        total=total,
    )


@router.get("/orders/{order_id}", response_model=OrderResponse, summary="查询订单状态")
async def get_order(
    order_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """查询指定订单的详情和支付状态。同时向支付渠道查询最新状态并同步。"""
    result = await db.execute(
        select(PaymentOrderModel).where(
            PaymentOrderModel.id == order_id,
            PaymentOrderModel.user_id == user.id,
        )
    )
    db_order = result.scalar_one_or_none()
    if not db_order:
        raise HTTPException(status_code=404, detail="订单不存在")

    # 如果订单仍待支付，向渠道查询最新状态
    if db_order.status == PaymentStatusEnum.PENDING.value:
        try:
            provider = get_payment_provider()
            pay_status = await provider.query_order(order_id)
            if pay_status.status != PaymentStatusEnum.PENDING:
                db_order.status = pay_status.status.value
                db_order.transaction_id = pay_status.transaction_id
                db_order.paid_at = pay_status.paid_at
                await db.commit()
                await db.refresh(db_order)
        except NotImplementedError:
            pass  # 渠道未配置时忽略主动查询

    return _model_to_response(db_order)


@router.post("/orders/{order_id}/refund", response_model=OrderResponse, summary="申请退款")
async def refund_order(
    order_id: str,
    body: RefundRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """对已支付的订单发起退款。"""
    result = await db.execute(
        select(PaymentOrderModel).where(
            PaymentOrderModel.id == order_id,
            PaymentOrderModel.user_id == user.id,
        )
    )
    db_order = result.scalar_one_or_none()
    if not db_order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if db_order.status != PaymentStatusEnum.PAID.value:
        raise HTTPException(status_code=400, detail="只有已支付的订单可以退款")

    refund_amount = body.amount or db_order.amount

    try:
        provider = get_payment_provider()
        refund_result = await provider.refund(order_id, refund_amount, body.reason)
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e))

    if refund_result.status == "success":
        db_order.status = PaymentStatusEnum.REFUNDED.value
        db_order.refunded_at = datetime.now(timezone.utc)
        db_order.refund_reason = body.reason
        await db.commit()
        await db.refresh(db_order)
        logger.info(f"订单退款成功: {order_id}, 金额: {refund_amount}")

    return _model_to_response(db_order)


@router.post("/orders/{order_id}/close", summary="关闭订单")
async def close_order(
    order_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
):
    """关闭未支付的订单。"""
    result = await db.execute(
        select(PaymentOrderModel).where(
            PaymentOrderModel.id == order_id,
            PaymentOrderModel.user_id == user.id,
        )
    )
    db_order = result.scalar_one_or_none()
    if not db_order:
        raise HTTPException(status_code=404, detail="订单不存在")

    if db_order.status != PaymentStatusEnum.PENDING.value:
        raise HTTPException(status_code=400, detail="只有待支付的订单可以关闭")

    try:
        provider = get_payment_provider()
        await provider.close_order(order_id)
    except NotImplementedError:
        pass  # 渠道未配置时直接在本地关闭

    db_order.status = PaymentStatusEnum.CLOSED.value
    await db.commit()
    await db.refresh(db_order)

    logger.info(f"订单已关闭: {order_id}")
    return _model_to_response(db_order)


# ========== 支付回调 ==========


@router.post("/webhook/wechat", summary="微信支付回调", include_in_schema=False)
async def wechat_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    微信支付异步通知回调。

    生产环境需验证签名，当前为占位实现。
    """
    body = await request.body()
    logger.info(f"[Webhook] 微信支付回调: {body[:200]}")
    signature = request.headers.get("X-Wechat-Signature")
    timestamp = request.headers.get("X-Webhook-Timestamp")
    if not WebhookSecurity.verify(
        scope="wechat_pay",
        body=body,
        signature=signature,
        secret=settings.WECHAT_PAY_WEBHOOK_SECRET,
        timestamp=timestamp,
    ):
        raise HTTPException(status_code=403, detail="微信支付回调签名验证失败")

    # TODO: 验证签名 + 解析报文 + 更新订单状态
    # 占位返回成功
    return {"code": "SUCCESS", "message": "OK"}


@router.post("/webhook/alipay", summary="支付宝回调", include_in_schema=False)
async def alipay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    支付宝异步通知回调。

    生产环境需验证签名，当前为占位实现。
    """
    body = await request.body()
    form = await request.form()
    logger.info(f"[Webhook] 支付宝回调: trade_no={form.get('trade_no')}")
    signature = request.headers.get("X-Alipay-Signature")
    timestamp = request.headers.get("X-Webhook-Timestamp")
    if not WebhookSecurity.verify(
        scope="alipay",
        body=body,
        signature=signature,
        secret=settings.ALIPAY_WEBHOOK_SECRET,
        timestamp=timestamp,
    ):
        raise HTTPException(status_code=403, detail="支付宝回调签名验证失败")

    # TODO: 验证签名 + 更新订单状态
    return "success"
