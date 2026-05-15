"""Unified verified webhook handling and business event dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.payment import PaymentOrder
from src.models.webhook import WebhookReceived
from src.services.esign_webhook_service import ESignWebhookError, apply_esign_webhook
from src.services.payment_webhook_service import PaymentWebhookError, apply_payment_webhook
from src.services.webhook_idempotency_service import (
    begin_webhook,
    build_webhook_idempotency_key,
    mark_webhook_failed,
    mark_webhook_processed,
    webhook_processing_lock,
)

PAYMENT_SCOPES = {"wechat_pay", "alipay"}
ESIGN_SCOPE = "esign"
SUPPORTED_WEBHOOK_SCOPES = PAYMENT_SCOPES | {ESIGN_SCOPE}


class WebhookHandlerError(ValueError):
    """Raised when a verified webhook cannot be handled."""


class WebhookBusinessError(WebhookHandlerError):
    """Raised when a verified webhook fails business writeback."""


class UnsupportedWebhookScopeError(WebhookHandlerError):
    """Raised for a webhook scope without a business event handler."""


@dataclass(slots=True)
class WebhookHandleResult:
    """Result of handling one verified webhook delivery."""

    record: WebhookReceived
    already_handled: bool
    result: dict[str, Any] | None = None


def payment_order_result(order: PaymentOrder) -> dict[str, Any]:
    """Return the stable admin/API summary for a payment webhook result."""

    return {
        "order_id": order.id,
        "status": order.status,
        "payment_provider": order.payment_provider,
        "transaction_id": order.transaction_id,
    }


async def apply_webhook_business_event(
    db: AsyncSession,
    *,
    scope: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Dispatch a verified webhook payload to its canonical business writeback."""

    if scope in PAYMENT_SCOPES:
        order = await apply_payment_webhook(
            db,
            provider=scope,
            payload=payload,
        )
        return payment_order_result(order)

    if scope == ESIGN_SCOPE:
        return await apply_esign_webhook(db, payload=payload)

    raise UnsupportedWebhookScopeError(f"Unsupported webhook scope: {scope}")


async def handle_verified_webhook(
    db: AsyncSession,
    *,
    scope: str,
    payload: dict[str, Any],
    body: bytes = b"",
    idempotency_key: str | None = None,
) -> WebhookHandleResult:
    """Persist idempotency, apply business effects once, and commit the delivery."""

    if scope not in SUPPORTED_WEBHOOK_SCOPES:
        raise UnsupportedWebhookScopeError(f"Unsupported webhook scope: {scope}")

    resolved_key = str(
        idempotency_key or build_webhook_idempotency_key(scope, payload=payload, body=body)
    )
    async with webhook_processing_lock(scope, resolved_key):
        record, already_handled = await begin_webhook(
            db,
            scope=scope,
            idempotency_key=resolved_key,
            payload=payload,
        )
        if already_handled:
            await db.commit()
            return WebhookHandleResult(record=record, already_handled=True)

        try:
            result = await apply_webhook_business_event(db, scope=scope, payload=payload)
            await mark_webhook_processed(record)
            await db.commit()
            return WebhookHandleResult(
                record=record,
                already_handled=False,
                result=result,
            )
        except (PaymentWebhookError, ESignWebhookError, UnsupportedWebhookScopeError) as exc:
            await mark_webhook_failed(record, exc)
            await db.commit()
            raise WebhookBusinessError(str(exc)) from exc
        except Exception as exc:
            await db.rollback()
            raise WebhookHandlerError(str(exc)) from exc
