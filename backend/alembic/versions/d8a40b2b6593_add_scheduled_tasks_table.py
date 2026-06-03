# -*- coding: utf-8 -*-
"""add scheduled_tasks table (D-1 定时任务管理后端)

Revision ID: d8a40b2b6593
Revises: 60527fdd4aec
Create Date: 2026-06-04

定时任务「管理」元数据表。契约对齐
mobile/src/lib/api/__mocks__/capabilities.mock.ts 的 ScheduledTask。

MVP：仅落库管理数据；cron 实际触发 / agent persona 真跑 = P-later。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "d8a40b2b6593"
down_revision: str | None = "60527fdd4aec"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scheduled_tasks",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("cron", sa.String(128), nullable=False),
        sa.Column(
            "cron_human",
            sa.String(128),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "agent_persona",
            sa.String(64),
            nullable=False,
            server_default="",
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "next_run_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_run_ok", sa.Boolean(), nullable=True),
        sa.Column(
            "config",
            JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "org_id",
            UUID(as_uuid=False),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_index("ix_scheduled_tasks_kind", "scheduled_tasks", ["kind"])
    op.create_index("ix_scheduled_tasks_status", "scheduled_tasks", ["status"])
    op.create_index("ix_scheduled_tasks_org_id", "scheduled_tasks", ["org_id"])
    op.create_index(
        "ix_scheduled_tasks_org_status",
        "scheduled_tasks",
        ["org_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_scheduled_tasks_org_status", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_org_id", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_status", table_name="scheduled_tasks")
    op.drop_index("ix_scheduled_tasks_kind", table_name="scheduled_tasks")
    op.drop_table("scheduled_tasks")
