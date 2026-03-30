# -*- coding: utf-8 -*-
"""
调查持久化模型 — Investigation Model

存储尽职调查结果，支持历史查询和报告生成
"""

from typing import Optional
from sqlalchemy import String, Text, JSON, Integer, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from src.models.base import Base, TimestampMixin, GUID


class InvestigationStatus(str, enum.Enum):
    """调查状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class InvestigationRiskLevel(str, enum.Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class Investigation(Base, TimestampMixin):
    """尽职调查记录"""
    __tablename__ = "investigations"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    investigation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="comprehensive"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InvestigationStatus.PENDING.value,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 调查结果 (JSON)
    basic_info: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    litigation: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    credit: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    risk: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    relations: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 综合报告
    report_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InvestigationRiskLevel.UNKNOWN.value,
    )
    risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Agent 协同元数据
    agent_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    consensus_result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    conflicts: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    def to_dict(self):
        d = super().to_dict()
        d["created_at"] = str(d.get("created_at", ""))
        d["updated_at"] = str(d.get("updated_at", ""))
        return d
