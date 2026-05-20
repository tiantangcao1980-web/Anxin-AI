# -*- coding: utf-8 -*-
"""add user_token_usage table for cost_tracker persistence

Revision ID: 047_user_token_usage
Revises: 046_add_incidents_table
Create Date: 2026-05-14 (A4: cost_tracker 持久化 + cron 重置)

cost_tracker 当前是进程内内存累计, 重启即丢. 本表记录:
  - 每个 (user_id, period_start, period_end) 的累计 tokens / cost / call_count
  - 每次计费周期结束时 archive + 清零, 下个周期重新累计
  - 应用启动时 restore 当前周期, 避免重启丢配额
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op


revision: str = "047_user_token_usage"
down_revision: str | None = "046_add_incidents_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_token_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=False, server_default="0"),
        sa.Column("call_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("archived", sa.Boolean, nullable=False, server_default=sa.false()),
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
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    # 一个 user 在同一周期内只有一条 active 记录 (archived=False)
    op.create_index(
        "ix_user_token_usage_user_period",
        "user_token_usage",
        ["user_id", "period_start", "period_end"],
        unique=False,
    )
    # 配合启动 restore 查询
    op.create_index(
        "ix_user_token_usage_archived",
        "user_token_usage",
        ["archived"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_token_usage_archived", table_name="user_token_usage")
    op.drop_index("ix_user_token_usage_user_period", table_name="user_token_usage")
    op.drop_table("user_token_usage")
