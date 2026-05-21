"""scope due diligence search cache by organization

Revision ID: 039_search_cache_org_scope
Revises: 038_sync_log
Create Date: 2026-05-06
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from src.models.base import GUID

revision: str = "039_search_cache_org_scope"
down_revision: str | None = "038_sync_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("search_cache", sa.Column("org_id", GUID(), nullable=True))
    op.create_foreign_key(
        "fk_search_cache_org_id_organizations",
        "search_cache",
        "organizations",
        ["org_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_search_cache_org_id", "search_cache", ["org_id"])
    op.create_index("ix_cache_org_key_source", "search_cache", ["org_id", "cache_key", "data_source"])
    op.create_index("ix_cache_org_company", "search_cache", ["org_id", "company_name"])


def downgrade() -> None:
    op.drop_index("ix_cache_org_company", table_name="search_cache")
    op.drop_index("ix_cache_org_key_source", table_name="search_cache")
    op.drop_index("ix_search_cache_org_id", table_name="search_cache")
    op.drop_constraint("fk_search_cache_org_id_organizations", "search_cache", type_="foreignkey")
    op.drop_column("search_cache", "org_id")
