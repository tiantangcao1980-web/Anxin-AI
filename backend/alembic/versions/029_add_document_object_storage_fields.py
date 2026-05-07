"""add document object storage metadata

Revision ID: 029_document_object_storage
Revises: 028_password_reset_tokens
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "029_document_object_storage"
down_revision: str | None = "028_password_reset_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("storage_backend", sa.String(16), nullable=True))
    op.add_column("documents", sa.Column("object_key", sa.String(1024), nullable=True))
    op.create_index("ix_documents_object_key", "documents", ["object_key"])

    op.add_column("document_versions", sa.Column("storage_backend", sa.String(16), nullable=True))
    op.add_column("document_versions", sa.Column("object_key", sa.String(1024), nullable=True))
    op.create_index("ix_document_versions_object_key", "document_versions", ["object_key"])

    op.execute(
        sa.text(
            """
            UPDATE documents
            SET
                storage_backend = COALESCE(storage_backend, 'local'),
                object_key = COALESCE(object_key, file_path)
            WHERE file_path IS NOT NULL
              AND file_path != ''
              AND (storage_backend IS NULL OR object_key IS NULL)
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE document_versions
            SET
                storage_backend = COALESCE(storage_backend, 'local'),
                object_key = COALESCE(object_key, file_path)
            WHERE file_path IS NOT NULL
              AND file_path != ''
              AND (storage_backend IS NULL OR object_key IS NULL)
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_document_versions_object_key", table_name="document_versions")
    op.drop_column("document_versions", "object_key")
    op.drop_column("document_versions", "storage_backend")

    op.drop_index("ix_documents_object_key", table_name="documents")
    op.drop_column("documents", "object_key")
    op.drop_column("documents", "storage_backend")
