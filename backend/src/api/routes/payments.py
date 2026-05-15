"""
支付管理 API 路由

提供订单创建、查询、退款、关闭以及支付回调接口。
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.payment import PaymentOrder as PaymentOrderModel
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.official_webhook_security import (
    OfficialWebhookVerificationError,
    parse_wechat_pay_notification,
    verify_alipay_notification,
)
from src.services.payment_service import (
    CreateOrderRequest,
    PaymentProviderConfigError,
    PaymentProviderType,
    PaymentStatusEnum,
    RefundRequest,
    get_payment_provider,
)
from src.services.refund_service import RefundService
from src.services.webhook_handler import WebhookBusinessError, handle_verified_webhook
from src.services.webhook_idempotency_service import build_webhook_idempotency_key
from src.services.webhook_security import WebhookSecurity

router = APIRouter()


def _commercial_environment() -> bool:
    return settings.ENVIRONMENT.lower() in {"production", "staging"}


# ========== 响应模型 ==========


class OrderResponse(BaseModel):
    """订单响应"""

    id: str
    order_type: str
    amount: float
    status: str
    description: str
    related_id: str | None = None
    payment_provider: str
    payment_url: str | None = None
    qr_code: str | None = None
    transaction_id: str | None = None
    paid_at: datetime | None = None
    refunded_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    """订单列表响应"""

    items: list[OrderResponse]
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


def _payment_audit_value(order: PaymentOrderModel) -> dict[str, object]:
    return {
        "order_type": order.order_type,
        "amount": order.amount,
        "status": order.status,
        "provider": order.payment_provider,
        "related_id": order.related_id,
    }


# ========== 接口 ==========


@router.post("/orders", response_model=OrderResponse, summary="创建支付订单")
async def create_order(
    body: CreateOrderRequest,
    request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    创建支付订单。

    - **type**: 订单类型（consultation_fee / delegation_deposit / subscription / contract_signing）
    - **amount**: 金额（元）
    - **description**: 订单描述
    - **related_id**: 关联的业务 ID（可选）
    - **provider**: 支付渠道（默认 mock）
    """
    order_id = uuid.uuid4().hex

    try:
        provider = get_payment_provider(body.provider.value)
        pay_result = await provider.create_order(
            order_id=order_id,
            amount=body.amount,
            description=body.description,
            notify_url=f"/api/v1/payments/webhook/{body.provider.value}",
        )
    except PaymentProviderConfigError as e:
        raise HTTPException(
            status_code=503 if _commercial_environment() else 501,
            detail=str(e),
        ) from e
    except NotImplementedError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e

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
    await AuditService(db).log_from_request(
        request,
        action="payment.order.create",
        resource_type="payment_order",
        resource_id=db_order.id,
        user=user,
        new_value=_payment_audit_value(db_order),
        extra_data={"source": "payment", "provider": db_order.payment_provider},
    )

    logger.info(f"订单已创建: {order_id}, 用户: {user.id}, 金额: {body.amount}")
    return _model_to_response(db_order)


