# -*- coding: utf-8 -*-
"""users 表新增 ai_profile JSON 字段，支持用户画像持久化

Revision ID: 024_user_ai_profile
Revises: 023_conversation_star
Create Date: 2026-04-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "024_user_ai_profile"
down_revision: Union[str, None] = "023_conversation_star"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 用户 AI 画像：法律专业度、常用场景、追问耐心度、默认上下文等
    op.add_column(
        "users",
        sa.Column("ai_profile", JSONB, nullable=True, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("users", "ai_profile")
