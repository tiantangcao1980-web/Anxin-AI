"""add durable webhook received table

Revision ID: 030_webhook_received
Revises: 029_document_object_storage
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "030_webhook_received"
down_revision: str | None = "029_document_object_storage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "webhook_received",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), server_default="processing", nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scope", "idempotency_key", name="uq_webhook_received_scope_key"),
    )
    op.create_index("ix_webhook_received_status", "webhook_received", ["status"])
    op.create_index("ix_webhook_received_processed_at", "webhook_received", ["processed_at"])


def downgrade() -> None:
    op.drop_index("ix_webhook_received_processed_at", table_name="webhook_received")
    op.drop_index("ix_webhook_received_status", table_name="webhook_received")
    op.drop_table("webhook_received")
