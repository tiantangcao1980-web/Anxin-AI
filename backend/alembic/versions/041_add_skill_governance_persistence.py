"""add skill governance persistence tables

Revision ID: 041_skill_governance_persistence
Revises: 040_agent_governance_control_plane
Create Date: 2026-05-08
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op
from src.models.base import GUID

revision: str = "041_skill_governance_persistence"
down_revision: str | None = "040_agent_governance_control_plane"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "skill_governance_proposals",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", GUID(), nullable=False),
        sa.Column("skill_name", sa.String(length=160), nullable=False),
        sa.Column("current_version", sa.String(length=80), nullable=True),
        sa.Column("proposed_version", sa.String(length=80), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("created_by", sa.String(length=160), nullable=False),
        sa.Column("created_by_role", sa.String(length=60), nullable=False, server_default="agent"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="draft"),
        sa.Column("eval_results", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.String(length=160), nullable=True),
        sa.Column("approver_role", sa.String(length=60), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gray_percentage", sa.Integer(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rolled_back_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rollback_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_skill_governance_proposals_org_id"),
        sa.UniqueConstraint("org_id", "skill_name", "proposed_version", name="uq_skill_governance_proposals_org_version"),
    )
    op.create_index(
        "ix_skill_governance_proposals_org_status",
        "skill_governance_proposals",
        ["org_id", "status"],
    )
    op.create_index(
        "ix_skill_governance_proposals_skill",
        "skill_governance_proposals",
        ["org_id", "skill_name"],
    )

    op.create_table(
        "skill_enabled_versions",
        sa.Column("id", GUID(), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", GUID(), nullable=False),
        sa.Column("skill_name", sa.String(length=160), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="enabled"),
        sa.Column("proposal_id", GUID(), nullable=True),
        sa.Column("enabled_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["org_id", "proposal_id"],
            ["skill_governance_proposals.org_id", "skill_governance_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "skill_name", name="uq_skill_enabled_versions_org_skill"),
    )
    op.create_index(
        "ix_skill_enabled_versions_org_status",
        "skill_enabled_versions",
        ["org_id", "status"],
    )

    op.create_table(
        "skill_governance_audit_events",
        sa.Column("id", GUID(), nullable=False),
        sa.Column("org_id", GUID(), nullable=False),
        sa.Column("proposal_id", GUID(), nullable=True),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="success"),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("resource_snapshot", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["org_id", "proposal_id"],
            ["skill_governance_proposals.org_id", "skill_governance_proposals.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_skill_governance_audit_events_org_created",
        "skill_governance_audit_events",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_skill_governance_audit_events_action_status",
        "skill_governance_audit_events",
        ["action", "status"],
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_skill_governance_audit_events_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'skill_governance_audit_events is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER tr_skill_governance_audit_events_no_update_delete
            BEFORE UPDATE OR DELETE ON skill_governance_audit_events
            FOR EACH ROW EXECUTE FUNCTION prevent_skill_governance_audit_events_mutation();
            """
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS tr_skill_governance_audit_events_no_update_delete ON skill_governance_audit_events")
        op.execute("DROP FUNCTION IF EXISTS prevent_skill_governance_audit_events_mutation()")

    op.drop_index("ix_skill_governance_audit_events_action_status", table_name="skill_governance_audit_events")
    op.drop_index("ix_skill_governance_audit_events_org_created", table_name="skill_governance_audit_events")
    op.drop_table("skill_governance_audit_events")

    op.drop_index("ix_skill_enabled_versions_org_status", table_name="skill_enabled_versions")
    op.drop_table("skill_enabled_versions")

    op.drop_index("ix_skill_governance_proposals_skill", table_name="skill_governance_proposals")
    op.drop_index("ix_skill_governance_proposals_org_status", table_name="skill_governance_proposals")
    op.drop_table("skill_governance_proposals")
