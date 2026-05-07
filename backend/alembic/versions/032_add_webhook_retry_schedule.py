"""add webhook retry schedule fields

Revision ID: 032_webhook_retry_schedule
Revises: 031_contract_esign_flow_mapping
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "032_webhook_retry_schedule"
down_revision: str | None = "031_contract_esign_flow_mapping"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("webhook_received", sa.Column("last_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("webhook_received", sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_webhook_received_next_retry_at", "webhook_received", ["next_retry_at"])


def downgrade() -> None:
    op.drop_index("ix_webhook_received_next_retry_at", table_name="webhook_received")
    op.drop_column("webhook_received", "next_retry_at")
    op.drop_column("webhook_received", "last_retry_at")
