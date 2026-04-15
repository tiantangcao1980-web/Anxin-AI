# -*- coding: utf-8 -*-
"""添加 AI 旁听会议记录表

Revision ID: 022_meeting_records
Revises: 021_email_verified
Create Date: 2026-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "022_meeting_records"
down_revision: Union[str, None] = "021_email_verified"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _uuid_col():
    """返回与现有 users/cases/contracts.id 一致的类型。
    PostgreSQL 下用 UUID，其他方言 fallback 到 CHAR(36)。"""
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        return UUID(as_uuid=False)
    return sa.CHAR(36)


def upgrade() -> None:
    op.create_table(
        "meeting_records",
        sa.Column("id", _uuid_col(), primary_key=True),
        sa.Column("conversation_id", sa.String(100), nullable=False, index=True),
        sa.Column("conversation_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="listening"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_by", _uuid_col(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=False),
        sa.Column("transcript_text", sa.Text, nullable=True),
        sa.Column("summary", JSON, nullable=True),
        sa.Column("insights", JSON, nullable=True),
        sa.Column("action_items", JSON, nullable=True),
        sa.Column("related_case_id", _uuid_col(), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("related_contract_id", _uuid_col(), sa.ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("meeting_records")
