"""add remote control pairing and command queue

Revision ID: 042_remote_control_queue
Revises: 041_skill_governance_persistence
Create Date: 2026-05-08
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "042_remote_control_queue"
down_revision: str | None = "041_skill_governance_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "remote_control_pairings",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("user_id", sa.CHAR(length=36), nullable=False),
        sa.Column("mobile_device_id", sa.String(length=128), nullable=False),
        sa.Column("desktop_device_id", sa.String(length=128), nullable=False),
        sa.Column("requested_scopes", sa.JSON(), nullable=False),
        sa.Column("privacy_mode", sa.String(length=40), nullable=False, server_default="hybrid"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="pending_desktop_confirmation"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_by", sa.CHAR(length=36), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["confirmed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_remote_control_pairings_org_id"),
    )
    op.create_index(
        "ix_remote_control_pairings_org_status",
        "remote_control_pairings",
        ["org_id", "status"],
    )
    op.create_index(
        "ix_remote_control_pairings_user_desktop",
        "remote_control_pairings",
        ["user_id", "desktop_device_id"],
    )

    op.create_table(
        "remote_control_commands",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("user_id", sa.CHAR(length=36), nullable=False),
        sa.Column("pairing_id", sa.CHAR(length=36), nullable=False),
        sa.Column("desktop_device_id", sa.String(length=128), nullable=False),
        sa.Column("command_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("risk_level", sa.String(length=40), nullable=False, server_default="l3"),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="queued"),
        sa.Column("route_id", sa.CHAR(length=36), nullable=True),
        sa.Column("route_consumer_id", sa.String(length=160), nullable=True),
        sa.Column("route_scopes", sa.JSON(), nullable=False),
        sa.Column("second_confirmed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pairing_id"], ["remote_control_pairings.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_remote_control_commands_org_status",
        "remote_control_commands",
        ["org_id", "status"],
    )
    op.create_index(
        "ix_remote_control_commands_pairing",
        "remote_control_commands",
        ["pairing_id"],
    )
    op.create_index(
        "ix_remote_control_commands_desktop_status",
        "remote_control_commands",
        ["desktop_device_id", "status"],
    )

    op.create_table(
        "remote_control_audit_events",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("user_id", sa.CHAR(length=36), nullable=True),
        sa.Column("pairing_id", sa.CHAR(length=36), nullable=True),
        sa.Column("command_id", sa.CHAR(length=36), nullable=True),
        sa.Column("actor_type", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="success"),
        sa.Column("reason_code", sa.String(length=100), nullable=False),
        sa.Column("resource_snapshot", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_remote_control_audit_events_org_created",
        "remote_control_audit_events",
        ["org_id", "created_at"],
    )
    op.create_index(
        "ix_remote_control_audit_events_action_status",
        "remote_control_audit_events",
        ["action", "status"],
    )
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_remote_control_audit_events_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'remote_control_audit_events is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER tr_remote_control_audit_events_no_update_delete
            BEFORE UPDATE OR DELETE ON remote_control_audit_events
            FOR EACH ROW EXECUTE FUNCTION prevent_remote_control_audit_events_mutation();
            """
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS tr_remote_control_audit_events_no_update_delete ON remote_control_audit_events")
        op.execute("DROP FUNCTION IF EXISTS prevent_remote_control_audit_events_mutation()")

    op.drop_index("ix_remote_control_audit_events_action_status", table_name="remote_control_audit_events")
    op.drop_index("ix_remote_control_audit_events_org_created", table_name="remote_control_audit_events")
    op.drop_table("remote_control_audit_events")

    op.drop_index("ix_remote_control_commands_desktop_status", table_name="remote_control_commands")
    op.drop_index("ix_remote_control_commands_pairing", table_name="remote_control_commands")
    op.drop_index("ix_remote_control_commands_org_status", table_name="remote_control_commands")
    op.drop_table("remote_control_commands")

    op.drop_index("ix_remote_control_pairings_user_desktop", table_name="remote_control_pairings")
    op.drop_index("ix_remote_control_pairings_org_status", table_name="remote_control_pairings")
    op.drop_table("remote_control_pairings")
