"""add agent governance control-plane tables

Revision ID: 040_agent_governance_control_plane
Revises: 039_search_cache_org_scope
Create Date: 2026-05-08
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "040_agent_governance_control_plane"
down_revision: str | None = "039_search_cache_org_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamp_columns() -> list[sa.Column[Any]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "agent_managers",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("owner_user_id", sa.CHAR(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False, server_default="organization"),
        sa.Column("scope_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("policy", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_agent_managers_org_id"),
        sa.UniqueConstraint("org_id", "name", name="uq_agent_managers_org_name"),
    )
    op.create_index("ix_agent_managers_org_status", "agent_managers", ["org_id", "status"])

    op.create_table(
        "agent_teams",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("manager_id", sa.CHAR(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False, server_default="project"),
        sa.Column("scope_id", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("data_scope", sa.JSON(), nullable=True),
        sa.Column("visibility_policy", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id", "manager_id"],
            ["agent_managers.org_id", "agent_managers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_agent_teams_org_id"),
        sa.UniqueConstraint("org_id", "name", name="uq_agent_teams_org_name"),
    )
    op.create_index("ix_agent_teams_org_status", "agent_teams", ["org_id", "status"])

    op.create_table(
        "agent_workers",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("team_id", sa.CHAR(length=36), nullable=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("worker_type", sa.String(length=60), nullable=False, server_default="assistant"),
        sa.Column("runtime", sa.String(length=80), nullable=False, server_default="server"),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="l1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("capability_scope", sa.JSON(), nullable=True),
        sa.Column("policy_snapshot", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_agent_workers_org_id"),
    )
    op.create_index("ix_agent_workers_org_status", "agent_workers", ["org_id", "status"])
    op.create_index("ix_agent_workers_team", "agent_workers", ["team_id"])

    op.create_table(
        "human_participants",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("team_id", sa.CHAR(length=36), nullable=True),
        sa.Column("user_id", sa.CHAR(length=36), nullable=True),
        sa.Column("external_subject_id", sa.String(length=120), nullable=True),
        sa.Column("participant_type", sa.String(length=40), nullable=False, server_default="employee"),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="viewer"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("visibility_scope", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_human_participants_org_id"),
    )
    op.create_index("ix_human_participants_team", "human_participants", ["team_id"])
    op.create_index("ix_human_participants_user", "human_participants", ["user_id"])

    op.create_table(
        "agent_channel_policies",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("team_id", sa.CHAR(length=36), nullable=True),
        sa.Column("channel_type", sa.String(length=50), nullable=False, server_default="workspace"),
        sa.Column("channel_id", sa.String(length=120), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="active"),
        sa.Column("view_policy", sa.JSON(), nullable=False),
        sa.Column("speak_policy", sa.JSON(), nullable=False),
        sa.Column("assign_policy", sa.JSON(), nullable=False),
        sa.Column("takeover_policy", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_channel_policies_org_status", "agent_channel_policies", ["org_id", "status"])
    op.create_index("ix_agent_channel_policies_team", "agent_channel_policies", ["team_id"])

    op.create_table(
        "capability_routes",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("route_key", sa.String(length=160), nullable=False),
        sa.Column("route_type", sa.String(length=60), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="l1"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="disabled"),
        sa.Column("allowed_consumers", sa.JSON(), nullable=False),
        sa.Column("allowed_scopes", sa.JSON(), nullable=False),
        sa.Column("policy", sa.JSON(), nullable=True),
        sa.Column("token_ttl_seconds", sa.Integer(), nullable=False, server_default="900"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "id", name="uq_capability_routes_org_id"),
        sa.UniqueConstraint("org_id", "route_key", name="uq_capability_routes_org_key"),
    )
    op.create_index("ix_capability_routes_org_status", "capability_routes", ["org_id", "status"])
    op.create_index("ix_capability_routes_type_risk", "capability_routes", ["route_type", "risk_level"])

    op.create_table(
        "capability_route_token_leases",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("route_id", sa.CHAR(length=36), nullable=False),
        sa.Column("consumer_id", sa.String(length=160), nullable=False),
        sa.Column("consumer_type", sa.String(length=60), nullable=False, server_default="agent_worker"),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("scopes", sa.JSON(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id", "route_id"],
            ["capability_routes.org_id", "capability_routes.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "token_hash", name="uq_capability_route_token_leases_org_hash"),
    )
    op.create_index("ix_capability_route_token_leases_route", "capability_route_token_leases", ["route_id"])
    op.create_index("ix_capability_route_token_leases_expires_at", "capability_route_token_leases", ["expires_at"])
    op.create_index(
        "ix_capability_route_token_leases_consumer",
        "capability_route_token_leases",
        ["org_id", "consumer_type", "consumer_id"],
    )

    op.create_table(
        "agent_approvals",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        *_timestamp_columns(),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("route_id", sa.CHAR(length=36), nullable=True),
        sa.Column("requested_by", sa.CHAR(length=36), nullable=True),
        sa.Column("decided_by", sa.CHAR(length=36), nullable=True),
        sa.Column("action_type", sa.String(length=80), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False, server_default="l3"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["org_id", "route_id"],
            ["capability_routes.org_id", "capability_routes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_approvals_org_status", "agent_approvals", ["org_id", "status"])
    op.create_index("ix_agent_approvals_route", "agent_approvals", ["route_id"])
    op.create_index("ix_agent_approvals_expires_at", "agent_approvals", ["expires_at"])

    op.create_table(
        "agent_audit_events",
        sa.Column("id", sa.CHAR(length=36), nullable=False),
        sa.Column("org_id", sa.CHAR(length=36), nullable=False),
        sa.Column("team_id", sa.CHAR(length=36), nullable=True),
        sa.Column("worker_id", sa.CHAR(length=36), nullable=True),
        sa.Column("route_id", sa.CHAR(length=36), nullable=True),
        sa.Column("human_participant_id", sa.CHAR(length=36), nullable=True),
        sa.Column("actor_user_id", sa.CHAR(length=36), nullable=True),
        sa.Column("actor_type", sa.String(length=50), nullable=False, server_default="system"),
        sa.Column("actor_snapshot", sa.JSON(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="success"),
        sa.Column("reason_code", sa.String(length=100), nullable=True),
        sa.Column("resource_type", sa.String(length=80), nullable=True),
        sa.Column("resource_id", sa.String(length=120), nullable=True),
        sa.Column("resource_snapshot", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "worker_id"],
            ["agent_workers.org_id", "agent_workers.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "route_id"],
            ["capability_routes.org_id", "capability_routes.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["org_id", "human_participant_id"],
            ["human_participants.org_id", "human_participants.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_audit_events_org_created", "agent_audit_events", ["org_id", "created_at"])
    op.create_index("ix_agent_audit_events_action_status", "agent_audit_events", ["action", "status"])
    op.create_index("ix_agent_audit_events_route", "agent_audit_events", ["route_id"])
    if op.get_context().dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION prevent_agent_audit_events_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'agent_audit_events is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER tr_agent_audit_events_no_update_delete
            BEFORE UPDATE OR DELETE ON agent_audit_events
            FOR EACH ROW EXECUTE FUNCTION prevent_agent_audit_events_mutation();
            """
        )


