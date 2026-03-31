# -*- coding: utf-8 -*-
"""conversations 表新增 is_starred / starred_at 字段，支持对话收藏功能

Revision ID: 022_conversation_star
Revises: 021_email_verified
Create Date: 2026-03-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "022_conversation_star"
down_revision: Union[str, None] = "021_email_verified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("conversations", sa.Column("is_starred", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("conversations", sa.Column("starred_at", sa.DateTime(), nullable=True))
    op.create_index("ix_conversations_is_starred", "conversations", ["is_starred"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_conversations_is_starred", table_name="conversations")
    op.drop_column("conversations", "starred_at")
    op.drop_column("conversations", "is_starred")
