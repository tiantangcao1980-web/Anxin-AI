"""Background loop for retrying failed webhook records."""

import asyncio

from loguru import logger

from src.core.config import settings
from src.core.database import async_session_maker
from src.services.webhook_retry_service import retry_due_failed_webhooks


async def webhook_retry_worker(stop_event: asyncio.Event) -> None:
    """Periodically retry due failed webhooks until the application stops."""

    logger.info(
        "webhook 自动重试 worker 已启动: interval={}s batch={} max_attempts={}",
        settings.WEBHOOK_RETRY_INTERVAL_SECONDS,
        settings.WEBHOOK_RETRY_BATCH_SIZE,
        settings.WEBHOOK_RETRY_MAX_ATTEMPTS,
    )
    while not stop_event.is_set():
        try:
            async with async_session_maker() as db:
                summary = await retry_due_failed_webhooks(db)
                if summary["attempted"]:
                    logger.info(f"webhook 自动重试完成: {summary}")
        except Exception as exc:
            logger.exception(f"webhook 自动重试 worker 异常: {exc}")

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=max(settings.WEBHOOK_RETRY_INTERVAL_SECONDS, 1),
            )
        except TimeoutError:
            continue

    logger.info("webhook 自动重试 worker 已停止")
