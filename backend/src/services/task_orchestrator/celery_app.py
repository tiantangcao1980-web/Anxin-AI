# -*- coding: utf-8 -*-
"""
Celery 实例 —— task_orchestrator 异步执行总线

broker / backend 都用 Redis（与项目现有 cache / SSE 共用 Redis 实例）。
启动 worker::

    cd backend && celery -A src.services.task_orchestrator.celery_app:celery_app worker -l info -Q agent_tasks

注意：
- Celery 任务体 (``worker.run_agent_task``) 是同步函数，内部用 ``asyncio.run`` 起异步事务。
- 任务路由当前固定到 ``agent_tasks`` 队列；后续若引入 sandbox provider 可按 persona 拆队列。
"""

from __future__ import annotations

from celery import Celery

from src.core.config import settings


def _broker_url() -> str:
    return getattr(settings, "CELERY_BROKER_URL", None) or settings.REDIS_URL


def _backend_url() -> str:
    return getattr(settings, "CELERY_RESULT_BACKEND", None) or settings.REDIS_URL


celery_app = Celery(
    "anxin_agent_tasks",
    broker=_broker_url(),
    backend=_backend_url(),
    include=["src.services.task_orchestrator.worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_default_queue="agent_tasks",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # MVP：避免单 worker 抢过多任务
    broker_connection_retry_on_startup=True,
)


__all__ = ["celery_app"]
