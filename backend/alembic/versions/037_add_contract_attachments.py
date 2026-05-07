"""add contract attachment object storage records

Revision ID: 037_contract_attachments
Revises: 036_contract_versions
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "037_contract_attachments"
down_revision: str | None = "036_contract_versions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "contract_attachments",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("contract_id", sa.CHAR(length=36), nullable=False),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("storage_backend", sa.String(length=16), nullable=False),
        sa.Column("object_key", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by", sa.CHAR(length=36), nullable=True),
        sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_key", name="uq_contract_attachments_object_key"),
    )
    op.create_index("ix_contract_attachments_contract_id", "contract_attachments", ["contract_id"])
    op.create_index("ix_contract_attachments_org_id", "contract_attachments", ["org_id"])


def downgrade() -> None:
    op.drop_index("ix_contract_attachments_org_id", table_name="contract_attachments")
    op.drop_index("ix_contract_attachments_contract_id", table_name="contract_attachments")
    op.drop_table("contract_attachments")
