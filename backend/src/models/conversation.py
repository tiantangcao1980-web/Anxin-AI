"""
å¯¹è¯ç®¡çæ¨¡å
"""

import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON as JSONB
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin, ValueEnum


class MessageRole(str, enum.Enum):
    """æ¶æ¯è§è²"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base, TimestampMixin):
    """å¯¹è¯ä¼è¯"""

    __tablename__ = "conversations"

    title: Mapped[str | None] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text)

    # ä¼è¯ä¸ä¸æ?
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # ç»è®¡ä¿¡æ¯
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    # æåæ´»å¨æ¶é?
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # å¤é®
    user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))
    case_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("cases.id", ondelete="SET NULL"))

    # 收藏
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    starred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # å³ç³»
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base, TimestampMixin):
    """å¯¹è¯æ¶æ¯"""

    __tablename__ = "messages"

    role: Mapped[MessageRole] = mapped_column(
        ValueEnum(
            MessageRole,
            values_callable=lambda x: [e.value for e in x],
            name="messagerole",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AIç¸å³ä¿¡æ¯
    agent_name: Mapped[str | None] = mapped_column(String(100))
    reasoning: Mapped[str | None] = mapped_column(Text)  # æ¨çè¿ç¨

    # å¼ç¨åå¨ä½?
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    actions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)

    # Tokenç»è®¡
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # ç¨æ·åé¦
    rating: Mapped[int | None] = mapped_column(Integer)  # 1-5è¯å
    feedback: Mapped[str | None] = mapped_column(Text)

    # åæ°æ?
    msg_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # å¤é®
    conversation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )

    # å³ç³»
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")
