"""add governance tables (confirm_tickets, audit_events, shadow_runs)

Revision ID: 045_governance_tables
Revises: 044_skill_connector_configs
Create Date: 2026-05-14
"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "045_governance_tables"
down_revision: str | None = "044_skill_connector_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ts_cols() -> list[sa.Column[Any]]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # ────────────────────────────────────────────────────────────────
    # confirm_tickets — PEP-4 待人工 confirm 的外发 / 写动作
    # ────────────────────────────────────────────────────────────────
    op.create_table(
        "confirm_tickets",
        sa.Column("id", sa.String(length=64), nullable=False),
        *_ts_cols(),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=False),
        sa.Column("requester_id", sa.String(length=64), nullable=False),
        sa.Column("requester_role", sa.String(length=64), nullable=False),
        sa.Column("persona", sa.String(length=64), nullable=True),
        sa.Column("skill_id", sa.String(length=160), nullable=True),
        sa.Column("cookbook_name", sa.String(length=120), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=False),
        sa.Column("resource", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("context", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("decision_reasons", sa.JSON(), nullable=True, server_default=sa.text("'[]'")),
        sa.Column("policy_snapshot_id", sa.String(length=48), nullable=True),
        sa.Column("pending_action", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("draft_path", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("approver_id", sa.String(length=64), nullable=True),
        sa.Column("approver_role", sa.String(length=64), nullable=True),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_note", sa.Text(), nullable=True),
        sa.Column("cosigner_id", sa.String(length=64), nullable=True),
        sa.Column("cosigner_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("create_audit_event_id", sa.String(length=64), nullable=True),
        sa.Column("decision_audit_event_id", sa.String(length=64), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_confirm_tickets_tenant_status", "confirm_tickets", ["tenant_id", "status"])
    op.create_index("ix_confirm_tickets_persona_status", "confirm_tickets", ["persona", "status"])
    op.create_index("ix_confirm_tickets_tenant_id", "confirm_tickets", ["tenant_id"])
    op.create_index("ix_confirm_tickets_requester_id", "confirm_tickets", ["requester_id"])
    op.create_index("ix_confirm_tickets_persona", "confirm_tickets", ["persona"])
    op.create_index("ix_confirm_tickets_skill_id", "confirm_tickets", ["skill_id"])
    op.create_index("ix_confirm_tickets_cookbook_name", "confirm_tickets", ["cookbook_name"])
    op.create_index("ix_confirm_tickets_action", "confirm_tickets", ["action"])
    op.create_index("ix_confirm_tickets_status", "confirm_tickets", ["status"])
    op.create_index("ix_confirm_tickets_approver_id", "confirm_tickets", ["approver_id"])
    op.create_index("ix_confirm_tickets_create_audit_event_id", "confirm_tickets", ["create_audit_event_id"])

    # ────────────────────────────────────────────────────────────────
    # audit_events — JSONL 真相源 + DB 镜像
    # ────────────────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("actor_role", sa.String(length=64), nullable=True),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=True),
        sa.Column("action", sa.String(length=160), nullable=True),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=500), nullable=True),
        sa.Column("decision", sa.String(length=32), nullable=True),
        sa.Column("outcome", sa.String(length=32), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("policy_snapshot_id", sa.String(length=48), nullable=True),
        sa.Column("fingerprint", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", name="uq_audit_events_event_id"),
    )
    op.create_index("ix_audit_events_event_id", "audit_events", ["event_id"])
    op.create_index("ix_audit_events_ts", "audit_events", ["ts"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])
    op.create_index("ix_audit_events_trace_id", "audit_events", ["trace_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_resource_type", "audit_events", ["resource_type"])
    op.create_index("ix_audit_events_decision", "audit_events", ["decision"])
    op.create_index("ix_audit_events_outcome", "audit_events", ["outcome"])
    op.create_index("ix_audit_events_policy_snapshot_id", "audit_events", ["policy_snapshot_id"])
    op.create_index("ix_audit_events_actor_ts", "audit_events", ["actor_id", "ts"])
    op.create_index("ix_audit_events_action_ts", "audit_events", ["action", "ts"])
    op.create_index("ix_audit_events_decision_outcome", "audit_events", ["decision", "outcome"])

    # ────────────────────────────────────────────────────────────────
    # shadow_runs — REVIEW → PUBLISHED 24h 录制
    # ────────────────────────────────────────────────────────────────
    op.create_table(
        "shadow_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("skill_id", sa.String(length=160), nullable=False),
        sa.Column("review_version", sa.String(length=40), nullable=False),
        sa.Column("baseline_version", sa.String(length=40), nullable=True),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
        sa.Column("total_invocations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("baseline_errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("divergences", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("security_violations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_error_rate", sa.Float(), nullable=False, server_default="0.05"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("samples", sa.JSON(), nullable=True, server_default=sa.text("'[]'")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shadow_runs_skill_id", "shadow_runs", ["skill_id"])
    op.create_index("ix_shadow_runs_status", "shadow_runs", ["status"])
    op.create_index("ix_shadow_runs_skill_status", "shadow_runs", ["skill_id", "status"])


def downgrade() -> None:
    op.drop_table("shadow_runs")
    op.drop_table("audit_events")
    op.drop_table("confirm_tickets")
