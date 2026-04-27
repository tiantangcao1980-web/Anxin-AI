# -*- coding: utf-8 -*-
"""add im_gateway tables for P3 IM pairing flow

Revision ID: 029_im_gateway
Revises: 028_agent_tasks
Create Date: 2026-04-26

P3-B 配对授权 24h 窗口 — 创建三张 ``im_gateway_*`` 表：
    - ``im_gateway_channels``  : IM 通道
    - ``im_gateway_bindings``  : 平台用户 ↔ 内部用户绑定
    - ``im_gateway_pairings``  : 24h 配对授权请求

字段定义与 ``backend/src/services/im_gateway/models.py`` 完全对齐；
独立前缀 ``im_gateway_*`` 避免与既有 ``im_conversations``（014）冲突。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


# Alembic 元信息
revision = "029_im_gateway"
down_revision = "028_agent_tasks"
branch_labels = None
depends_on = None


# 枚举值（与 services.im_gateway.models 同步）
IM_CHANNEL_TYPE_VALUES = (
    "feishu",
    "wechat",
    "dingtalk",
    "telegram",
    "slack",
    "discord",
)

PAIRING_STATUS_VALUES = (
    "pending",
    "approved",
    "rejected",
    "expired",
)


def _create_pg_enum(bind, name: str, values: tuple[str, ...]) -> None:
    """幂等创建 PostgreSQL enum（已存在则跳过）。"""
    op.execute(
        "DO $$ BEGIN "
        f"CREATE TYPE {name} AS ENUM ("
        + ", ".join(f"'{v}'" for v in values)
        + "); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )


def upgrade() -> None:
    """创建 im_gateway 三表 + 索引 + enum。"""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # 1. PostgreSQL 上手动建 enum，避免 autogenerate 二次创建
    if dialect == "postgresql":
        _create_pg_enum(bind, "im_gateway_channel_type", IM_CHANNEL_TYPE_VALUES)
        _create_pg_enum(bind, "im_gateway_pairing_status", PAIRING_STATUS_VALUES)

        channel_type_col = sa.dialects.postgresql.ENUM(
            *IM_CHANNEL_TYPE_VALUES,
            name="im_gateway_channel_type",
            create_type=False,
        )
        pairing_status_col = sa.dialects.postgresql.ENUM(
            *PAIRING_STATUS_VALUES,
            name="im_gateway_pairing_status",
            create_type=False,
        )
        json_type: sa.types.TypeEngine = JSONB
        uuid_type: sa.types.TypeEngine = UUID(as_uuid=False)
    else:
        # SQLite 等其他方言降级到 STRING + JSON（用于本地测试）
        channel_type_col = sa.String(32)
        pairing_status_col = sa.String(32)
        json_type = sa.JSON
        uuid_type = sa.String(36)

    # ----------------------------- im_gateway_channels -----------------------------
    op.create_table(
        "im_gateway_channels",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("channel_type", channel_type_col, nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("config", json_type, nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true") if dialect == "postgresql" else sa.text("1"),
        ),
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
    op.create_index(
        "ix_im_gateway_channels_type",
        "im_gateway_channels",
        ["channel_type"],
    )
    op.create_index(
        "ix_im_gateway_channels_enabled",
        "im_gateway_channels",
        ["enabled"],
    )

    # ----------------------------- im_gateway_bindings -----------------------------
    op.create_table(
        "im_gateway_bindings",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "channel_id",
            uuid_type,
            sa.ForeignKey("im_gateway_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_user_id", sa.String(128), nullable=False),
        sa.Column(
            "internal_user_id",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bound_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.UniqueConstraint(
            "channel_id",
            "external_user_id",
            name="uq_im_gateway_binding_channel_extuser",
        ),
    )
    op.create_index(
        "ix_im_gateway_bindings_internal_user",
        "im_gateway_bindings",
        ["internal_user_id"],
    )

    # ----------------------------- im_gateway_pairings -----------------------------
    op.create_table(
        "im_gateway_pairings",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "channel_id",
            uuid_type,
            sa.ForeignKey("im_gateway_channels.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_user_id", sa.String(128), nullable=False),
        sa.Column(
            "status",
            pairing_status_col,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index(
        "ix_im_gateway_pairings_channel_ext",
        "im_gateway_pairings",
        ["channel_id", "external_user_id"],
    )
    op.create_index(
        "ix_im_gateway_pairings_status",
        "im_gateway_pairings",
        ["status"],
    )
    op.create_index(
        "ix_im_gateway_pairings_expires_at",
        "im_gateway_pairings",
        ["expires_at"],
    )
    # 任务要求的复合索引：(channel_id, status, expires_at) — 加速 cleanup_expired
    op.create_index(
        "ix_im_gateway_pairings_channel_status_expires",
        "im_gateway_pairings",
        ["channel_id", "status", "expires_at"],
    )


def downgrade() -> None:
    """回滚：drop 三表 + drop enum。"""
    op.drop_index(
        "ix_im_gateway_pairings_channel_status_expires",
        table_name="im_gateway_pairings",
    )
    op.drop_index("ix_im_gateway_pairings_expires_at", table_name="im_gateway_pairings")
    op.drop_index("ix_im_gateway_pairings_status", table_name="im_gateway_pairings")
    op.drop_index("ix_im_gateway_pairings_channel_ext", table_name="im_gateway_pairings")
    op.drop_table("im_gateway_pairings")

    op.drop_index(
        "ix_im_gateway_bindings_internal_user",
        table_name="im_gateway_bindings",
    )
    op.drop_table("im_gateway_bindings")

    op.drop_index("ix_im_gateway_channels_enabled", table_name="im_gateway_channels")
    op.drop_index("ix_im_gateway_channels_type", table_name="im_gateway_channels")
    op.drop_table("im_gateway_channels")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS im_gateway_pairing_status")
        op.execute("DROP TYPE IF EXISTS im_gateway_channel_type")
