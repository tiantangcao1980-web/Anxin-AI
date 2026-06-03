# -*- coding: utf-8 -*-
"""
企业内网集群 —— 部门 / 成员 / 群组 / 岗位 / 角色绑定

设计见 docs/v3/enterprise-cluster-design.md §2.2。

注意：本文件**只声明 ORM 模型**；Alembic migration 由
``backend/alembic/versions/...`` 单独生成。
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import GUID, Base, TimestampMixin

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# 部门
# ---------------------------------------------------------------------------


class Department(Base, TimestampMixin):
    """部门（树形 parent_id + materialized path）。"""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_departments_org_code"),
        Index("idx_departments_org_parent", "org_id", "parent_id"),
        Index("idx_departments_path", "path"),
    )

    org_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # materialized path 形如 "/root/dept_a/dept_b"，由 service 层维护
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    order_idx: Mapped[int] = mapped_column(Integer, default=0)
    leader_id: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    external_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    ext_source: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # 关系
    # 注：父/子关系故意**不在 ORM 层声明**，避免自引用 backref 触发懒加载；
    # 树遍历通过 materialized ``path`` 字段 + DepartmentService 完成。
    memberships: Mapped[list[DepartmentMembership]] = relationship(
        "DepartmentMembership",
        back_populates="department",
        cascade="all, delete-orphan",
    )


# ---------------------------------------------------------------------------
# 成员-部门
# ---------------------------------------------------------------------------


class DepartmentMembership(Base, TimestampMixin):
    """User × Department 多对多（一人多部门，含主部门标记）。"""

    __tablename__ = "department_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "department_id", name="uq_dept_membership"),
        Index("idx_dept_memberships_user", "user_id"),
        Index("idx_dept_memberships_dept", "department_id"),
    )

    user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    department_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    position_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    department: Mapped[Department] = relationship("Department", back_populates="memberships")


# ---------------------------------------------------------------------------
# 用户组（飞书"群体"）
# ---------------------------------------------------------------------------


class UserGroup(Base, TimestampMixin):
    """跨部门的自定义用户群体。"""

    __tablename__ = "user_groups"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_user_groups_org_name"),
    )

    org_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    group_type: Mapped[str] = mapped_column(String(50), default="static")  # static | dynamic
    rule: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    members: Mapped[list[UserGroupMember]] = relationship(
        "UserGroupMember",
        back_populates="group",
        cascade="all, delete-orphan",
    )


class UserGroupMember(Base, TimestampMixin):
    """UserGroup × User 关系。"""

    __tablename__ = "user_group_members"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_user_group_members"),
    )

    group_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("user_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    group: Mapped[UserGroup] = relationship("UserGroup", back_populates="members")


# ---------------------------------------------------------------------------
# 岗位
# ---------------------------------------------------------------------------


class Position(Base, TimestampMixin):
    """岗位（可选，研发-后端-P6 这类职级序列）。"""

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_positions_org_code"),
    )

    org_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    level: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# 角色绑定（核心）
# ---------------------------------------------------------------------------


class RoleBinding(Base, TimestampMixin):
    """主体 × 角色 × 作用域 —— 多维授权核心表。

    subject_type:
        - ``user``       绑到具体用户
        - ``department`` 绑到部门（向下继承到所有后代）
        - ``group``      绑到 UserGroup
        - ``position``   绑到岗位
    scope_type:
        - ``org``        在整个组织内生效
        - ``department`` 仅在该部门及其后代生效
    role 字段沿用 ``core.deps.UserRole`` 枚举值字符串。
    """

    __tablename__ = "role_bindings"
    __table_args__ = (
        UniqueConstraint(
            "subject_type",
            "subject_id",
            "role",
            "scope_type",
            "scope_id",
            name="uq_role_bindings_subject_role_scope",
        ),
        Index("idx_role_bindings_subject", "subject_type", "subject_id"),
        Index("idx_role_bindings_scope", "scope_type", "scope_id"),
        Index("idx_role_bindings_org", "org_id"),
    )

    org_id: Mapped[str] = mapped_column(
        GUID(),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    subject_id: Mapped[str] = mapped_column(GUID(), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False)
    scope_id: Mapped[str] = mapped_column(GUID(), nullable=False)

    granted_by: Mapped[str | None] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)


__all__ = [
    "Department",
    "DepartmentMembership",
    "Position",
    "RoleBinding",
    "UserGroup",
    "UserGroupMember",
]
