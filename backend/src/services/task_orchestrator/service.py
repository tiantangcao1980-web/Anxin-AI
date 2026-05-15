"""
TaskOrchestratorService —— 任务编排服务门面

封装"创建/入队/启动/进度/完成/失败/审批/取消/查询"等高层操作；
内部调用 ``TaskStateMachine`` 完成状态变更，并通过 SQLAlchemy AsyncSession 持久化。

P2 阶段实装策略：
- 事件总线：Redis Streams（``events.publish_event``）
- 任务队列：Celery（broker=Redis），见 ``celery_app.py`` / ``worker.py``
- worker 当前是占位（sleep + 模拟 progress），未真正调 agent — 留给 P5+。
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_orchestrator.events import (
    TaskEvent,
    TaskEventType,
    publish_event,
)
from src.services.task_orchestrator.models import Task, TaskStatus
from src.services.task_orchestrator.state_machine import (
    InvalidTransitionError,
    TaskStateMachine,
)

# ---------------------------------------------------------------------------
# 默认事件 emitter：把 sync 调用桥接到 Redis Streams 异步发布
# ---------------------------------------------------------------------------


def _default_emitter(event: TaskEvent) -> None:
    """状态机回调：把事件投递到 Redis Streams。

    state_machine.transition() 是同步函数；这里用 ``asyncio.create_task``
    把 publish 调度到当前事件循环。如果当前线程没有事件循环（worker 同步语境），
    退回到 ``asyncio.run`` 一次性发布。
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 同步上下文 — 一次性 run
        try:
            asyncio.run(publish_event(event))
        except Exception as e:  # pragma: no cover
            logger.warning(f"事件发布失败(sync): task={event.task_id} err={e}")
        return

    loop.create_task(_safe_publish(event))


async def _safe_publish(event: TaskEvent) -> None:
    try:
        await publish_event(event)
    except Exception as e:  # pragma: no cover
        logger.warning(f"事件发布失败: task={event.task_id} err={e}")


# ---------------------------------------------------------------------------
# 服务门面
# ---------------------------------------------------------------------------


