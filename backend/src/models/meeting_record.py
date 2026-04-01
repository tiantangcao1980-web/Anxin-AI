# -*- coding: utf-8 -*-
"""
会议/咨询记录模型

记录 AI 旁听助手的分析结果、纪要和待办事项。
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, GUID, TimestampMixin


class MeetingRecord(Base, TimestampMixin):
    """AI 旁听会议/咨询记录"""

    __tablename__ = "meeting_records"

    conversation_id: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True, comment="关联对话ID（IM或匿名聊天室）"
    )
    conversation_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="对话类型: im | anonymous_chat"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="listening", comment="状态: listening | completed"
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_by: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=False, comment="发起旁听的用户"
    )

    # AI 分析产出
    transcript_text: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="完整对话文本"
    )
    summary: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment="结构化纪要（摘要/法律分析/风险评估/建议）"
    )
    insights: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=list, comment="实时分析结果列表"
    )
    action_items: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=list, comment="待办事项列表"
    )

    # 业务关联
    related_case_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, comment="关联案件"
    )
    related_contract_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, comment="关联合同"
    )
