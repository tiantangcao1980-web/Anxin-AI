"""add enterprise directory tables (departments / memberships / groups / positions / role_bindings)

设计见 docs/v3/enterprise-cluster-design.md §2.2。

Revision ID: 045_enterprise_directory
Revises: 044_skill_connector_configs
Create Date: 2026-05-14
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op
from src.models.base import GUID

revision: str = "045_enterprise_directory"
down_revision: str | None = "044_skill_connector_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    # ------------------------------------------------------------------
    # departments
    # ------------------------------------------------------------------
    op.create_table(
        "departments",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", GUID(), nullable=False),
        sa.Column("parent_id", GUID(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.Column("path", sa.String(length=1024), nullable=True),
        sa.Column("order_idx", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("leader_id", GUID(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("external_id", sa.String(length=200), nullable=True),
        sa.Column("ext_source", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["departments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["leader_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "code", name="uq_departments_org_code"),
    )
    op.create_index(
        "idx_departments_org_parent",
        "departments",
        ["org_id", "parent_id"],
    )
    op.create_index("idx_departments_path", "departments", ["path"])

    # ------------------------------------------------------------------
    # department_memberships
    # ------------------------------------------------------------------
    op.create_table(
        "department_memberships",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("department_id", GUID(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("position_title", sa.String(length=200), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["department_id"], ["departments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "department_id", name="uq_dept_membership"
        ),
    )
    op.create_index(
        "idx_dept_memberships_user", "department_memberships", ["user_id"]
    )
    op.create_index(
        "idx_dept_memberships_dept", "department_memberships", ["department_id"]
    )

    # ------------------------------------------------------------------
    # user_groups
    # ------------------------------------------------------------------
    op.create_table(
        "user_groups",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "group_type", sa.String(length=50), nullable=False, server_default="static"
        ),
        sa.Column("rule", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "name", name="uq_user_groups_org_name"),
    )

    op.create_table(
        "user_group_members",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("group_id", GUID(), nullable=False),
        sa.Column("user_id", GUID(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["group_id"], ["user_groups.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("group_id", "user_id", name="uq_user_group_members"),
    )

    # ------------------------------------------------------------------
    # positions
    # ------------------------------------------------------------------
    op.create_table(
        "positions",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", GUID(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "code", name="uq_positions_org_code"),
    )

    # ------------------------------------------------------------------
    # role_bindings
    # ------------------------------------------------------------------
    op.create_table(
        "role_bindings",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", GUID(), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("subject_id", GUID(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("scope_type", sa.String(length=20), nullable=False),
        sa.Column("scope_id", GUID(), nullable=False),
        sa.Column("granted_by", GUID(), nullable=True),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_type",
            "subject_id",
            "role",
            "scope_type",
            "scope_id",
            name="uq_role_bindings_subject_role_scope",
        ),
    )
    op.create_index(
        "idx_role_bindings_subject",
        "role_bindings",
        ["subject_type", "subject_id"],
    )
    op.create_index(
        "idx_role_bindings_scope",
        "role_bindings",
        ["scope_type", "scope_id"],
    )
    op.create_index("idx_role_bindings_org", "role_bindings", ["org_id"])


def downgrade() -> None:
    # 反向顺序删表
    op.drop_index("idx_role_bindings_org", table_name="role_bindings")
    op.drop_index("idx_role_bindings_scope", table_name="role_bindings")
    op.drop_index("idx_role_bindings_subject", table_name="role_bindings")
    op.drop_table("role_bindings")

    op.drop_table("positions")

    op.drop_table("user_group_members")
    op.drop_table("user_groups")

    op.drop_index("idx_dept_memberships_dept", table_name="department_memberships")
    op.drop_index("idx_dept_memberships_user", table_name="department_memberships")
    op.drop_table("department_memberships")

    op.drop_index("idx_departments_path", table_name="departments")
    op.drop_index("idx_departments_org_parent", table_name="departments")
    op.drop_table("departments")
