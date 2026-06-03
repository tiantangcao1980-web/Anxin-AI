# -*- coding: utf-8 -*-
"""add plugins table (D-2 插件注册后端)

Revision ID: a3f1c9d27b84
Revises: d8a40b2b6593
Create Date: 2026-06-04

插件注册表（registry：source='official' / 'private'）。契约对齐
mobile/src/lib/api/__mocks__/capabilities.mock.ts 的 Plugin。

source='mcp' 来源插件不入本表：由 McpServerConfig（mcp_server_configs）
投影，见 services/plugin_service.py 与 models/plugin.py。

MVP：仅落库管理数据；pending_review 审核工作流 / 插件实际运行 = P-later。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "a3f1c9d27b84"
down_revision: str | None = "d8a40b2b6593"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "plugins",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column(
            "display_name",
            sa.String(255),
            nullable=False,
            server_default="",
        ),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="disabled",
        ),
        sa.Column(
            "description",
            sa.String(1024),
            nullable=False,
            server_default="",
        ),
        sa.Column(
            "publisher",
            sa.String(255),
            nullable=False,
            server_default="",
        ),
        sa.Column("icon", sa.String(512), nullable=True),
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
        sa.UniqueConstraint("org_id", "name", name="uq_plugins_org_name"),
    )

    op.create_index("ix_plugins_source", "plugins", ["source"])
    op.create_index("ix_plugins_status", "plugins", ["status"])
    op.create_index("ix_plugins_org_id", "plugins", ["org_id"])
    op.create_index("ix_plugins_org_source", "plugins", ["org_id", "source"])


def downgrade() -> None:
    op.drop_index("ix_plugins_org_source", table_name="plugins")
    op.drop_index("ix_plugins_org_id", table_name="plugins")
    op.drop_index("ix_plugins_status", table_name="plugins")
    op.drop_index("ix_plugins_source", table_name="plugins")
    op.drop_table("plugins")
