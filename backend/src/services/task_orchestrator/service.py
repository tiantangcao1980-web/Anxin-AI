# -*- coding: utf-8 -*-
"""
TaskOrchestratorService —— 任务编排服务门面

封装"创建/入队/启动/进度/完成/失败/审批/查询"等高层操作；
内部调用 ``TaskStateMachine`` 完成状态变更，并通过 SQLAlchemy AsyncSession 持久化。

所有方法在 P1 阶段仅提供骨架（``raise NotImplementedError("P2 实现")``）。
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.services.task_orchestrator.models import Task, TaskStatus
from src.services.task_orchestrator.state_machine import TaskStateMachine


class TaskOrchestratorService:
    """异步任务编排服务（P2 实现）。

    依赖：
        session: SQLAlchemy AsyncSession
        state_machine: 可选注入；默认使用全新 ``TaskStateMachine()``

    P2 实现要点：
        - ``enqueue`` 与队列后端（Redis Stream / Celery / 自建 worker）对接
        - ``start`` 申请 sandbox（Codex Cloud / 自建 runner）
        - ``progress`` 写细粒度进度事件（不改主状态）
        - ``request_approval`` 落地审批流（结合 models/approval.py）
    """

    def __init__(
        self,
        session: AsyncSession,
        state_machine: TaskStateMachine | None = None,
    ) -> None:
        self.session = session
        self.state_machine = state_machine or TaskStateMachine()

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
        """创建任务并落库（初始状态 QUEUED）。

        参数：
            user_id: 派发人用户 ID
            agent_persona: agent 角色
            payload: 任务参数
            priority: 优先级（默认 100）
            parent_task_id: 父任务 ID（链式调用）

        返回：
            新建的 ``Task`` ORM 实例（已 flush，含 id）。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    async def enqueue(self, task: Task) -> None:
        """将任务推入执行队列（不改主状态，仍然是 QUEUED）。

        P2 实现：发布到 Redis Stream / NATS / Celery，由 worker 消费。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    # ------------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------------
    async def start(self, task: Task, *, sandbox_id: str | None = None) -> Task:
        """worker 取到任务后调用：QUEUED → PROVISIONING → RUNNING。

        参数：
            task: 任务实例
            sandbox_id: 远端 sandbox 标识

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    async def progress(
        self,
        task: Task,
        *,
        progress: float | None = None,
        message: str | None = None,
    ) -> None:
        """上报中间进度（不改 status，发 ``PROGRESS`` 事件）。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    async def complete(self, task: Task, *, result: dict[str, Any]) -> Task:
        """RUNNING → REPORTING → DONE，并写入 result。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    async def fail(
        self,
        task: Task,
        *,
        error: dict[str, Any],
    ) -> Task:
        """任意非终态 → FAILED，并写入 error。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    async def request_approval(
        self,
        task: Task,
        *,
        approval_payload: dict[str, Any],
    ) -> Task:
        """RUNNING → NEEDS_APPROVAL，落地一条审批记录。

        P2 实现：与 models/approval.py 联动，给指派人发通知。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------
    async def get_task(self, task_id: str) -> Task | None:
        """按 ID 查询任务（含 result/error）。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")

    async def list_tasks_for_user(
        self,
        user_id: str,
        *,
        status: TaskStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Task]:
        """分页列出某用户的任务。

        阶段：P2。
        """
        raise NotImplementedError("P2 实现")
