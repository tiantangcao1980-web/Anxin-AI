# -*- coding: utf-8 -*-
"""
Celery 周期任务：扫描过期未处理的 ConfirmTicket → 标 expired

每 5 分钟跑一次（cron `*/5`），见 __init__.register_beat_schedule。
"""
from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from src.services.task_orchestrator.celery_app import celery_app


@celery_app.task(name="managed_agents.confirm_expire.run", acks_late=True)
def run() -> dict[str, Any]:
    async def _job() -> dict[str, Any]:
        from src.core.database import async_session_maker
        from src.services.governance import confirm_inbox

        try:
            async with async_session_maker() as session:
                expired = await confirm_inbox.expire_overdue(session)
                await session.commit()
            logger.info("confirm_expire: expired={}", expired)
            return {"expired": expired}
        except Exception as e:  # noqa: BLE001
            logger.warning("confirm_expire 失败：{}", e)
            return {"expired": 0, "error": repr(e)}

    return asyncio.run(_job())
