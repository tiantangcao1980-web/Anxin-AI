"""

合同管理模型

"""

import enum
from datetime import date
from typing import Any

from sqlalchemy import JSON as JSONB
from sqlalchemy import BigInteger, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin, ValueEnum


class ContractStatus(str, enum.Enum):
    """合同状态"""

    DRAFT = "draft"  # 草稿

    PENDING_REVIEW = "pending_review"  # 待审核

    UNDER_REVIEW = "under_review"  # 审核中

    REVIEW_FAILED = "review_failed"  # 审查失败，可重试

    APPROVED = "approved"  # 已批准

    SIGNED = "signed"  # 已签署

    ACTIVE = "active"  # 生效中

    EXPIRED = "expired"  # 已过期

    TERMINATED = "terminated"  # 已终止


class RiskLevel(str, enum.Enum):
    """风险等级"""

    LOW = "low"

    MEDIUM = "medium"

    HIGH = "high"

    CRITICAL = "critical"


class Contract(Base, TimestampMixin):
    """合同模型"""

    __tablename__ = "contracts"

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    contract_number: Mapped[str | None] = mapped_column(String(50), unique=True)

    contract_type: Mapped[str] = mapped_column(String(100), nullable=False)

    status: Mapped[ContractStatus] = mapped_column(
        ValueEnum(ContractStatus), default=ContractStatus.DRAFT
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # 当事人信息

    party_a: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 甲方信息

    party_b: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 乙方信息

    other_parties: Mapped[list[Any] | None] = mapped_column(JSONB)  # 其他方

    # 合同金额

    amount: Mapped[float | None] = mapped_column(Float)

    currency: Mapped[str] = mapped_column(String(10), default="CNY")

    # 关键日期

    sign_date: Mapped[date | None] = mapped_column(Date)

    effective_date: Mapped[date | None] = mapped_column(Date)

    expiry_date: Mapped[date | None] = mapped_column(Date)

    # AI审核结果

    risk_level: Mapped[RiskLevel | None] = mapped_column(ValueEnum(RiskLevel))

    risk_score: Mapped[float | None] = mapped_column(Float)

    review_summary: Mapped[str | None] = mapped_column(Text)

    key_terms: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 关键条款提取

    review_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # 完整审查结果

    # 合同文本存储
    original_text: Mapped[str | None] = mapped_column(Text)  # 原始合同文本
    modified_text: Mapped[str | None] = mapped_column(Text)  # 修改后的合同文本
    esign_flow_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    esign_provider: Mapped[str | None] = mapped_column(String(50))

    # 外键

    document_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("documents.id", ondelete="SET NULL")
    )

    org_id: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE")
    )

    reviewed_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )

    # 关系

    clauses: Mapped[list["ContractClause"]] = relationship(
        "ContractClause", back_populates="contract", cascade="all, delete-orphan"
    )

    risks: Mapped[list["ContractRisk"]] = relationship(
        "ContractRisk", back_populates="contract", cascade="all, delete-orphan"
    )

    versions: Mapped[list["ContractVersion"]] = relationship(
        "ContractVersion", back_populates="contract", cascade="all, delete-orphan"
    )

    attachments: Mapped[list["ContractAttachment"]] = relationship(
        "ContractAttachment", back_populates="contract", cascade="all, delete-orphan"
    )


class ContractVersion(Base, TimestampMixin):
    """合同版本快照"""

    __tablename__ = "contract_versions"
    __table_args__ = (
        UniqueConstraint("contract_id", "version", name="uq_contract_versions_contract_version"),
    )

    contract_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    source: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)

    description: Mapped[str | None] = mapped_column(String(255))

    created_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )

    contract: Mapped["Contract"] = relationship("Contract", back_populates="versions")


class ContractAttachment(Base, TimestampMixin):
    """合同附件对象存储记录"""

    __tablename__ = "contract_attachments"

    contract_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )

    org_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )

    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)

    content_type: Mapped[str] = mapped_column(String(255), nullable=False)

    storage_backend: Mapped[str] = mapped_column(String(16), nullable=False)

    object_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)

    file_size: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    uploaded_by: Mapped[str | None] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL")
    )

    contract: Mapped["Contract"] = relationship("Contract", back_populates="attachments")


class ContractClause(Base, TimestampMixin):
    """合同条款"""

    __tablename__ = "contract_clauses"

    clause_number: Mapped[str] = mapped_column(String(50), nullable=False)

    clause_type: Mapped[str] = mapped_column(String(100), nullable=False)

    title: Mapped[str | None] = mapped_column(String(255))

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # AI分析

    is_standard: Mapped[bool] = mapped_column(default=True)  # 是否标准条款

    risk_level: Mapped[RiskLevel | None] = mapped_column(ValueEnum(RiskLevel))

    analysis: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    suggestions: Mapped[list[Any] | None] = mapped_column(JSONB)

    # 外键

    contract_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )

    # 关系

    contract: Mapped["Contract"] = relationship("Contract", back_populates="clauses")


class ContractRisk(Base, TimestampMixin):
    """合同风险点"""

    __tablename__ = "contract_risks"

    risk_type: Mapped[str] = mapped_column(String(100), nullable=False)

    risk_level: Mapped[RiskLevel] = mapped_column(ValueEnum(RiskLevel), default=RiskLevel.MEDIUM)

    title: Mapped[str] = mapped_column(String(255), nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)

    # 关联条款

    related_clause: Mapped[str | None] = mapped_column(String(50))

    original_text: Mapped[str | None] = mapped_column(Text)  # 原文

    # 建议

    suggestion: Mapped[str | None] = mapped_column(Text)

    suggested_text: Mapped[str | None] = mapped_column(Text)  # 建议修改后的文本

    # 处理状态

    is_resolved: Mapped[bool] = mapped_column(default=False)

    resolution_note: Mapped[str | None] = mapped_column(Text)

    # 外键

    contract_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )

    # 关系

    contract: Mapped["Contract"] = relationship("Contract", back_populates="risks")
