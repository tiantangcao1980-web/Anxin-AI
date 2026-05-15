"""Durable webhook idempotency helpers."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.webhook import WebhookReceived

PROCESSING = "processing"
PROCESSED = "processed"
FAILED = "failed"


class WebhookProcessingLockUnavailable(RuntimeError):  # noqa: N818
    """Raised when webhook processing cannot acquire its short lease."""


_LOCAL_WEBHOOK_LOCK_GUARD = asyncio.Lock()
_LOCAL_WEBHOOK_LOCKS: dict[str, asyncio.Lock] = {}

_EVENT_ID_KEYS = (
    "event_id",
    "eventId",
    "notify_id",
    "notifyId",
    "notification_id",
    "notificationId",
    "webhook_id",
    "webhookId",
    "idempotency_key",
    "idempotencyKey",
)


def _candidate_dicts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [payload]
    for key in ("extra", "data", "event", "payload", "resource"):
        value = payload.get(key)
        if isinstance(value, dict):
            candidates.append(value)
            plaintext = value.get("plaintext")
            if isinstance(plaintext, dict):
                candidates.append(plaintext)
    return candidates


def _first_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for source in _candidate_dicts(payload):
        for key in keys:
            value = source.get(key)
            if value is not None:
                text = str(value).strip()
                if text:
                    return text
    return None


def build_webhook_idempotency_key(
    scope: str,
    *,
    payload: dict[str, Any],
    body: bytes,
) -> str:
    """Build a stable provider event key, falling back to a canonical body digest."""

    explicit_key = _first_string(payload, _EVENT_ID_KEYS)
    if explicit_key:
        return explicit_key[:128]

    if body:
        digest_source = body
    else:
        digest_source = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(scope.encode("utf-8") + b":" + digest_source).hexdigest()


async def begin_webhook(
    db: AsyncSession,
    *,
    scope: str,
    idempotency_key: str,
    payload: dict[str, Any],
) -> tuple[WebhookReceived, bool]:
    """Create or reuse a webhook record.

    Returns `(record, already_handled)`. Existing processed or in-flight records are
    treated as handled so providers can safely retry without double-applying side
    effects. Existing failed records are retried.
    """

    result = await db.execute(
        select(WebhookReceived).where(
            WebhookReceived.scope == scope,
            WebhookReceived.idempotency_key == idempotency_key,
        )
    )
    record = result.scalar_one_or_none()
    if record is not None:
        if record.status in {PROCESSED, PROCESSING}:
            return record, True
        record.status = PROCESSING
        record.payload = payload
        record.error = None
        record.next_retry_at = None
        await db.flush()
        return record, False

    record = WebhookReceived(
        scope=scope,
        idempotency_key=idempotency_key,
        payload=payload,
        status=PROCESSING,
        retry_count=0,
    )
    db.add(record)
    await db.flush()
    return record, False


@asynccontextmanager
async def webhook_processing_lock(scope: str, idempotency_key: str) -> AsyncIterator[None]:
    """Serialize identical webhook deliveries around idempotency + side effects."""

    lock_key = f"webhook-processing:{scope}:{idempotency_key}"
    backend = settings.WEBHOOK_PROCESSING_LOCK_BACKEND.lower()

    if backend == "local" or (
        backend == "auto" and settings.ENVIRONMENT not in {"production", "staging"}
    ):
        async with _LOCAL_WEBHOOK_LOCK_GUARD:
            lock = _LOCAL_WEBHOOK_LOCKS.setdefault(lock_key, asyncio.Lock())
        async with lock:
            yield
        return

    redis_client = None
    token = secrets.token_urlsafe(24)
    try:
        import redis.asyncio as redis

        redis_from_url = cast(Any, redis.from_url)
        redis_client = redis_from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=3,
        )
        await redis_client.ping()
        deadline = asyncio.get_running_loop().time() + max(
            float(settings.WEBHOOK_PROCESSING_LOCK_WAIT_SECONDS), 0.0
        )
        while True:
            acquired = await redis_client.set(
                lock_key,
                token,
                nx=True,
                ex=max(int(settings.WEBHOOK_PROCESSING_LOCK_TTL_SECONDS), 1),
            )
            if acquired:
                break
            if asyncio.get_running_loop().time() >= deadline:
                raise WebhookProcessingLockUnavailable("Webhook event is already processing")
            await asyncio.sleep(0.1)
        yield
    except WebhookProcessingLockUnavailable:
        raise
    except Exception as exc:
        if settings.ENVIRONMENT in {"production", "staging"} or backend == "redis":
            raise WebhookProcessingLockUnavailable("Webhook processing lock unavailable") from exc
        logger.warning("Webhook processing lock uses local fallback: {}", exc)
        async with _LOCAL_WEBHOOK_LOCK_GUARD:
            lock = _LOCAL_WEBHOOK_LOCKS.setdefault(lock_key, asyncio.Lock())
        async with lock:
            yield
    finally:
        if redis_client is not None:
            script = """
            if redis.call('GET', KEYS[1]) == ARGV[1] then
                return redis.call('DEL', KEYS[1])
            end
            return 0
            """
            try:
                await redis_client.eval(script, 1, lock_key, token)
                await redis_client.aclose()
            except Exception as exc:
                logger.warning("释放 webhook processing Redis 锁失败: {}", exc)


async def mark_webhook_processed(record: WebhookReceived) -> None:
    """Mark a webhook record as successfully processed."""

    record.status = PROCESSED
    record.processed_at = datetime.now(UTC)
    record.error = None
    record.next_retry_at = None


async def mark_webhook_failed(record: WebhookReceived, error: Exception | str) -> None:
    """Mark a webhook record as failed while preserving it for later retry."""

    now = datetime.now(UTC)
    record.status = FAILED
    record.processed_at = None
    record.error = str(error)[:4000]
    record.retry_count = (record.retry_count or 0) + 1
    record.last_retry_at = now
    if record.retry_count >= settings.WEBHOOK_RETRY_MAX_ATTEMPTS:
        record.next_retry_at = None
        return

    delay = min(
        settings.WEBHOOK_RETRY_MAX_DELAY_SECONDS,
        settings.WEBHOOK_RETRY_BASE_DELAY_SECONDS * (2 ** max(record.retry_count - 1, 0)),
    )
    record.next_retry_at = now + timedelta(seconds=delay)
