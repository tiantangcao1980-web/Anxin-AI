# -*- coding: utf-8 -*-
"""
律所内部管理模型
包含团队、团队成员、案件分配、工时记录、发票等表
"""

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer,
    JSON, String, Text, UniqueConstraint, Index, func,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin, GUID


class Team(Base, TimestampMixin):
    """团队表"""

    __tablename__ = "teams"

    org_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属组织",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="团队名称",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="团队描述",
    )
    leader_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, comment="团队负责人",
    )


class TeamMember(Base, TimestampMixin):
    """团队成员表"""

    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_members_team_user"),
    )

    team_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="团队ID",
    )
    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="用户ID",
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="member", comment="角色: leader | member",
    )


class CaseAssignment(Base, TimestampMixin):
    """案件分配表"""

    __tablename__ = "case_assignments"

    case_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="案件ID",
    )
    assignee_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="被分配人",
    )
    assigned_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, comment="分配人",
    )
    role: Mapped[str] = mapped_column(
        String(30), nullable=False, default="support",
        comment="角色: lead | support | review",
    )
    hours_estimated: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="预估工时（小时）",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active",
        comment="状态: active | completed | withdrawn",
    )


class TimeEntry(Base, TimestampMixin):
    """工时记录表"""

    __tablename__ = "time_entries"
    __table_args__ = (
        Index("ix_time_entries_user_date", "user_id", "date"),
    )

    user_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="用户ID",
    )
    case_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联案件ID",
    )
    date: Mapped[date] = mapped_column(
        Date, nullable=False, comment="工时日期",
    )
    minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="工时（分钟）",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="工时说明",
    )
    billable: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, comment="是否可计费",
    )
    rate: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="费率（元/小时）",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="状态: draft | submitted | approved | rejected",
    )
    approved_by: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, comment="审批人",
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审批时间",
    )


class Invoice(Base, TimestampMixin):
    """发票表"""

    __tablename__ = "invoices"

    org_id: Mapped[str] = mapped_column(
        GUID(), ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False, index=True, comment="所属组织",
    )
    case_id: Mapped[Optional[str]] = mapped_column(
        GUID(), ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True, index=True, comment="关联案件ID",
    )
    number: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, comment="发票编号",
    )
    client_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="客户名称",
    )
    total_amount: Mapped[float] = mapped_column(
        Float, nullable=False, comment="总金额",
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft",
        comment="状态: draft | sent | paid | overdue | cancelled",
    )
    due_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True, comment="到期日",
    )
    items: Mapped[Optional[list]] = mapped_column(
        JSON, nullable=True, default=list,
        comment="发票明细: [{description, hours, rate, amount}]",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="备注",
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="支付时间",
    )
