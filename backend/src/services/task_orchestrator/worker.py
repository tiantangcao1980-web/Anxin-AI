"""
task_orchestrator —— Celery worker（P2 占位实现）

当前版本只验证 **状态流转 + 事件流通**：
    1. service.start(task_id)            — QUEUED → PROVISIONING → RUNNING
    2. 模拟干活：sleep(2) + 推 3 个 progress 事件
    3. service.complete(task_id, result) — RUNNING → REPORTING → DONE

未来 P5+ 才会真的调度 agent persona 执行业务。
P3 阶段会在此基础上加上沙箱隔离 + 心跳超时检测。
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from src.core.database import async_session_maker
from src.services.task_orchestrator.celery_app import celery_app
from src.services.task_orchestrator.service import TaskOrchestratorService

PROGRESS_STEPS: list[tuple[float, str]] = [
    (0.2, "分析中..."),
    (0.55, "调用工具中..."),
    (0.9, "汇总结果..."),
]


async def _run_async(task_id: str) -> dict[str, Any]:
    """异步业务体（被 Celery 同步任务桥接调用）。"""
    async with async_session_maker() as session:
        try:
            service = TaskOrchestratorService(session)

            # 1. 启动
            await service.start(task_id)
            await session.commit()

            # 2. 占位干活：sleep + 多次 progress
            for ratio, msg in PROGRESS_STEPS:
                await asyncio.sleep(2 / len(PROGRESS_STEPS))
                await service.progress(
                    task_id,
                    {"progress": ratio, "message": msg},
                )

            # 3. 完成
            result = {"summary": "P2 MVP — 占位结果", "ok": True}
            await service.complete(task_id, result)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.exception(f"agent task 执行失败: task={task_id} err={e}")
            # 单独事务标 failed，避免和上面 rollback 冲突
            try:
                async with async_session_maker() as fail_session:
                    fail_service = TaskOrchestratorService(fail_session)
                    await fail_service.fail(
                        task_id,
                        {"code": "WORKER_EXCEPTION", "message": str(e)},
                    )
                    await fail_session.commit()
            except Exception as inner:  # pragma: no cover
                logger.error(f"标记 failed 也失败: task={task_id} err={inner}")
            raise


@celery_app.task(
    name="task_orchestrator.run_agent_task",
    bind=True,
    autoretry_for=(),  # MVP：不自动重试，失败由人工 / 上层触发
    acks_late=True,
)
def run_agent_task(self, task_id: str) -> dict[str, Any]:  # noqa: D401
    """Celery 入口任务（同步签名）。

    参数：
        task_id: ``agent_tasks.id`` UUID 字符串

    返回：
        最终 result dict（同时已写入 DB）。
    """
    logger.info(f"[celery] run_agent_task start: task={task_id}")
    result = asyncio.run(_run_async(task_id))
    logger.info(f"[celery] run_agent_task done : task={task_id}")
    return result


__all__ = ["run_agent_task"]
