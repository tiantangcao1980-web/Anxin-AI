# -*- coding: utf-8 -*-
"""
异步任务状态机

合法转移图（见 README.md 中的 mermaid 示意）::

    queued ──► provisioning ──► running ──► reporting ──► done
                                  │           │
                                  │           └──► needs_approval ──► running
                                  │                                   │
                                  └─────────────► failed ◄────────────┘

所有状态变更必须通过 ``TaskStateMachine.transition`` 进入，
确保时间戳（started_at / finished_at）和事件（``TaskEvent``）一致写入。

实现阶段：P2。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from src.services.task_orchestrator.events import TaskEvent, TaskEventType
from src.services.task_orchestrator.models import Task, TaskStatus


class InvalidTransitionError(RuntimeError):
    """非法状态转移异常（早失败，避免脏数据）。"""

    def __init__(self, from_state: TaskStatus, to_state: TaskStatus) -> None:
        super().__init__(
            f"非法状态转移: {from_state.value} -> {to_state.value}"
        )
        self.from_state = from_state
        self.to_state = to_state


# 合法转移表：from -> set(to)
TRANSITIONS: dict[TaskStatus, frozenset[TaskStatus]] = {
    TaskStatus.QUEUED: frozenset({TaskStatus.PROVISIONING, TaskStatus.FAILED}),
    TaskStatus.PROVISIONING: frozenset({TaskStatus.RUNNING, TaskStatus.FAILED}),
    TaskStatus.RUNNING: frozenset(
        {TaskStatus.REPORTING, TaskStatus.NEEDS_APPROVAL, TaskStatus.FAILED}
    ),
    TaskStatus.REPORTING: frozenset({TaskStatus.DONE, TaskStatus.FAILED}),
    TaskStatus.NEEDS_APPROVAL: frozenset(
        {TaskStatus.RUNNING, TaskStatus.FAILED}
    ),
    TaskStatus.DONE: frozenset(),  # 终态
    TaskStatus.FAILED: frozenset(),  # 终态
}


# 事件类型映射：进入某状态时发出的事件
ENTER_EVENT: dict[TaskStatus, TaskEventType] = {
    TaskStatus.QUEUED: TaskEventType.QUEUED,
    TaskStatus.PROVISIONING: TaskEventType.PROVISIONING,
    TaskStatus.RUNNING: TaskEventType.STARTED,
    TaskStatus.REPORTING: TaskEventType.REPORTING,
    TaskStatus.DONE: TaskEventType.COMPLETED,
    TaskStatus.FAILED: TaskEventType.FAILED,
    TaskStatus.NEEDS_APPROVAL: TaskEventType.NEEDS_APPROVAL,
}


# 事件回调签名：(event) -> Awaitable[None] | None
EventEmitter = Callable[[TaskEvent], Any]


class TaskStateMachine:
    """任务状态机。

    用法::

        sm = TaskStateMachine(emitter=lambda ev: redis.publish(...))
        sm.transition(task, TaskStatus.PROVISIONING)
        sm.transition(task, TaskStatus.RUNNING)
        sm.transition(task, TaskStatus.DONE, result={"answer": "..."})

    参数：
        emitter: 可选事件发射器；P2 阶段对接 Redis Pub/Sub + SSE 网关。
    """

    TRANSITIONS = TRANSITIONS

    def __init__(self, emitter: EventEmitter | None = None) -> None:
        self._emitter = emitter

    @classmethod
    def can_transition(
        cls, from_state: TaskStatus, to_state: TaskStatus
    ) -> bool:
        """判断 ``from_state -> to_state`` 是否合法。"""
        return to_state in cls.TRANSITIONS.get(from_state, frozenset())

    def transition(
        self,
        task: Task,
        to_state: TaskStatus,
        **context: Any,
    ) -> Task:
        """执行状态转移。

        - 合法性校验，否则抛出 ``InvalidTransitionError``。
        - 自动写入时间戳：进入 RUNNING 写 started_at；进入 DONE/FAILED 写 finished_at。
        - 将上下文（result / error / approval_payload 等）写入对应字段。
        - 通过 ``self._emitter`` 发出 ``TaskEvent``。

        说明：本方法只在内存中改 ORM 实例，**不**主动 commit；
        由 ``TaskOrchestratorService`` 控制事务边界。

        参数：
            task: ORM 实例
            to_state: 目标状态
            **context: 透传上下文（result / error / payload / sandbox_id ...）

        返回：
            更新后的 ``Task`` 实例（同传入对象）。
        """
        from_state = task.status
        if not self.can_transition(from_state, to_state):
            raise InvalidTransitionError(from_state, to_state)

        now = datetime.now(timezone.utc)
        task.status = to_state

        # 时间戳钩子
        if to_state == TaskStatus.RUNNING and task.started_at is None:
            task.started_at = now
        if to_state in (TaskStatus.DONE, TaskStatus.FAILED):
            task.finished_at = now

        # 上下文写入
        if "result" in context:
            task.result = context["result"]
        if "error" in context:
            task.error = context["error"]
        if "sandbox_id" in context:
            task.sandbox_id = context["sandbox_id"]

        # 事件发射
        if self._emitter is not None:
            event = TaskEvent(
                task_id=task.id,
                event_type=ENTER_EVENT.get(to_state, TaskEventType.PROGRESS),
                payload={
                    "from": from_state.value,
                    "to": to_state.value,
                    **{
                        k: v
                        for k, v in context.items()
                        if k in ("result", "error", "progress", "message")
                    },
                },
                timestamp=now,
            )
            self._emitter(event)

        return task
