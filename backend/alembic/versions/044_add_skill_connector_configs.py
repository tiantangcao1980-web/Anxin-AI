"""add skill connector credential configuration table

Revision ID: 044_skill_connector_configs
Revises: 043_add_remote_control_execution_state
Create Date: 2026-05-09
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "044_skill_connector_configs"
down_revision: str | None = "043_add_remote_control_execution_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "skill_connector_configs",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("skill_name", sa.String(length=160), nullable=False),
        sa.Column("connector_name", sa.String(length=120), nullable=False),
        sa.Column("connector_type", sa.String(length=60), nullable=False, server_default="http_api"),
        sa.Column("endpoint_url", sa.String(length=500), nullable=True),
        sa.Column("auth_type", sa.String(length=40), nullable=False, server_default="api_key"),
        sa.Column("encrypted_fields", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(length=160), nullable=True),
        sa.Column("updated_by", sa.String(length=160), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_skill_connector_configs_org_id"),
        sa.UniqueConstraint(
            "org_id",
            "skill_name",
            "connector_name",
            name="uq_skill_connector_configs_org_skill_connector",
        ),
    )
    op.create_index(
        "ix_skill_connector_configs_org_skill",
        "skill_connector_configs",
        ["org_id", "skill_name"],
    )
    op.create_index(
        "ix_skill_connector_configs_org_enabled",
        "skill_connector_configs",
        ["org_id", "is_enabled"],
    )


def downgrade() -> None:
    op.drop_index("ix_skill_connector_configs_org_enabled", table_name="skill_connector_configs")
    op.drop_index("ix_skill_connector_configs_org_skill", table_name="skill_connector_configs")
    op.drop_table("skill_connector_configs")
