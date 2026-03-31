# -*- coding: utf-8 -*-
"""添加 email_verified 字段到 users 表

Revision ID: 021_email_verified
Revises: 020_document_snapshots
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "021_email_verified"
down_revision: Union[str, None] = "020_document_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    # 将已有的种子管理员账号标记为已验证
    op.execute("UPDATE users SET email_verified = true WHERE role IN ('super_admin', 'admin')")


def downgrade() -> None:
    op.drop_column("users", "email_verified")
