# -*- coding: utf-8 -*-
"""审批流模型 — 匹配已有数据库表结构"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, GUID

import enum


class ApprovalStatus(str, enum.Enum):
    """审批状态"""
    pending = "pending"       # 待审批
    approved = "approved"     # 已通过
    rejected = "rejected"    # 已驳回
    withdrawn = "withdrawn"   # 已撤回


class ApprovalType(str, enum.Enum):
    """审批类型"""
    contract = "contract"       # 合同审批
    document = "document"       # 文档审批
    case_assign = "case_assign" # 案件指派
    expense = "expense"         # 费用报销
    leave = "leave"             # 请假
    custom = "custom"           # 自定义


class ChainMode(str, enum.Enum):
    """审批链模式"""
    sequential = "sequential"  # 顺序审批（逐级）
    parallel = "parallel"      # 并行审批（会签）


class Approval(Base, TimestampMixin):
    """审批记录模型 — 映射到 approvals 表"""

    __tablename__ = "approvals"

    title: Mapped[str] = mapped_column(String(500), nullable=False)

    # 数据库列名是 approval_type，Python 属性名用 approval_type
    approval_type: Mapped[str] = mapped_column(
        String(100), nullable=False, default=ApprovalType.custom.value
    )

    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ApprovalStatus.pending.value
    )

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 发起人
    requester_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 组织
    org_id: Mapped[Optional[str]] = mapped_column(
        GUID(), nullable=True
    )

    # 关联资源
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # 审批人
    approver_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # 审批时间
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # 审批意见
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 附加数据
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 风险等级
    risk_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="low"
    )

    # 过期时间
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ========== 审批链支持 ==========

    # 审批链配置 JSON:
    # {
    #   "mode": "sequential" | "parallel",
    #   "steps": [
    #     {"step": 1, "approver_id": "xxx", "approver_name": "张三", "status": "pending"},
    #     {"step": 2, "approver_id": "yyy", "approver_name": "李四", "status": "pending"}
    #   ]
    # }
    approval_chain: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 当前审批步骤（从 0 开始）
    current_step: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # 关联的审批模板ID
    template_id: Mapped[Optional[str]] = mapped_column(
        GUID(), nullable=True
    )


class ApprovalTemplate(Base, TimestampMixin):
    """审批模板模型 — 预定义审批流程"""

    __tablename__ = "approval_templates"

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # 模板适用类型：contract / expense / case_assign / document / custom
    type: Mapped[str] = mapped_column(
        String(100), nullable=False, default=ApprovalType.custom.value
    )

    # 审批链配置 JSON，同 Approval.approval_chain 格式
    chain_config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # 创建人
    created_by: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # 是否启用
    enabled: Mapped[bool] = mapped_column(
        default=True, nullable=False
    )
