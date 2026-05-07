"""add refund idempotency key

Revision ID: 033_refund_idempotency_key
Revises: 032_webhook_retry_schedule
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "033_refund_idempotency_key"
down_revision: str | None = "032_webhook_retry_schedule"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("refunds", sa.Column("idempotency_key", sa.String(128), nullable=True))
    op.create_index("ix_refunds_idempotency_key", "refunds", ["idempotency_key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_refunds_idempotency_key", table_name="refunds")
    op.drop_column("refunds", "idempotency_key")
