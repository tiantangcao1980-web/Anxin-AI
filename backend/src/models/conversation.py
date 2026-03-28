"""
å¯¹è¯ç®¡çæ¨¡å
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, ForeignKey, DateTime, Integer, Enum as SQLEnum
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from src.models.base import Base, TimestampMixin, GUID


class MessageRole(str, enum.Enum):
    """æ¶æ¯è§è²"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base, TimestampMixin):
    """å¯¹è¯ä¼è¯"""
    
    __tablename__ = "conversations"
    
    title: Mapped[Optional[str]] = mapped_column(String(255))
    summary: Mapped[Optional[str]] = mapped_column(Text)
    
    # ä¼è¯ä¸ä¸æ?
    context: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # ç»è®¡ä¿¡æ¯
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    
    # æåæ´»å¨æ¶é?
    last_message_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # å¤é®
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE")
    )
    case_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="SET NULL")
    )
    
    # å³ç³»
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base, TimestampMixin):
    """å¯¹è¯æ¶æ¯"""
    
    __tablename__ = "messages"
    
    role: Mapped[MessageRole] = mapped_column(
        SQLEnum(MessageRole), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # AIç¸å³ä¿¡æ¯
    agent_name: Mapped[Optional[str]] = mapped_column(String(100))
    reasoning: Mapped[Optional[str]] = mapped_column(Text)  # æ¨çè¿ç¨
    
    # å¼ç¨åå¨ä½?
    citations: Mapped[Optional[list]] = mapped_column(JSONB)
    actions: Mapped[Optional[list]] = mapped_column(JSONB)
    
    # Tokenç»è®¡
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    
    # ç¨æ·åé¦
    rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5è¯å
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    
    # åæ°æ?
    msg_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # å¤é®
    conversation_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    
    # å³ç³»
    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )
