# -*- coding: utf-8 -*-
"""merge 3 heads (enterprise_directory + governance + im_channel)

合并三个发散 head：045_enterprise_directory / 045_governance_tables /
048_im_channel_mgmt，消除 multiple heads，使 ``alembic upgrade head`` 可达单一 head。
本 merge revision 不含 schema 变更（空 upgrade/downgrade）。

Revision ID: 60527fdd4aec
Revises: 045_enterprise_directory, 045_governance_tables, 048_im_channel_mgmt
Create Date: 2026-06-04 02:48:47.553054
"""

from collections.abc import Sequence

revision: str = "60527fdd4aec"
down_revision: tuple[str, ...] | None = (
    "045_enterprise_directory",
    "045_governance_tables",
    "048_im_channel_mgmt",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