def downgrade() -> None:
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS tr_agent_audit_events_no_update_delete ON agent_audit_events")
        op.execute("DROP FUNCTION IF EXISTS prevent_agent_audit_events_mutation()")

    op.drop_index("ix_agent_audit_events_route", table_name="agent_audit_events")
    op.drop_index("ix_agent_audit_events_action_status", table_name="agent_audit_events")
    op.drop_index("ix_agent_audit_events_org_created", table_name="agent_audit_events")
    op.drop_table("agent_audit_events")

    op.drop_index("ix_agent_approvals_expires_at", table_name="agent_approvals")
    op.drop_index("ix_agent_approvals_route", table_name="agent_approvals")
    op.drop_index("ix_agent_approvals_org_status", table_name="agent_approvals")
    op.drop_table("agent_approvals")

    op.drop_index("ix_capability_routes_type_risk", table_name="capability_routes")
    op.drop_index("ix_capability_routes_org_status", table_name="capability_routes")
    op.drop_index("ix_capability_route_token_leases_consumer", table_name="capability_route_token_leases")
    op.drop_index("ix_capability_route_token_leases_expires_at", table_name="capability_route_token_leases")
    op.drop_index("ix_capability_route_token_leases_route", table_name="capability_route_token_leases")
    op.drop_table("capability_route_token_leases")
    op.drop_table("capability_routes")

    op.drop_index("ix_agent_channel_policies_team", table_name="agent_channel_policies")
    op.drop_index("ix_agent_channel_policies_org_status", table_name="agent_channel_policies")
    op.drop_table("agent_channel_policies")

    op.drop_index("ix_human_participants_user", table_name="human_participants")
    op.drop_index("ix_human_participants_team", table_name="human_participants")
    op.drop_table("human_participants")

    op.drop_index("ix_agent_workers_team", table_name="agent_workers")
    op.drop_index("ix_agent_workers_org_status", table_name="agent_workers")
    op.drop_table("agent_workers")

    op.drop_index("ix_agent_teams_org_status", table_name="agent_teams")
    op.drop_table("agent_teams")

    op.drop_index("ix_agent_managers_org_status", table_name="agent_managers")
    op.drop_table("agent_managers")
