"""add contract version snapshots

Revision ID: 036_contract_versions
Revises: 035_im_message_sequence
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from src.models.base import GUID

revision: str = "036_contract_versions"
down_revision: str | None = "035_im_message_sequence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contracts",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_table(
        "contract_versions",
        # [S8 fix] 用 GUID()（PG: UUID / 其它: CHAR(36)）匹配 contracts.id 类型，
        # 避免 PG 中外键类型冲突 (DatatypeMismatchError)
        sa.Column("id", GUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("contract_id", GUID(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="manual"),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_by", GUID(), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_id", "version", name="uq_contract_versions_contract_version"),
    )
    op.create_index("ix_contract_versions_contract_id", "contract_versions", ["contract_id"])


def downgrade() -> None:
    op.drop_index("ix_contract_versions_contract_id", table_name="contract_versions")
    op.drop_table("contract_versions")
    op.drop_column("contracts", "version")
