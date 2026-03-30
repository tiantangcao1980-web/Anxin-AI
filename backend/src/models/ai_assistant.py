# -*- coding: utf-8 -*-
"""AI 私有助手模型"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Boolean, Integer, Float, Index
from sqlalchemy import JSON as JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, GUID


class AIAssistantConfig(Base, TimestampMixin):
    """企业专属 AI 助手配置"""

    __tablename__ = "ai_assistant_configs"

    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, default="安心法务助手"
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    welcome_message: Mapped[Optional[str]] = mapped_column(
        Text, default="您好！我是您的专属法务助手，有什么法律问题可以帮您？"
    )
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    personality: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict, comment="风格配置: style, tone, language"
    )
    enabled_agents: Mapped[Optional[list]] = mapped_column(
        JSONB, default=list, comment="启用的 Agent key 列表"
    )
    knowledge_base_ids: Mapped[Optional[list]] = mapped_column(
        JSONB, default=list, comment="关联的知识库 ID 列表"
    )
    max_context_turns: Mapped[int] = mapped_column(
        Integer, default=10, comment="保留的上下文轮数"
    )
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    llm_config_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="指定使用的 LLM 配置 ID"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        Index("ix_ai_assistant_configs_org_id", "org_id"),
        Index("ix_ai_assistant_configs_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<AIAssistantConfig {self.name} org={self.org_id}>"


class ConversationSummary(Base, TimestampMixin):
    """对话摘要（AI 自动生成）"""

    __tablename__ = "conversation_summaries"

    conversation_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False, comment="AI 生成的摘要")
    key_topics: Mapped[Optional[list]] = mapped_column(
        JSONB, default=list, comment="关键话题"
    )
    action_items: Mapped[Optional[list]] = mapped_column(
        JSONB, default=list, comment="待办事项"
    )
    sentiment: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="positive/neutral/negative"
    )
    turn_count: Mapped[int] = mapped_column(Integer, default=0)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    legal_domains: Mapped[Optional[list]] = mapped_column(
        JSONB, default=list, comment="涉及的法律领域"
    )

    __table_args__ = (
        Index("ix_conversation_summaries_user_id", "user_id"),
        Index("ix_conversation_summaries_conversation_id", "conversation_id"),
    )

    def __repr__(self) -> str:
        return f"<ConversationSummary conv={self.conversation_id}>"


class AIAssistantFeedback(Base, TimestampMixin):
    """AI 助手反馈"""

    __tablename__ = "ai_assistant_feedbacks"

    assistant_config_id: Mapped[Optional[str]] = mapped_column(
        GUID(),
        ForeignKey("ai_assistant_configs.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True
    )
    message_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="针对具体消息的反馈"
    )
    rating: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="评分 1-5"
    )
    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    feedback_type: Mapped[str] = mapped_column(
        String(30),
        default="helpful",
        comment="helpful/unhelpful/incorrect/offensive/other",
    )

    __table_args__ = (
        Index("ix_ai_assistant_feedbacks_user_id", "user_id"),
        Index("ix_ai_assistant_feedbacks_config_id", "assistant_config_id"),
        Index("ix_ai_assistant_feedbacks_conversation_id", "conversation_id"),
    )

    def __repr__(self) -> str:
        return f"<AIAssistantFeedback user={self.user_id} rating={self.rating}>"
