# -*- coding: utf-8 -*-
"""
案源市场模型 (V2 架构)

核心：连接需求方（发布法律需求）和服务方（律师接单/投标）。

三张表：
1. CaseRequest — 需求方发布的法律需求
2. LawyerBid — 律师对某个需求的投标/报价
3. CaseMatch — 系统撮合结果（需求+律师的匹配记录）
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, Float, Boolean, DateTime, ForeignKey, Index
from sqlalchemy import JSON as JSONB
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, GUID


class RequestStatus(str, enum.Enum):
    """需求状态"""
    DRAFT = "draft"             # 草稿
    PUBLISHED = "published"     # 已发布（律师可见）
    MATCHED = "matched"         # 已匹配（有律师接单）
    IN_PROGRESS = "in_progress" # 服务进行中
    COMPLETED = "completed"     # 已完成
    CANCELLED = "cancelled"     # 已取消
    EXPIRED = "expired"         # 已过期


class BidStatus(str, enum.Enum):
    """投标状态"""
    PENDING = "pending"         # 待审核
    ACCEPTED = "accepted"       # 已接受
    REJECTED = "rejected"       # 已拒绝
    WITHDRAWN = "withdrawn"     # 律师撤回


class CaseRequest(Base, TimestampMixin):
    """
    案源需求（需求方发布）

    需求方在 /app 端发起，选择"允许向律师推送"后进入案源市场。
    """
    __tablename__ = "case_requests"

    # 发布者
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="SET NULL")
    )

    # 需求信息
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    legal_area: Mapped[str] = mapped_column(String(50), nullable=False)  # 合同/劳动/知产/诉讼...
    urgency: Mapped[str] = mapped_column(String(20), default="normal")  # urgent/normal/flexible
    budget_min: Mapped[Optional[float]] = mapped_column(Float)
    budget_max: Mapped[Optional[float]] = mapped_column(Float)
    location: Mapped[Optional[str]] = mapped_column(String(100))  # 所在城市

    # 隐私控制
    is_anonymous: Mapped[bool] = mapped_column(Boolean, default=True)  # 默认匿名
    visible_to_market: Mapped[bool] = mapped_column(Boolean, default=True)

    # 状态
    status: Mapped[RequestStatus] = mapped_column(
        SQLEnum(RequestStatus), default=RequestStatus.PUBLISHED
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 匹配结果
    matched_lawyer_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # 扩展数据
    tags: Mapped[Optional[list]] = mapped_column(JSONB)  # ["合同纠纷", "50万以上"]
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    # 统计
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    bid_count: Mapped[int] = mapped_column(Integer, default=0)

    # 关系
    user = relationship("User", foreign_keys=[user_id], backref="case_requests")
    bids = relationship("LawyerBid", back_populates="case_request", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_case_requests_status", "status"),
        Index("ix_case_requests_legal_area", "legal_area"),
        Index("ix_case_requests_user_id", "user_id"),
        Index("ix_case_requests_location", "location"),
    )


class LawyerBid(Base, TimestampMixin):
    """
    律师投标（服务方端提交）

    律师在 /pro 端看到案源后提交报价和方案。
    """
    __tablename__ = "lawyer_bids"

    # 关联
    case_request_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("case_requests.id", ondelete="CASCADE"), nullable=False
    )
    lawyer_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 报价
    quoted_price: Mapped[Optional[float]] = mapped_column(Float)
    proposal: Mapped[str] = mapped_column(Text, nullable=False)  # 方案说明
    estimated_days: Mapped[Optional[int]] = mapped_column(Integer)  # 预计完成天数

    # 状态
    status: Mapped[BidStatus] = mapped_column(
        SQLEnum(BidStatus), default=BidStatus.PENDING
    )

    # 需求方评价
    client_rating: Mapped[Optional[int]] = mapped_column(Integer)  # 1-5
    client_comment: Mapped[Optional[str]] = mapped_column(Text)

    # 律师评价（双向评价）
    lawyer_rating: Mapped[Optional[int]] = mapped_column(Integer)
    lawyer_comment: Mapped[Optional[str]] = mapped_column(Text)

    # 关系
    case_request = relationship("CaseRequest", back_populates="bids")
    lawyer = relationship("User", foreign_keys=[lawyer_id])

    __table_args__ = (
        Index("ix_lawyer_bids_case_request", "case_request_id"),
        Index("ix_lawyer_bids_lawyer", "lawyer_id"),
        Index("ix_lawyer_bids_status", "status"),
    )
