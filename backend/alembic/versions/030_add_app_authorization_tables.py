# -*- coding: utf-8 -*-
"""add app_authorizations + app_tokens tables for P4-A OAuth framework

Revision ID: 030_app_authorization
Revises: 029_im_gateway
Create Date: 2026-04-26

P4-A 通用 OAuth 应用授权框架 — 创建两张表 + 索引：
    - ``app_authorizations`` : user × provider 的授权记录
    - ``app_tokens``         : Fernet 加密后的 access/refresh token

字段定义与 ``backend/src/services/app_authorization/models.py`` 完全对齐。
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID


# Alembic 元信息
revision = "030_app_authorization"
down_revision = "029_im_gateway"
branch_labels = None
depends_on = None


# 状态枚举值（与 services.app_authorization.models.AppAuthorizationStatus 同步）
APP_AUTHORIZATION_STATUS_VALUES = (
    "connected",
    "expired",
    "revoked",
    "error",
)


def _create_pg_enum(name: str, values: tuple[str, ...]) -> None:
    """幂等创建 PostgreSQL enum（已存在则跳过）。"""
    op.execute(
        "DO $$ BEGIN "
        f"CREATE TYPE {name} AS ENUM ("
        + ", ".join(f"'{v}'" for v in values)
        + "); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
    )


def upgrade() -> None:
    """创建 app_authorizations + app_tokens 表 + 索引 + enum。"""
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        _create_pg_enum("app_authorization_status", APP_AUTHORIZATION_STATUS_VALUES)

        status_col = sa.dialects.postgresql.ENUM(
            *APP_AUTHORIZATION_STATUS_VALUES,
            name="app_authorization_status",
            create_type=False,
        )
        json_type: sa.types.TypeEngine = JSONB
        uuid_type: sa.types.TypeEngine = UUID(as_uuid=False)
    else:
        # SQLite 等其他方言降级到 STRING + JSON（用于本地测试）
        status_col = sa.String(32)
        json_type = sa.JSON
        uuid_type = sa.String(36)

    # ----------------------------- app_authorizations -----------------------------
    op.create_table(
        "app_authorizations",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "user_id",
            uuid_type,
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column(
            "status",
            status_col,
            nullable=False,
            server_default="connected",
        ),
        sa.Column("scopes", json_type, nullable=True),
        sa.Column("connected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
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
        "ix_app_authorizations_user_provider_status",
        "app_authorizations",
        ["user_id", "provider_id", "status"],
    )
    op.create_index(
        "ix_app_authorizations_provider",
        "app_authorizations",
        ["provider_id"],
    )

    # ----------------------------- app_tokens -----------------------------
    op.create_table(
        "app_tokens",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column(
            "authorization_id",
            uuid_type,
            sa.ForeignKey("app_authorizations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("encrypted_access_token", sa.LargeBinary(), nullable=False),
        sa.Column("encrypted_refresh_token", sa.LargeBinary(), nullable=True),
        sa.Column(
            "token_type",
            sa.String(32),
            nullable=False,
            server_default="Bearer",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
        "ix_app_tokens_expires_at",
        "app_tokens",
        ["expires_at"],
    )


def downgrade() -> None:
    """回滚：drop 两表 + drop enum。"""
    op.drop_index("ix_app_tokens_expires_at", table_name="app_tokens")
    op.drop_table("app_tokens")

    op.drop_index(
        "ix_app_authorizations_provider",
        table_name="app_authorizations",
    )
    op.drop_index(
        "ix_app_authorizations_user_provider_status",
        table_name="app_authorizations",
    )
    op.drop_table("app_authorizations")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TYPE IF EXISTS app_authorization_status")
