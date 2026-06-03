# -*- coding: utf-8 -*-
"""add im_gateway_channels management columns (status / bound_agent_persona / org)

Revision ID: 048_im_channel_mgmt
Revises: 047_user_token_usage
Create Date: 2026-06-03 (P3-C: IM 渠道配置管理后端)

为已有 ``im_gateway_channels`` 表（029 创建）补充渠道管理所需列：
  - status               连接状态枚举（依据 config 完整度推导，非真实握手）
  - bound_agent_persona  绑定的 agent persona key
  - org_id               所属组织（按组织隔离）
  - created_by           创建者用户 ID

dev 环境靠 init_db / Base.metadata.create_all 直接建全表，本迁移用于生产增量升级。
枚举类型在 PostgreSQL 下需显式 CREATE TYPE；SQLite 不支持 ALTER 加约束，故 status
列用普通字符串落库（与 ValueEnum values_callable 行为一致）。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "048_im_channel_mgmt"
down_revision: str | None = "047_user_token_usage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_CHANNEL_STATUS_ENUM = sa.Enum(
    "unconfigured",
    "connecting",
    "connected",
    "error",
    name="im_gateway_channel_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    if is_pg:
        # PostgreSQL 需先创建枚举类型
        _CHANNEL_STATUS_ENUM.create(bind, checkfirst=True)
        status_type: sa.types.TypeEngine = _CHANNEL_STATUS_ENUM
    else:
        # SQLite 等：用普通字符串列，避免 ALTER 加 CHECK 约束的兼容问题
        status_type = sa.String(length=20)

    op.add_column(
        "im_gateway_channels",
        sa.Column(
            "status",
            status_type,
            nullable=False,
            server_default="unconfigured",
        ),
    )
    op.add_column(
        "im_gateway_channels",
        sa.Column("bound_agent_persona", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "im_gateway_channels",
        sa.Column("org_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "im_gateway_channels",
        sa.Column("created_by", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_im_gateway_channels_org_id",
        "im_gateway_channels",
        ["org_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    op.drop_index("ix_im_gateway_channels_org_id", table_name="im_gateway_channels")
    op.drop_column("im_gateway_channels", "created_by")
    op.drop_column("im_gateway_channels", "org_id")
    op.drop_column("im_gateway_channels", "bound_agent_persona")
    op.drop_column("im_gateway_channels", "status")

    if is_pg:
        _CHANNEL_STATUS_ENUM.drop(bind, checkfirst=True)
