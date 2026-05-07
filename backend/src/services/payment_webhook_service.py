"""Payment webhook business writeback helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.billing import Subscription
from src.models.payment import PaymentOrder
from src.services.payment_service import PaymentStatusEnum
from src.services.subscription_service import SubscriptionService, SubscriptionStateError
from src.services.webhook_events import PaymentWebhookEvent


class PaymentWebhookError(ValueError):
    """Raised when a payment webhook cannot be applied safely."""


SUCCESS_STATES = {
    "paid",
    "success",
    "succeeded",
    "trade_success",
    "trade_finished",
    "transaction.success",
    "successed",
}
FAILED_STATES = {"failed", "fail", "trade_failed", "pay_error"}
CLOSED_STATES = {"closed", "cancelled", "canceled", "trade_closed"}
REFUNDED_STATES = {"refunded", "refund", "trade_refund", "refund_success"}


def _normalize_state(raw: Any) -> str:
    return str(raw or "").strip().lower()


def _extract_first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    resource = payload.get("resource")
    if isinstance(resource, dict):
        plaintext = resource.get("plaintext")
        if isinstance(plaintext, dict):
            value = _extract_first(plaintext, keys)
            if value not in (None, ""):
                return value
        value = _extract_first(resource, keys)
        if value not in (None, ""):
            return value
    return None


def _status_from_payload(payload: dict[str, Any]) -> PaymentStatusEnum:
    state = _extract_payment_state(payload)
    if state in SUCCESS_STATES:
        return PaymentStatusEnum.PAID
    if state in FAILED_STATES:
        return PaymentStatusEnum.FAILED
    if state in CLOSED_STATES:
        return PaymentStatusEnum.CLOSED
    if state in REFUNDED_STATES:
        return PaymentStatusEnum.REFUNDED
    raise PaymentWebhookError(f"Unsupported payment webhook status: {state or '<missing>'}")


def _extract_payment_state(payload: dict[str, Any]) -> str:
    return _normalize_state(
        _extract_first(
            payload,
            (
                "status",
                "trade_status",
                "trade_state",
                "event_type",
                "event",
                "payment_status",
            ),
        )
    )


def _extract_order_id(payload: dict[str, Any]) -> str:
    order_id = _extract_first(
        payload,
        (
            "out_trade_no",
            "order_id",
            "order",
            "order_no",
            "merchant_order_id",
        ),
    )
    if not order_id:
        order_id = _extract_first(payload, ("id",))
    if not order_id:
        raise PaymentWebhookError("Missing order id in payment webhook")
    return str(order_id)


def _extract_transaction_id(payload: dict[str, Any]) -> str | None:
    value = _extract_first(
        payload,
        (
            "transaction_id",
            "trade_no",
            "payment_id",
            "channel_transaction_id",
        ),
    )
    return str(value) if value else None


def _extract_event_id(payload: dict[str, Any]) -> str | None:
    value = _extract_first(
        payload,
        (
            "event_id",
            "eventId",
            "notify_id",
            "notifyId",
            "id",
        ),
    )
    return str(value) if value else None


def _extract_event_type(payload: dict[str, Any]) -> str | None:
    value = _extract_first(
        payload,
        (
            "event_type",
            "eventType",
            "event",
            "trade_status",
            "trade_state",
            "status",
        ),
    )
    return str(value) if value else None


def parse_payment_webhook_event(
    *,
    provider: str,
    payload: dict[str, Any],
) -> PaymentWebhookEvent:
    """Normalize a verified provider payload into a stable payment event."""

    return PaymentWebhookEvent(
        provider=provider,
        order_id=_extract_order_id(payload),
        status=_status_from_payload(payload),
        provider_status=_extract_payment_state(payload),
        transaction_id=_extract_transaction_id(payload),
        event_id=_extract_event_id(payload),
        event_type=_extract_event_type(payload),
    )


async def apply_payment_webhook(
    db: AsyncSession,
    *,
    provider: str,
    payload: dict[str, Any],
    event: PaymentWebhookEvent | None = None,
) -> PaymentOrder:
    """Apply a verified payment webhook to the local order and related subscription."""
    event = event or parse_payment_webhook_event(provider=provider, payload=payload)
    if event.provider != provider:
        raise PaymentWebhookError(
            f"Payment event provider mismatch: expected {provider}, got {event.provider}"
        )
    order_id = event.order_id
    status = event.status
    transaction_id = event.transaction_id

    lookup_ids = [order_id]
    try:
        canonical_order_id = str(UUID(order_id))
    except ValueError:
        canonical_order_id = None
    if canonical_order_id and canonical_order_id not in lookup_ids:
        lookup_ids.append(canonical_order_id)

    result = await db.execute(select(PaymentOrder).where(PaymentOrder.id.in_(lookup_ids)))
    order = result.scalar_one_or_none()
    if not order:
        raise PaymentWebhookError(f"Payment order not found: {order_id}")
    if order.payment_provider != provider:
        raise PaymentWebhookError(
            f"Payment provider mismatch: expected {order.payment_provider}, got {provider}"
        )

    now = datetime.now(UTC)
    order.status = status.value
    if transaction_id:
        order.transaction_id = transaction_id
    if status == PaymentStatusEnum.PAID and not order.paid_at:
        order.paid_at = now
    elif status == PaymentStatusEnum.REFUNDED and not order.refunded_at:
        order.refunded_at = now

    if order.order_type == "subscription" and order.related_id:
        sub_result = await db.execute(
            select(Subscription).where(Subscription.id == order.related_id)
        )
        subscription = sub_result.scalar_one_or_none()
        if subscription:
            service = SubscriptionService(db)
            try:
                if status == PaymentStatusEnum.PAID:
                    await service.activate_or_renew_from_payment(
                        subscription,
                        payment_id=order.id,
                        event_data={"provider": provider, "transaction_id": transaction_id},
                    )
                elif status == PaymentStatusEnum.FAILED:
                    await service.mark_past_due_from_payment(
                        subscription,
                        payment_id=order.id,
                    )
                elif status == PaymentStatusEnum.CLOSED:
                    await service.transition_subscription(
                        subscription,
                        "cancelled",
                        event_type="payment_closed",
                        reason="payment_closed",
                        payment_id=order.id,
                    )
                elif status == PaymentStatusEnum.REFUNDED:
                    await service.expire_from_refund(
                        subscription,
                        payment_id=order.id,
                    )
            except SubscriptionStateError as exc:
                raise PaymentWebhookError(str(exc)) from exc

    await db.flush()
    return order
