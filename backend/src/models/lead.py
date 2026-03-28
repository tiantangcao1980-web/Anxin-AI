# -*- coding: utf-8 -*-
"""
案源管理模型
"""

from typing import Optional
from sqlalchemy import String, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, GUID


class Lead(Base, TimestampMixin):
    """案源线索表"""
    __tablename__ = "leads"

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_info: Mapped[Optional[str]] = mapped_column(String(255))
    source: Mapped[Optional[str]] = mapped_column(String(100))  # 转介绍, 线上咨询, 主动拓展, 电话咨询
    case_type: Mapped[Optional[str]] = mapped_column(String(100))
    estimated_amount: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str] = mapped_column(String(20), default="new")  # new, contacted, qualified, proposal, won, lost
    follow_ups: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # 关联
    assignee_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )
    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    # 关系
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assignee_id])
    creator: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])
