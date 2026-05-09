"""Durable agent governance control-plane models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import GUID, Base, TimestampMixin


class AgentManager(Base, TimestampMixin):
    """Organization or project level agent coordinator."""

    __tablename__ = "agent_managers"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False, default="organization")
    scope_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    policy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("ix_agent_managers_org_status", "org_id", "status"),
        UniqueConstraint("org_id", "id", name="uq_agent_managers_org_id"),
        UniqueConstraint("org_id", "name", name="uq_agent_managers_org_name"),
    )


class AgentTeam(Base, TimestampMixin):
    """Governed group of workers scoped to a department, project, or client matter."""

    __tablename__ = "agent_teams"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    manager_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False, default="project")
    scope_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    data_scope: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    visibility_policy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "manager_id"],
            ["agent_managers.org_id", "agent_managers.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_agent_teams_org_status", "org_id", "status"),
        UniqueConstraint("org_id", "id", name="uq_agent_teams_org_id"),
        UniqueConstraint("org_id", "name", name="uq_agent_teams_org_name"),
    )


class AgentWorker(Base, TimestampMixin):
    """Concrete execution unit that consumes governed capability routes."""

    __tablename__ = "agent_workers"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    worker_type: Mapped[str] = mapped_column(String(60), nullable=False, default="assistant")
    runtime: Mapped[str] = mapped_column(String(80), nullable=False, default="server")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="l1")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    capability_scope: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    policy_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_agent_workers_org_status", "org_id", "status"),
        Index("ix_agent_workers_team", "team_id"),
        UniqueConstraint("org_id", "id", name="uq_agent_workers_org_id"),
    )


class HumanParticipant(Base, TimestampMixin):
    """Human participant in a governed agent workspace."""

    __tablename__ = "human_participants"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    external_subject_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    participant_type: Mapped[str] = mapped_column(String(40), nullable=False, default="employee")
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    visibility_scope: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_human_participants_team", "team_id"),
        Index("ix_human_participants_user", "user_id"),
        UniqueConstraint("org_id", "id", name="uq_human_participants_org_id"),
    )


class AgentChannelPolicy(Base, TimestampMixin):
    """Declarative visibility and action policy for an agent workspace channel."""

    __tablename__ = "agent_channel_policies"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    team_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False, default="workspace")
    channel_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    view_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    speak_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    assign_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    takeover_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_agent_channel_policies_org_status", "org_id", "status"),
        Index("ix_agent_channel_policies_team", "team_id"),
    )


class CapabilityRoute(Base, TimestampMixin):
    """Durable capability route contract without storing raw provider credentials."""

    __tablename__ = "capability_routes"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    route_key: Mapped[str] = mapped_column(String(160), nullable=False)
    route_type: Mapped[str] = mapped_column(String(60), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="l1")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="disabled")
    allowed_consumers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    policy: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    token_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("org_id", "route_key", name="uq_capability_routes_org_key"),
        UniqueConstraint("org_id", "id", name="uq_capability_routes_org_id"),
        Index("ix_capability_routes_org_status", "org_id", "status"),
        Index("ix_capability_routes_type_risk", "route_type", "risk_level"),
    )


class CapabilityRouteTokenLease(Base, TimestampMixin):
    """Issued route-token lease state; raw tokens are never persisted."""

    __tablename__ = "capability_route_token_leases"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    route_id: Mapped[str] = mapped_column(GUID(), nullable=False)
    consumer_id: Mapped[str] = mapped_column(String(160), nullable=False)
    consumer_type: Mapped[str] = mapped_column(String(60), nullable=False, default="agent_worker")
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "route_id"],
            ["capability_routes.org_id", "capability_routes.id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("org_id", "token_hash", name="uq_capability_route_token_leases_org_hash"),
        Index("ix_capability_route_token_leases_route", "route_id"),
        Index("ix_capability_route_token_leases_expires_at", "expires_at"),
        Index("ix_capability_route_token_leases_consumer", "org_id", "consumer_type", "consumer_id"),
    )


class AgentApproval(Base, TimestampMixin):
    """Approval request for high-risk agent actions."""

    __tablename__ = "agent_approvals"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    route_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action_type: Mapped[str] = mapped_column(String(80), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="l3")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="pending")
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "route_id"],
            ["capability_routes.org_id", "capability_routes.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_agent_approvals_org_status", "org_id", "status"),
        Index("ix_agent_approvals_route", "route_id"),
        Index("ix_agent_approvals_expires_at", "expires_at"),
    )


class AgentAuditEvent(Base):
    """Append-only audit event for governed agent control-plane actions."""

    __tablename__ = "agent_audit_events"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    team_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    route_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    human_participant_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    actor_user_id: Mapped[str | None] = mapped_column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False, default="system")
    actor_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="success")
    reason_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    resource_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "team_id"],
            ["agent_teams.org_id", "agent_teams.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "worker_id"],
            ["agent_workers.org_id", "agent_workers.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "route_id"],
            ["capability_routes.org_id", "capability_routes.id"],
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["org_id", "human_participant_id"],
            ["human_participants.org_id", "human_participants.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_agent_audit_events_org_created", "org_id", "created_at"),
        Index("ix_agent_audit_events_action_status", "action", "status"),
        Index("ix_agent_audit_events_route", "route_id"),
    )


def _reject_agent_audit_event_mutation(*_args: object) -> None:
    raise ValueError("agent_audit_events is append-only")


event.listen(AgentAuditEvent, "before_update", _reject_agent_audit_event_mutation)
event.listen(AgentAuditEvent, "before_delete", _reject_agent_audit_event_mutation)


class SkillGovernanceProposal(Base, TimestampMixin):
    """Durable proposal record for governed Skill evolution."""

    __tablename__ = "skill_governance_proposals"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(160), nullable=False)
    current_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    proposed_version: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    created_by: Mapped[str] = mapped_column(String(160), nullable=False)
    created_by_role: Mapped[str] = mapped_column(String(60), nullable=False, default="agent")
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")
    eval_results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    approved_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    approver_role: Mapped[str | None] = mapped_column(String(60), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gray_percentage: Mapped[int | None] = mapped_column(Integer, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rollback_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("org_id", "id", name="uq_skill_governance_proposals_org_id"),
        UniqueConstraint("org_id", "skill_name", "proposed_version", name="uq_skill_governance_proposals_org_version"),
        Index("ix_skill_governance_proposals_org_status", "org_id", "status"),
        Index("ix_skill_governance_proposals_skill", "org_id", "skill_name"),
    )


class SkillEnabledVersion(Base, TimestampMixin):
    """Org-scoped enabled Skill version selected by governance."""

    __tablename__ = "skill_enabled_versions"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(160), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="enabled")
    proposal_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    enabled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "proposal_id"],
            ["skill_governance_proposals.org_id", "skill_governance_proposals.id"],
            ondelete="RESTRICT",
        ),
        UniqueConstraint("org_id", "skill_name", name="uq_skill_enabled_versions_org_skill"),
        Index("ix_skill_enabled_versions_org_status", "org_id", "status"),
    )


class SkillConnectorConfig(Base, TimestampMixin):
    """Org-scoped Skill connector configuration with encrypted credential values."""

    __tablename__ = "skill_connector_configs"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(160), nullable=False)
    connector_name: Mapped[str] = mapped_column(String(120), nullable=False)
    connector_type: Mapped[str] = mapped_column(String(60), nullable=False, default="http_api")
    endpoint_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    auth_type: Mapped[str] = mapped_column(String(40), nullable=False, default="api_key")
    encrypted_fields: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(String(160), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(160), nullable=True)

    __table_args__ = (
        UniqueConstraint("org_id", "id", name="uq_skill_connector_configs_org_id"),
        UniqueConstraint(
            "org_id",
            "skill_name",
            "connector_name",
            name="uq_skill_connector_configs_org_skill_connector",
        ),
        Index("ix_skill_connector_configs_org_skill", "org_id", "skill_name"),
        Index("ix_skill_connector_configs_org_enabled", "org_id", "is_enabled"),
    )


class SkillGovernanceAuditEvent(Base):
    """Append-only audit event for governed Skill lifecycle decisions."""

    __tablename__ = "skill_governance_audit_events"

    org_id: Mapped[str] = mapped_column(GUID(), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    proposal_id: Mapped[str | None] = mapped_column(GUID(), nullable=True)
    actor: Mapped[str] = mapped_column(String(160), nullable=False)
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="success")
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["org_id", "proposal_id"],
            ["skill_governance_proposals.org_id", "skill_governance_proposals.id"],
            ondelete="RESTRICT",
        ),
        Index("ix_skill_governance_audit_events_org_created", "org_id", "created_at"),
        Index("ix_skill_governance_audit_events_action_status", "action", "status"),
    )


def _reject_skill_governance_audit_event_mutation(*_args: object) -> None:
    raise ValueError("skill_governance_audit_events is append-only")


event.listen(SkillGovernanceAuditEvent, "before_update", _reject_skill_governance_audit_event_mutation)
event.listen(SkillGovernanceAuditEvent, "before_delete", _reject_skill_governance_audit_event_mutation)
