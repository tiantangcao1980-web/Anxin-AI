"""add contract e-sign flow mapping

Revision ID: 031_contract_esign_flow_mapping
Revises: 030_webhook_received
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "031_contract_esign_flow_mapping"
down_revision: str | None = "030_webhook_received"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("contracts", sa.Column("esign_flow_id", sa.String(128), nullable=True))
    op.add_column("contracts", sa.Column("esign_provider", sa.String(50), nullable=True))
    op.create_index("ix_contracts_esign_flow_id", "contracts", ["esign_flow_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_contracts_esign_flow_id", table_name="contracts")
    op.drop_column("contracts", "esign_provider")
    op.drop_column("contracts", "esign_flow_id")
