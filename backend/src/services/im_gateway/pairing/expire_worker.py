"""
IM 配对授权过期清理 worker（Celery beat 定时任务）

调度策略：每 10 分钟扫描一次（粒度足够覆盖 24h 窗口的 SLA）。
注册方式（在 ``celery_app.py`` 启动 beat 时附加 schedule，或通过命令行）::

    celery -A src.services.task_orchestrator.celery_app beat -l info
    celery -A src.services.task_orchestrator.celery_app worker -l info -Q im_gateway

任务体复用 ``PairingService.cleanup_expired()``，不直接操作 ORM。
"""

from __future__ import annotations

import asyncio

from loguru import logger

from src.core.database import async_session_maker
from src.services.im_gateway.pairing.service import PairingService
from src.services.task_orchestrator.celery_app import celery_app

# 每 10 分钟一次（足够覆盖 24h 配对窗口的过期 SLA）
PAIRING_CLEANUP_SCHEDULE_SECONDS = 10 * 60


@celery_app.task(
    name="im_gateway.cleanup_expired_pairing_requests",
    queue="im_gateway",
    bind=True,
)
def cleanup_expired_pairing_requests(self) -> int:
    """Celery beat 入口：扫描所有 PENDING 且已过期的配对请求并置 EXPIRED。

    返回：本次更新的行数（用于监控 / 告警）。
    """
    try:
        affected = asyncio.run(_cleanup_async())
    except RuntimeError:
        # 事件循环已存在（极少数边界场景：worker 内嵌在 async runtime 时），
        # 退化到新建独立 loop。
        loop = asyncio.new_event_loop()
        try:
            affected = loop.run_until_complete(_cleanup_async())
        finally:
            loop.close()

    logger.info("celery.im_pairing.cleanup_expired affected={}", affected)
    return affected


async def _cleanup_async() -> int:
    async with async_session_maker() as session:
        service = PairingService(session)
        affected = await service.cleanup_expired()
        await session.commit()
        return affected


def register_beat_schedule() -> None:
    """把过期清理 task 注册到 celery beat（懒注册，避免 import 副作用）。

    main API 进程启动时不需要调用；只有 ``celery beat`` 进程在初始化时调用。
    """
    celery_app.conf.beat_schedule = {
        **(celery_app.conf.beat_schedule or {}),
        "im_gateway.cleanup_expired_pairing_requests": {
            "task": "im_gateway.cleanup_expired_pairing_requests",
            "schedule": PAIRING_CLEANUP_SCHEDULE_SECONDS,
        },
    }


__all__ = [
    "cleanup_expired_pairing_requests",
    "register_beat_schedule",
    "PAIRING_CLEANUP_SCHEDULE_SECONDS",
]
