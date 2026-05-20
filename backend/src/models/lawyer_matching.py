"""
找律师模块 — 数据模型

核心理念（滴滴模式）：
- 用户发起需求 → AI 预分析 → 生成匿名案情摘要 → 匹配律师
- 匿名聊天室（律师仅看到：案情摘要 + 法律领域 + 紧急程度）
- 用户满意 → 一键委托 → 签署委托协议 → 支付 → 揭示身份

信息分级揭示：
- Level 0: 匿名咨询（律师看脱敏案情）
- Level 1: 意向沟通（用户主动揭示部分信息）
- Level 2: 正式委托（签约后互相公开必要信息）
- Level 3: 深度合作（全部材料共享）
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin

# ===== 枚举定义 =====


class ConsultationStatus(str, PyEnum):
    """咨询状态"""

    PENDING = "pending"  # 待匹配
    MATCHING = "matching"  # 匹配中
    MATCHED = "matched"  # 已匹配，等待律师接单
    IN_PROGRESS = "in_progress"  # 咨询进行中
    DELEGATION = "delegation"  # 委托签约中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消
    EXPIRED = "expired"  # 已过期


class UrgencyLevel(str, PyEnum):
    """紧急程度"""

    LOW = "low"  # 一般咨询
    MEDIUM = "medium"  # 需要尽快处理
    HIGH = "high"  # 紧急
    URGENT = "urgent"  # 非常紧急（3分钟匹配）


class PrivacyLevel(int, PyEnum):
    """信息揭示级别"""

    ANONYMOUS = 0  # 完全匿名
    PARTIAL = 1  # 部分信息（行业、城市）
    DELEGATED = 2  # 正式委托（必要信息）
    FULL = 3  # 深度合作（全部材料）


class DelegationStatus(str, PyEnum):
    """委托状态"""

    DRAFT = "draft"  # 草稿
    PENDING_SIGN = "pending_sign"  # 待签署
    SIGNED = "signed"  # 已签署
    PAID = "paid"  # 已支付
    IN_PROGRESS = "in_progress"  # 服务中
    COMPLETED = "completed"  # 已完成
    DISPUTED = "disputed"  # 争议中
    REFUNDED = "refunded"  # 已退款


# ===== 数据模型 =====


class LawyerProfile(Base, TimestampMixin):
    """入驻律师档案"""

    __tablename__ = "lawyer_profiles"

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    # 基本信息
    real_name: Mapped[str] = mapped_column(String(100), nullable=False)
    license_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    law_firm: Mapped[str | None] = mapped_column(String(200))
    years_of_practice: Mapped[int] = mapped_column(Integer, default=0)
    city: Mapped[str | None] = mapped_column(String(50))
    province: Mapped[str | None] = mapped_column(String(50))

    # 专业领域（JSON 数组）
    specializations: Mapped[list[str] | None] = mapped_column(JSON, default=list)
    # 简介
    bio: Mapped[str | None] = mapped_column(Text)
    # 头像
    avatar_url: Mapped[str | None] = mapped_column(String(500))

    # 评分与统计
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    success_cases: Mapped[int] = mapped_column(Integer, default=0)
    total_reviews: Mapped[int] = mapped_column(Integer, default=0)

    # 价格区间（元/小时）
    hourly_rate_min: Mapped[int | None] = mapped_column(Integer)
    hourly_rate_max: Mapped[int | None] = mapped_column(Integer)

    # 在线状态
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    is_accepting: Mapped[bool] = mapped_column(Boolean, default=True)
    available_hours: Mapped[dict[str, Any] | None] = mapped_column(JSON)  # 可接单时段

    # 认证状态
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 关系
    user = relationship("User", backref="lawyer_profile")


class Consultation(Base, TimestampMixin):
    """咨询请求（用户发起找律师）"""

    __tablename__ = "consultations"

    # 发起人
    user_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))

    # AI 生成的匿名案情摘要（脱敏后）
    anonymous_summary: Mapped[str | None] = mapped_column(Text)
    # 原始描述（仅系统内部可见，律师不可见）
    original_description: Mapped[str | None] = mapped_column(Text)

    # 法律领域标签
    legal_domain: Mapped[str | None] = mapped_column(String(100))  # 合同纠纷/劳动争议/知识产权等
    legal_tags: Mapped[list[str] | None] = mapped_column(JSON, default=list)

    # 紧急程度
    urgency: Mapped[str] = mapped_column(String(20), default=UrgencyLevel.MEDIUM.value)

    # 咨询状态
    status: Mapped[str] = mapped_column(String(20), default=ConsultationStatus.PENDING.value)

    # 信息揭示级别
    privacy_level: Mapped[int] = mapped_column(Integer, default=0)

    # 匹配的律师
    matched_lawyer_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 匹配时间
    matched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # 完成时间
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 用户评分
    user_rating: Mapped[int | None] = mapped_column(Integer)  # 1-5
    user_review: Mapped[str | None] = mapped_column(Text)

    # 关系
    user = relationship("User", foreign_keys=[user_id], backref="consultations")
    matched_lawyer = relationship("User", foreign_keys=[matched_lawyer_id])


class Delegation(Base, TimestampMixin):
    """委托记录（一键委托 + 签约 + 支付）"""

    __tablename__ = "delegations"

    consultation_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("consultations.id", ondelete="SET NULL"), nullable=True
    )

    # 委托双方
    client_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))
    lawyer_id: Mapped[str] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))

    # 委托内容
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    service_type: Mapped[str | None] = mapped_column(String(50))  # 即时咨询/预约咨询/案件委托

    # 状态
    status: Mapped[str] = mapped_column(String(20), default=DelegationStatus.DRAFT.value)

    # 费用
    quoted_amount: Mapped[float | None] = mapped_column(Float)  # 报价金额
    platform_fee: Mapped[float | None] = mapped_column(Float)  # 平台服务费
    total_amount: Mapped[float | None] = mapped_column(Float)  # 总金额
    paid_amount: Mapped[float | None] = mapped_column(Float)  # 已支付金额

    # 签署
    contract_url: Mapped[str | None] = mapped_column(String(500))  # 委托协议文件
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 关系
    consultation = relationship("Consultation", backref="delegation")
    client = relationship("User", foreign_keys=[client_id], backref="delegations_as_client")
    lawyer = relationship("User", foreign_keys=[lawyer_id], backref="delegations_as_lawyer")
