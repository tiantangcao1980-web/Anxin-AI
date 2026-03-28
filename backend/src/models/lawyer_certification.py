# -*- coding: utf-8 -*-
"""律师认证与接单配置模型"""

from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Text, ForeignKey, Boolean, DateTime, Integer, Float, JSON, Date, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin, GUID


class LawyerCertification(Base, TimestampMixin):
    """律师执业证认证"""
    __tablename__ = "lawyer_certifications"

    lawyer_profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("lawyer_profiles.id", ondelete="CASCADE"),
        unique=True, nullable=False, comment="律师档案ID"
    )
    license_image_url: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="执业证照片URL"
    )
    id_card_image_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="身份证照片URL（可选）"
    )
    license_issue_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="执业证签发日期"
    )
    license_expiry_date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="执业证到期日期"
    )
    bar_association: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="所属律师协会"
    )

    # 审核状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="认证状态: pending/approved/rejected/expired"
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="驳回原因"
    )
    verified_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="审核人ID"
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审核时间"
    )

    # Relationships
    lawyer_profile = relationship("LawyerProfile", backref="certification")
    verifier = relationship("User", foreign_keys=[verified_by])

    __table_args__ = (
        Index("ix_lawyer_certifications_status", "status"),
        Index("ix_lawyer_certifications_expiry", "license_expiry_date"),
    )


class LawyerServiceConfig(Base, TimestampMixin):
    """律师接单配置"""
    __tablename__ = "lawyer_service_configs"

    lawyer_profile_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("lawyer_profiles.id", ondelete="CASCADE"),
        unique=True, nullable=False, comment="律师档案ID"
    )
    service_types: Mapped[Optional[dict]] = mapped_column(
        JSON, default=list, comment='服务类型: ["instant_consultation","appointment","case_delegation"]'
    )
    auto_accept: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, comment="是否自动接单"
    )
    max_concurrent_cases: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False, comment="最大并发案件数"
    )
    response_time_hours: Mapped[int] = mapped_column(
        Integer, default=24, nullable=False, comment="承诺响应时间（小时）"
    )
    working_hours: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True, comment='工作时间: {"mon":"09:00-18:00", ...}'
    )
    min_case_amount: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="最低接案金额"
    )

    # Relationships
    lawyer_profile = relationship("LawyerProfile", backref="service_config")
