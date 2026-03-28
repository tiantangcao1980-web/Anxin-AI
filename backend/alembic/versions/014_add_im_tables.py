# -*- coding: utf-8 -*-
"""添加 IM 即时通讯表

Revision ID: 014_im_tables
Revises: 013_feature_flags
Create Date: 2026-03-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID

# revision identifiers, used by Alembic.
revision = "014_im_tables"
down_revision = "013_feature_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ===== im_conversations =====
    op.create_table(
        "im_conversations",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column("type", sa.String(20), nullable=False, comment="对话类型: private|group|case|contract"),
        sa.Column("title", sa.String(200), nullable=True, comment="对话标题"),
        sa.Column("avatar_url", sa.String(500), nullable=True, comment="对话头像 URL"),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("metadata_", sa.JSON, nullable=True, comment="额外元数据"),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_preview", sa.String(200), nullable=True),
        sa.Column(
            "case_id",
            sa.CHAR(36),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "contract_id",
            sa.CHAR(36),
            sa.ForeignKey("contracts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_im_conversations_type", "im_conversations", ["type"])
    op.create_index("ix_im_conversations_last_message_at", "im_conversations", ["last_message_at"])
    op.create_index("ix_im_conversations_case_id", "im_conversations", ["case_id"])
    op.create_index("ix_im_conversations_contract_id", "im_conversations", ["contract_id"])

    # ===== im_participants =====
    op.create_table(
        "im_participants",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.CHAR(36),
            sa.ForeignKey("im_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), server_default="member", nullable=False),
        sa.Column("nickname", sa.String(100), nullable=True),
        sa.Column("is_muted", sa.Boolean, server_default="false", nullable=False),
        sa.Column("unread_count", sa.Integer, server_default="0", nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_im_participants_conversation_id", "im_participants", ["conversation_id"])
    op.create_index("ix_im_participants_user_id", "im_participants", ["user_id"])
    op.create_index(
        "uq_im_participants_conv_user",
        "im_participants",
        ["conversation_id", "user_id"],
        unique=True,
    )

    # ===== im_messages =====
    op.create_table(
        "im_messages",
        sa.Column("id", sa.CHAR(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.CHAR(36),
            sa.ForeignKey("im_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sender_id",
            sa.CHAR(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("message_type", sa.String(20), server_default="text", nullable=False),
        sa.Column(
            "reply_to_id",
            sa.CHAR(36),
            sa.ForeignKey("im_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata_", sa.JSON, nullable=True),
        sa.Column("is_recalled", sa.Boolean, server_default="false", nullable=False),
        sa.Column("read_by", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_im_messages_conversation_id", "im_messages", ["conversation_id"])
    op.create_index("ix_im_messages_sender_id", "im_messages", ["sender_id"])
    op.create_index("ix_im_messages_created_at", "im_messages", ["created_at"])
    op.create_index(
        "ix_im_messages_conv_created",
        "im_messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("im_messages")
    op.drop_table("im_participants")
    op.drop_table("im_conversations")
