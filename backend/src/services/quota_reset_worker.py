# -*- coding: utf-8 -*-
"""
QuotaResetWorker — A4 (2026-05-14)

Celery beat 每日凌晨触发, 找出今天周期结束的订阅, 把对应用户的
cost_tracker 累计 archive 到 DB 并清零内存, 同时为下一周期创建新行。

启用方式 (celery_app.conf.beat_schedule):
    "quota-reset-daily": {
        "task": "src.services.quota_reset_worker.run_daily_quota_reset",
        "schedule": crontab(minute="5", hour="0"),  # 每天 00:05
    }

也可手动通过 admin API 触发 (POST /admin/quota/reset/{user_id})。
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import and_, select

from src.core.database import get_db_context
from src.harness.cost_tracker import cost_tracker
from src.models.billing import Subscription
from src.services.task_orchestrator.celery_app import celery_app


def _calc_next_period(start: date, length_days: int = 30) -> tuple[date, date]:
    """根据已结束周期推断下一个周期起止 (默认月度)。"""
    new_start = start + timedelta(days=length_days)
    new_end = new_start + timedelta(days=length_days - 1)
    return new_start, new_end


async def _run_daily_quota_reset_async() -> dict[str, Any]:
    """异步实现, Celery sync 任务里用 asyncio.run 调起。"""
    today = date.today()
    stats: dict[str, Any] = {
        "checked_subscriptions": 0,
        "reset_users": 0,
        "errors": 0,
        "details": [],
    }

    async with get_db_context() as db:
        # 找出 current_period_end == 今天 的活跃订阅 (今天是周期最后一天)
        # 也兼容 < today 的 (兜底, 防止 cron 错过执行)
        result = await db.execute(
            select(Subscription).where(
                and_(
                    Subscription.status.in_(["active", "trial"]),
                    Subscription.current_period_end <= today,
                )
            )
        )
        subs = result.scalars().all()
        stats["checked_subscriptions"] = len(subs)

        for sub in subs:
            try:
                # 推断新周期 (沿用 current_period_end 之后的 30 天)
                new_start, new_end = _calc_next_period(
                    sub.current_period_end, length_days=30
                )
                outcome = await cost_tracker.archive_and_reset_user(
                    db,
                    sub.user_id,
                    new_period_start=new_start,
                    new_period_end=new_end,
                )
                if outcome["archived_tokens"] > 0 or outcome["new_period_started"]:
                    stats["reset_users"] += 1
                    stats["details"].append({
                        "user_id": sub.user_id,
                        "archived_tokens": outcome["archived_tokens"],
                        "archived_cost": outcome["archived_cost"],
                        "new_period": f"{new_start}~{new_end}",
                    })
                # 同步推进订阅 current_period (保持订阅本身的状态机一致)
                # 注意: 真实生产线由 payment_service 在续费成功时推进; 这里仅在
                # auto_renew=True 时辅助推进, 避免无效订阅占用查询
                if getattr(sub, "auto_renew", False):
                    sub.current_period_start = new_start
                    sub.current_period_end = new_end
            except Exception as e:
                stats["errors"] += 1
                logger.error(
                    f"[QuotaReset] user={sub.user_id} reset failed: {e}"
                )

        await db.commit()

    logger.info(
        f"[QuotaReset] daily run done: checked={stats['checked_subscriptions']} "
        f"reset={stats['reset_users']} errors={stats['errors']}"
    )
    return stats


@celery_app.task(name="src.services.quota_reset_worker.run_daily_quota_reset")
def run_daily_quota_reset() -> dict[str, Any]:
    """Celery 同步入口: asyncio.run 包裹异步主体。"""
    return asyncio.run(_run_daily_quota_reset_async())


__all__ = ["run_daily_quota_reset", "_run_daily_quota_reset_async"]
