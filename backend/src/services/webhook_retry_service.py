"""Retry failed webhook records through their business writeback handlers."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.webhook import WebhookReceived
from src.services.webhook_handler import PAYMENT_SCOPES, apply_webhook_business_event
from src.services.webhook_idempotency_service import (
    FAILED,
    PROCESSING,
    mark_webhook_failed,
    mark_webhook_processed,
)


class WebhookRetryError(ValueError):
    """Raised when a failed webhook record cannot be retried."""


async def retry_failed_webhook(
    db: AsyncSession,
    record: WebhookReceived,
) -> dict[str, Any]:
    """Retry one failed webhook record using the existing business writeback path."""

    if record.status != FAILED:
        raise WebhookRetryError(f"Webhook record is not failed: {record.status}")
    if record.scope not in PAYMENT_SCOPES and record.scope != "esign":
        raise WebhookRetryError(f"Unsupported webhook scope for retry: {record.scope}")

    record.status = PROCESSING
    record.error = None
    await db.flush()

    try:
        result = await apply_webhook_business_event(
            db,
            scope=record.scope,
            payload=record.payload,
        )
        await mark_webhook_processed(record)
        await db.flush()
        return result
    except Exception as exc:
        await mark_webhook_failed(record, exc)
        await db.flush()
        raise WebhookRetryError(str(exc)) from exc


async def retry_due_failed_webhooks(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int | None = None,
    max_attempts: int | None = None,
) -> dict[str, int]:
    """Retry failed webhook records whose backoff window has elapsed."""

    now = now or datetime.now(UTC)
    limit = limit or settings.WEBHOOK_RETRY_BATCH_SIZE
    max_attempts = max_attempts or settings.WEBHOOK_RETRY_MAX_ATTEMPTS
    result = await db.execute(
        select(WebhookReceived)
        .where(
            and_(
                WebhookReceived.status == FAILED,
                WebhookReceived.retry_count < max_attempts,
                or_(
                    WebhookReceived.next_retry_at.is_(None),
                    WebhookReceived.next_retry_at <= now,
                ),
            )
        )
        .order_by(WebhookReceived.next_retry_at.asc(), WebhookReceived.created_at.asc())
        .limit(limit)
    )
    records = list(result.scalars().all())
    summary = {"attempted": 0, "succeeded": 0, "failed": 0}

    for record in records:
        summary["attempted"] += 1
        try:
            await retry_failed_webhook(db, record)
            await db.commit()
            summary["succeeded"] += 1
        except WebhookRetryError as exc:
            await db.commit()
            summary["failed"] += 1
            logger.warning(f"webhook 自动重试失败: id={record.id}, scope={record.scope}, error={exc}")
        except Exception as exc:
            await db.rollback()
            summary["failed"] += 1
            logger.exception(f"webhook 自动重试异常: id={record.id}, scope={record.scope}, error={exc}")

    return summary