@router.get("/orders", response_model=OrderListResponse, summary="查询当前用户订单列表")
async def list_orders(
    status_filter: str | None = Query(None, alias="status", description="按状态筛选"),
    order_type: str | None = Query(None, description="按订单类型筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
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
) -> OrderResponse:
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
            provider = get_payment_provider(db_order.payment_provider)
            pay_status = await provider.query_order(order_id)
            if pay_status.status != PaymentStatusEnum.PENDING:
                db_order.status = pay_status.status.value
                db_order.transaction_id = pay_status.transaction_id
                db_order.paid_at = pay_status.paid_at
                await db.commit()
                await db.refresh(db_order)
        except (NotImplementedError, PaymentProviderConfigError) as e:
            if _commercial_environment():
                raise HTTPException(status_code=503, detail=str(e)) from e
            pass  # 渠道未配置时忽略主动查询

    return _model_to_response(db_order)


@router.post("/orders/{order_id}/refund", response_model=OrderResponse, summary="申请退款")
async def refund_order(
    order_id: str,
    body: RefundRequest,
    request: Request,
    idempotency_key_header: str | None = Header(None, alias="Idempotency-Key"),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """对已支付的订单发起退款。"""
    previous_order = await db.get(PaymentOrderModel, order_id)
    previous_status = (
        previous_order.status if previous_order and previous_order.user_id == user.id else None
    )
    service = RefundService(db)
    try:
        refund = await service.refund(
            user_id=user.id,
            order_id=order_id,
            amount=body.amount,
            reason=body.reason,
            idempotency_key=body.idempotency_key or idempotency_key_header,
        )
    except (NotImplementedError, PaymentProviderConfigError) as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    db_order = await db.get(PaymentOrderModel, refund["order_id"])
    if not db_order:
        raise HTTPException(status_code=404, detail="订单不存在")
    await db.refresh(db_order)
    await AuditService(db).log_from_request(
        request,
        action="payment.order.refund",
        resource_type="payment_order",
        resource_id=db_order.id,
        user=user,
        old_value={"status": previous_status} if previous_status else None,
        new_value={
            **_payment_audit_value(db_order),
            "refund_amount": refund.get("amount"),
            "refund_status": refund.get("status"),
            "refund_id": refund.get("id"),
        },
        extra_data={
            "source": "payment",
            "provider": db_order.payment_provider,
            "idempotency_key_present": bool(body.idempotency_key or idempotency_key_header),
        },
    )

    return _model_to_response(db_order)


@router.post("/orders/{order_id}/close", summary="关闭订单")
async def close_order(
    order_id: str,
    request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
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

    old_value = _payment_audit_value(db_order)
    try:
        provider = get_payment_provider(db_order.payment_provider)
        await provider.close_order(order_id)
    except (NotImplementedError, PaymentProviderConfigError) as e:
        if _commercial_environment():
            raise HTTPException(status_code=503, detail=str(e)) from e
        pass  # 渠道未配置时直接在本地关闭

    db_order.status = PaymentStatusEnum.CLOSED.value
    await db.commit()
    await db.refresh(db_order)
    await AuditService(db).log_from_request(
        request,
        action="payment.order.close",
        resource_type="payment_order",
        resource_id=db_order.id,
        user=user,
        old_value=old_value,
        new_value=_payment_audit_value(db_order),
        extra_data={"source": "payment", "provider": db_order.payment_provider},
    )

    logger.info(f"订单已关闭: {order_id}")
    return _model_to_response(db_order)


# ========== 支付回调 ==========


@router.post("/webhook/wechat", summary="微信支付回调", include_in_schema=False)
async def wechat_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    微信支付异步通知回调。

    显式启用官方模式时按微信支付 v3 RSA-SHA256 验签，未启用时走通用 HMAC 回归路径。
    """
    body = await request.body()
    logger.info(
        "[Webhook] 微信支付回调: {}",
        body[:200].decode("utf-8", errors="replace"),
    )
    scope = PaymentProviderType.WECHAT_PAY.value
    if settings.WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED:
        try:
            payload, idempotency_payload = parse_wechat_pay_notification(
                headers=request.headers,
                body=body,
                public_key=settings.WECHAT_PAY_PLATFORM_PUBLIC_KEY,
                public_key_path=settings.WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH,
                expected_serial=settings.WECHAT_PAY_PLATFORM_SERIAL,
                api_v3_key=settings.WECHAT_PAY_API_V3_KEY,
                max_age_seconds=settings.WEBHOOK_SIGNATURE_MAX_AGE_SECONDS,
            )
        except OfficialWebhookVerificationError as exc:
            raise HTTPException(status_code=403, detail=f"微信支付官方验签失败: {exc}") from exc
    else:
        signature = request.headers.get("X-Wechat-Signature")
        timestamp = request.headers.get("X-Webhook-Timestamp")
        if not await WebhookSecurity.verify(
            scope="wechat_pay",
            body=body,
            signature=signature,
            secret=settings.WECHAT_PAY_WEBHOOK_SECRET,
            timestamp=timestamp,
        ):
            raise HTTPException(status_code=403, detail="微信支付回调签名验证失败")
        payload = await request.json()
        idempotency_payload = payload

    idempotency_key = str(
        idempotency_payload.get("id")
        or build_webhook_idempotency_key(scope, payload=idempotency_payload, body=body)
    )
    try:
        await handle_verified_webhook(
            db,
            scope=scope,
            payload=payload,
            body=body,
            idempotency_key=idempotency_key,
        )
    except WebhookBusinessError as e:
        logger.warning(f"微信支付回调业务回写失败: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"微信支付回调处理异常: {e}")
        raise HTTPException(status_code=500, detail="微信支付回调处理失败") from e

    return {"code": "SUCCESS", "message": "OK"}


@router.post("/webhook/alipay", summary="支付宝回调", include_in_schema=False)
async def alipay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> PlainTextResponse:
    """
    支付宝异步通知回调。

    显式启用官方模式时按支付宝 RSA2 异步通知验签，未启用时走通用 HMAC 回归路径。
    """
    body = await request.body()
    form = await request.form()
    logger.info(f"[Webhook] 支付宝回调: trade_no={form.get('trade_no')}")
    scope = PaymentProviderType.ALIPAY.value
    payload = dict(form)
    if settings.ALIPAY_OFFICIAL_WEBHOOK_ENABLED:
        try:
            verify_alipay_notification(
                params=payload,
                public_key=settings.ALIPAY_PUBLIC_KEY,
                public_key_path=settings.ALIPAY_PUBLIC_KEY_PATH,
            )
        except OfficialWebhookVerificationError as exc:
            raise HTTPException(status_code=403, detail=f"支付宝官方验签失败: {exc}") from exc
    else:
        signature = request.headers.get("X-Alipay-Signature")
        timestamp = request.headers.get("X-Webhook-Timestamp")
        if not await WebhookSecurity.verify(
            scope="alipay",
            body=body,
            signature=signature,
            secret=settings.ALIPAY_WEBHOOK_SECRET,
            timestamp=timestamp,
        ):
            raise HTTPException(status_code=403, detail="支付宝回调签名验证失败")

    idempotency_key = str(
        payload.get("notify_id") or build_webhook_idempotency_key(scope, payload=payload, body=body)
    )
    try:
        await handle_verified_webhook(
            db,
            scope=scope,
            payload=payload,
            body=body,
            idempotency_key=idempotency_key,
        )
    except WebhookBusinessError as e:
        logger.warning(f"支付宝回调业务回写失败: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception(f"支付宝回调处理异常: {e}")
        raise HTTPException(status_code=500, detail="支付宝回调处理失败") from e

    return PlainTextResponse("success")
