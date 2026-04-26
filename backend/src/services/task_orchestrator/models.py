# -*- coding: utf-8 -*-
"""
异步任务 ORM 模型

为避免与历史 ``tasks`` 表冲突，本模块使用独立的 ``agent_tasks`` 表，
专门存储由 task_orchestrator 调度的远端 agent 异步任务。

字段语义：
    id              : UUID，主键
    user_id         : 派发人（FK -> users.id）
    agent_persona   : agent 角色（free_legal / pro_legal / contract_review ...）
    status          : 任务状态（见 ``TaskStatus``）
    priority        : 优先级，数值越小越先执行（默认 100）
    payload         : 派发参数（请求快照）
    result          : 成功结果
    error           : 失败/异常信息
    parent_task_id  : 父任务 ID（子任务 / 链式任务）
    sandbox_id      : 远端执行 sandbox 标识（Codex Cloud / 自建 runner）
    started_at      : 开始执行时间
    finished_at     : 结束时间（done / failed 都会写入）
    created_at/updated_at: 由 ``TimestampMixin`` 注入

说明：
- 不在此处生成 alembic 迁移，由人工 ``alembic revision --autogenerate`` 后审阅。
- 状态变更只允许通过 ``TaskStateMachine`` 完成，避免脏写。
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
# 与项目其它 model 一致：以 JSON 为基础类型，并在 PostgreSQL 上自动 variant 到 JSONB。
# 这样在 SQLite 测试库上可以正常 CREATE TABLE，在生产 PG 上仍享受 JSONB 索引能力。
from sqlalchemy import JSON as _JSON
from sqlalchemy.dialects.postgresql import JSONB as _PGJSONB

JSONB = _JSON().with_variant(_PGJSONB(), "postgresql")
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base, TimestampMixin, ValueEnum


class TaskStatus(str, enum.Enum):
    """异步任务状态机枚举。

    合法转移见 ``state_machine.TaskStateMachine.TRANSITIONS``。
    """

    QUEUED = "queued"
    PROVISIONING = "provisioning"
    RUNNING = "running"
    REPORTING = "reporting"
    DONE = "done"
    FAILED = "failed"
    NEEDS_APPROVAL = "needs_approval"
    CANCELLED = "cancelled"


class Task(Base, TimestampMixin):
    """异步任务 ORM 模型 —— 表 ``agent_tasks``。

    与现有 ``models/task.py`` 中的 ``Task`` (表 ``tasks``) 互不影响：
    后者是用户/案件层面的待办事项；本模型专属 agent 远端执行任务。
    """

    __tablename__ = "agent_tasks"

    user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="派发人用户 ID",
    )
    agent_persona: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="agent 角色（free_legal/pro_legal/contract_review/...）",
    )
    status: Mapped[TaskStatus] = mapped_column(
        ValueEnum(TaskStatus, name="agent_task_status"),
        nullable=False,
        default=TaskStatus.QUEUED,
        comment="任务状态",
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
        comment="优先级（数字越小越先执行）",
    )
    payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="派发参数 / 请求快照",
    )
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="任务成功结果",
    )
    error: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="任务失败信息（code/message/stack/...）",
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="进入 running 时间",
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="进入 done/failed 时间",
    )

    parent_task_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("agent_tasks.id", ondelete="SET NULL"),
        nullable=True,
        comment="父任务 ID（链式/子任务）",
    )
    sandbox_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="远端执行 sandbox 标识",
    )

    __table_args__ = (
        Index("ix_agent_tasks_user_status", "user_id", "status"),
        Index("ix_agent_tasks_status_priority", "status", "priority"),
        Index("ix_agent_tasks_parent_task_id", "parent_task_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return (
            f"<Task id={self.id} status={self.status.value} "
            f"persona={self.agent_persona} prio={self.priority}>"
        )
