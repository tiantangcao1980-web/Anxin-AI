"""add durable sync log

Revision ID: 038_sync_log
Revises: 037_contract_attachments
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from src.models.base import GUID

revision: str = "038_sync_log"
down_revision: str | None = "037_contract_attachments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sync_log",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("client_version", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "version", name="uq_sync_log_user_version"),
    )
    op.create_index("ix_sync_log_user_version", "sync_log", ["user_id", "version"])
    op.create_index("ix_sync_log_user_entity", "sync_log", ["user_id", "entity_type", "entity_id"])
    op.create_index("ix_sync_log_user_device", "sync_log", ["user_id", "device_id"])


def downgrade() -> None:
    op.drop_index("ix_sync_log_user_device", table_name="sync_log")
    op.drop_index("ix_sync_log_user_entity", table_name="sync_log")
    op.drop_index("ix_sync_log_user_version", table_name="sync_log")
    op.drop_table("sync_log")
