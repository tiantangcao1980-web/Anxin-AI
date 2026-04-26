# -*- coding: utf-8 -*-
"""add agent_tasks table for task_orchestrator

Revision ID: 028_agent_tasks
Revises: 027_experience_patterns
Create Date: 2026-04-26

P2 异步任务 MVP — 创建 agent_tasks 表 + 索引。
与现有 tasks 表（用户/案件待办）解耦，专属 agent 远端执行任务。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


# Alembic 元信息
revision = "028_agent_tasks"
down_revision = "027_experience_patterns"
branch_labels = None
depends_on = None


# 状态枚举（与 services.task_orchestrator.models.TaskStatus 同步）
AGENT_TASK_STATUS_VALUES = (
    "queued",
    "provisioning",
    "running",
    "reporting",
    "done",
    "failed",
    "needs_approval",
    "cancelled",
)


def upgrade() -> None:
    """创建 agent_tasks 表 + 索引 + enum 类型。"""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1. PostgreSQL 上手动建 enum，避免 autogenerate 二次创建
    if dialect == "postgresql":
        op.execute(
            "DO $$ BEGIN "
            "CREATE TYPE agent_task_status AS ENUM ("
            + ", ".join(f"'{v}'" for v in AGENT_TASK_STATUS_VALUES)
            + "); "
            "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        )
        status_type: sa.types.TypeEngine = sa.dialects.postgresql.ENUM(
            *AGENT_TASK_STATUS_VALUES,
            name="agent_task_status",
            create_type=False,
        )
        json_type: sa.types.TypeEngine = JSONB
        uuid_type: sa.types.TypeEngine = UUID(as_uuid=False)
    else:
        # SQLite 等其他方言降级到原生 STRING + JSON（用于本地测试）
        status_type = sa.String(32)
        json_type = sa.JSON
        uuid_type = sa.String(36)

    op.create_table(
        "agent_tasks",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("agent_persona", sa.String(64), nullable=False),
        sa.Column(
            "status",
            status_type,
            nullable=False,
            server_default="queued",
        ),
        sa.Column(
            "priority",
            sa.Integer(),
            nullable=False,
            server_default="100",
        ),
        sa.Column("payload", json_type, nullable=True),
        sa.Column("result", json_type, nullable=True),
        sa.Column("error", json_type, nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "parent_task_id",
            uuid_type,
            sa.ForeignKey("agent_tasks.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sandbox_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 2. 索引（与 models.py __table_args__ 对齐 + 任务要求 (user_id, status, created_at)）
    op.create_index(
        "ix_agent_tasks_user_status",
        "agent_tasks",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_agent_tasks_status_priority",
        "agent_tasks",
        ["status", "priority"],
    )
    op.create_index(
        "ix_agent_tasks_parent_task_id",
        "agent_tasks",
        ["parent_task_id"],
    )
    op.create_index(
        "ix_agent_tasks_user_status_created",
        "agent_tasks",
        ["user_id", "status", "created_at"],
    )


def downgrade() -> None:
    """回滚：删表 + 删 enum。"""
    op.drop_index("ix_agent_tasks_user_status_created", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_parent_task_id", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_status_priority", table_name="agent_tasks")
    op.drop_index("ix_agent_tasks_user_status", table_name="agent_tasks")
    op.drop_table("agent_tasks")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS agent_task_status")