class TaskOrchestratorService:
    """异步任务编排服务（P2 实装）。

    依赖：
        session: SQLAlchemy AsyncSession
        state_machine: 可选注入；默认使用 ``_default_emitter`` → Redis Streams
        enqueue_fn: 可选入队函数；默认调用 Celery ``run_agent_task.delay``
    """

    def __init__(
        self,
        session: AsyncSession,
        state_machine: TaskStateMachine | None = None,
        enqueue_fn: Any = None,
    ) -> None:
        self.session = session
        self.state_machine = state_machine or TaskStateMachine(emitter=_default_emitter)
        self._enqueue_fn = enqueue_fn

    # ------------------------------------------------------------------
    # 创建 / 入队
    # ------------------------------------------------------------------
    async def create_task(
        self,
        *,
        user_id: str,
        agent_persona: str,
        payload: dict[str, Any] | None = None,
        priority: int = 100,
        parent_task_id: str | None = None,
    ) -> Task:
        """创建任务并落库（初始状态 QUEUED），同时入 Celery 队列。

        参数：
            user_id: 派发人用户 ID
            agent_persona: agent 角色
            payload: 任务参数
            priority: 优先级（默认 100）
            parent_task_id: 父任务 ID（链式调用）

        返回：
            新建的 ``Task`` ORM 实例（已 flush，含 id）。
        """
        task = Task(
            user_id=user_id,
            agent_persona=agent_persona,
            status=TaskStatus.QUEUED,
            priority=priority,
            payload=payload or {},
            parent_task_id=parent_task_id,
        )
        self.session.add(task)
        await self.session.flush()  # 拿到 id
        await self.session.refresh(task)

        # emit QUEUED 事件（不经状态机，因为 task 已经创建即为 QUEUED）
        await publish_event(
            TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.QUEUED,
                payload={"to": TaskStatus.QUEUED.value, "priority": priority},
            )
        )

        await self.enqueue(task)
        return task

    async def enqueue(self, task: Task) -> None:
        """将任务推入执行队列（不改主状态，仍然是 QUEUED）。

        默认实现：调用 ``celery_app.run_agent_task.delay(task.id)``。
        测试时可注入 ``enqueue_fn`` 替换。
        """
        if self._enqueue_fn is not None:
            try:
                self._enqueue_fn(task.id)
            except Exception as e:  # pragma: no cover
                logger.warning(f"自定义 enqueue_fn 失败: task={task.id} err={e}")
            return

        # 默认走 Celery；导入失败/Redis 故障时降级为只记日志
        try:
            from src.services.task_orchestrator.worker import run_agent_task

            run_agent_task.delay(task.id)
        except Exception as e:
            logger.warning(
                f"Celery enqueue 失败，任务停留在 QUEUED 等待人工/重试: "
                f"task={task.id} err={e}"
            )

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    async def start(
        self,
        task_id: str,
        *,
        sandbox_id: str | None = None,
    ) -> Task:
        """worker 取到任务后调用：QUEUED → PROVISIONING → RUNNING。"""
        task = await self._get_or_raise(task_id)
        self.state_machine.transition(task, TaskStatus.PROVISIONING, sandbox_id=sandbox_id)
        self.state_machine.transition(task, TaskStatus.RUNNING)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def progress(
        self,
        task_id: str,
        payload: dict[str, Any],
    ) -> None:
        """上报中间进度（不改 status，仅发 ``PROGRESS`` 事件）。

        参数：
            task_id: 任务 ID
            payload: 进度 payload，可含 ``progress`` (0~1) / ``message`` / 其他自定义字段
        """
        task = await self._get_or_raise(task_id)
        if task.status != TaskStatus.RUNNING:
            logger.debug(
                f"progress 事件在非 RUNNING 状态发出，仍允许: "
                f"task={task_id} status={task.status.value}"
            )
        await publish_event(
            TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.PROGRESS,
                payload=payload,
            )
        )

    async def complete(self, task_id: str, result: dict[str, Any]) -> Task:
        """RUNNING → REPORTING → DONE，并写入 result。"""
        task = await self._get_or_raise(task_id)
        self.state_machine.transition(task, TaskStatus.REPORTING)
        self.state_machine.transition(task, TaskStatus.DONE, result=result)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def fail(self, task_id: str, error: dict[str, Any]) -> Task:
        """任意非终态 → FAILED，并写入 error。"""
        task = await self._get_or_raise(task_id)
        self.state_machine.transition(task, TaskStatus.FAILED, error=error)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def request_approval(
        self,
        task_id: str,
        reason: str | None = None,
    ) -> Task:
        """RUNNING → NEEDS_APPROVAL，暂停 worker。"""
        task = await self._get_or_raise(task_id)
        self.state_machine.transition(
            task,
            TaskStatus.NEEDS_APPROVAL,
            message=reason or "等待人工审批",
        )
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def approve(self, task_id: str, approver_id: str) -> Task:
        """NEEDS_APPROVAL → RUNNING，继续 worker。"""
        task = await self._get_or_raise(task_id)
        self.state_machine.transition(
            task,
            TaskStatus.RUNNING,
            approver_id=approver_id,
            message="审批通过",
        )
        # 单独发一个 APPROVED 语义事件（前端用来更新审批 UI）
        await publish_event(
            TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.APPROVED,
                payload={"approver_id": approver_id},
            )
        )
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def reject(
        self,
        task_id: str,
        approver_id: str,
        reason: str,
    ) -> Task:
        """NEEDS_APPROVAL → CANCELLED（驳回视为取消）。"""
        task = await self._get_or_raise(task_id)
        if task.status != TaskStatus.NEEDS_APPROVAL:
            raise InvalidTransitionError(task.status, TaskStatus.CANCELLED)
        self.state_machine.transition(
            task,
            TaskStatus.CANCELLED,
            error={
                "code": "APPROVAL_REJECTED",
                "message": reason,
                "approver_id": approver_id,
            },
            reason=reason,
            approver_id=approver_id,
        )
        # 单独发一个 REJECTED 语义事件
        await publish_event(
            TaskEvent(
                task_id=task.id,
                event_type=TaskEventType.REJECTED,
                payload={"approver_id": approver_id, "reason": reason},
            )
        )
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def cancel(self, task_id: str) -> Task:
        """任意非终态 → CANCELLED。"""
        task = await self._get_or_raise(task_id)
        if task.status in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED):
            raise InvalidTransitionError(task.status, TaskStatus.CANCELLED)
        self.state_machine.transition(task, TaskStatus.CANCELLED)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    async def get_task(self, task_id: str) -> Task | None:
        """按 ID 查询任务（含 result/error）。"""
        result = await self.session.execute(select(Task).where(Task.id == task_id))
        return result.scalar_one_or_none()

    async def list_tasks_for_user(
        self,
        user_id: str,
        *,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """分页列出某用户的任务（按 created_at 倒序）。"""
        stmt = select(Task).where(Task.user_id == user_id)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        stmt = stmt.order_by(desc(Task.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # 内部 helper
    # ------------------------------------------------------------------
    async def _get_or_raise(self, task_id: str) -> Task:
        task = await self.get_task(task_id)
        if task is None:
            raise LookupError(f"agent task 不存在: {task_id}")
        return task
