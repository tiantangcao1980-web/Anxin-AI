# -*- coding: utf-8 -*-
"""修复 ai_assistant_feedbacks.conversation_id 类型：String(36) → UUID + ForeignKey

Revision ID: 025_fix_feedback_conversation_fk
Revises: 024_user_ai_profile
Create Date: 2026-04-02

"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "025_fix_feedback_conversation_fk"
down_revision: Union[str, None] = "024_user_ai_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 先删除旧索引，避免 USING CAST 冲突
    op.drop_index(
        "ix_ai_assistant_feedbacks_conversation_id",
        table_name="ai_assistant_feedbacks",
    )
    # 将 conversation_id 列从 varchar(36) 改为 UUID，同时清除无效值
    op.execute(
        """
        ALTER TABLE ai_assistant_feedbacks
            ALTER COLUMN conversation_id TYPE UUID
                USING CASE
                    WHEN conversation_id ~ '^[0-9a-fA-F-]{36}$'
                    THEN conversation_id::uuid
                    ELSE NULL
                END
        """
    )
    # 添加外键约束
    op.create_foreign_key(
        "fk_feedbacks_conversation_id",
        "ai_assistant_feedbacks",
        "conversations",
        ["conversation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # 重建索引
    op.create_index(
        "ix_ai_assistant_feedbacks_conversation_id",
        "ai_assistant_feedbacks",
        ["conversation_id"],
    )

    # 修复 message_id 列：String(36) → UUID（无外键，仅类型统一）
    op.execute(
        """
        ALTER TABLE ai_assistant_feedbacks
            ALTER COLUMN message_id TYPE UUID
                USING CASE
                    WHEN message_id ~ '^[0-9a-fA-F-]{36}$'
                    THEN message_id::uuid
                    ELSE NULL
                END
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_feedbacks_conversation_id",
        "ai_assistant_feedbacks",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_ai_assistant_feedbacks_conversation_id",
        table_name="ai_assistant_feedbacks",
    )
    op.alter_column(
        "ai_assistant_feedbacks",
        "conversation_id",
        type_=sa.String(36),
        existing_type=sa.dialects.postgresql.UUID(as_uuid=False),
    )
    op.alter_column(
        "ai_assistant_feedbacks",
        "message_id",
        type_=sa.String(36),
        existing_type=sa.dialects.postgresql.UUID(as_uuid=False),
    )
    op.create_index(
        "ix_ai_assistant_feedbacks_conversation_id",
        "ai_assistant_feedbacks",
        ["conversation_id"],
    )
