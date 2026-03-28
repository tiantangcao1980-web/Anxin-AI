# -*- coding: utf-8 -*-
"""
IM 即时通讯数据模型

包含对话、参与者、消息三个核心表。
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, GUID, TimestampMixin


class IMConversation(Base, TimestampMixin):
    """IM 对话/会话"""

    __tablename__ = "im_conversations"

    type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="对话类型: private|group|case|contract"
    )
    title: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="对话标题（群聊/业务关联名称）"
    )
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="对话头像 URL"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", comment="是否激活"
    )
    metadata_: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="额外元数据"
    )
    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后消息时间"
    )
    last_message_preview: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="最后消息预览文本"
    )

    # 可选关联
    case_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联案件 ID",
    )
    contract_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("contracts.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联合同 ID",
    )

    # 关系
    participants: Mapped[list["IMParticipant"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="selectin"
    )
    messages: Mapped[list["IMMessage"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", lazy="noload"
    )

    __table_args__ = (
        Index("ix_im_conversations_type", "type"),
        Index("ix_im_conversations_last_message_at", "last_message_at"),
        Index("ix_im_conversations_case_id", "case_id"),
        Index("ix_im_conversations_contract_id", "contract_id"),
    )


class IMParticipant(Base, TimestampMixin):
    """IM 对话参与者"""

    __tablename__ = "im_participants"

    conversation_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("im_conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="对话 ID",
    )
    user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="用户 ID",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="member",
        server_default="member",
        comment="角色: owner|admin|member",
    )
    nickname: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="群内昵称"
    )
    is_muted: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", comment="是否免打扰"
    )
    unread_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", comment="未读消息数"
    )
    last_read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最后已读时间"
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="加入时间",
    )

    # 关系
    conversation: Mapped["IMConversation"] = relationship(back_populates="participants")

    __table_args__ = (
        Index("ix_im_participants_conversation_id", "conversation_id"),
        Index("ix_im_participants_user_id", "user_id"),
        Index(
            "uq_im_participants_conv_user",
            "conversation_id",
            "user_id",
            unique=True,
        ),
    )


class IMMessage(Base, TimestampMixin):
    """IM 消息"""

    __tablename__ = "im_messages"

    conversation_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("im_conversations.id", ondelete="CASCADE"),
        nullable=False,
        comment="对话 ID",
    )
    sender_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="发送者 ID",
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="消息内容"
    )
    message_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        server_default="text",
        comment="消息类型: text|image|file|system|card",
    )
    reply_to_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("im_messages.id", ondelete="SET NULL"),
        nullable=True,
        comment="回复消息 ID",
    )
    metadata_: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="附件/额外信息"
    )
    is_recalled: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", comment="是否已撤回"
    )
    read_by: Mapped[list | None] = mapped_column(
        JSON, nullable=True, comment="已读用户 ID 列表"
    )

    # 关系
    conversation: Mapped["IMConversation"] = relationship(back_populates="messages")
    reply_to: Mapped["IMMessage | None"] = relationship(
        remote_side="IMMessage.id", lazy="selectin"
    )

    __table_args__ = (
        Index("ix_im_messages_conversation_id", "conversation_id"),
        Index("ix_im_messages_sender_id", "sender_id"),
        Index("ix_im_messages_created_at", "created_at"),
        Index(
            "ix_im_messages_conv_created",
            "conversation_id",
            "created_at",
        ),
    )
