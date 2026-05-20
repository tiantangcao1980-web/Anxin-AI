"""Agent governance control-plane model and migration regressions."""

import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, create_engine, insert
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.exc import IntegrityError

from src.models import (
    AgentApproval,
    AgentAuditEvent,
    AgentChannelPolicy,
    AgentManager,
    AgentTeam,
    AgentWorker,
    Base,
    CapabilityRoute,
    CapabilityRouteTokenLease,
    HumanParticipant,
    Organization,
    User,
)
from src.models.agent_governance import _reject_agent_audit_event_mutation

EXPECTED_TABLES = {
    "agent_managers",
    "agent_teams",
    "agent_workers",
    "human_participants",
    "agent_channel_policies",
    "capability_routes",
    "capability_route_token_leases",
    "agent_approvals",
    "agent_audit_events",
}

RAW_SECRET_COLUMN_NAMES = {
    "api_key",
    "api_secret",
    "client_secret",
    "credential",
    "password",
    "provider_secret",
    "provider_token",
    "raw_token",
    "secret",
    "token",
}

TENANT_SCOPED_TABLES = [
    Organization.__table__,
    User.__table__,
    AgentManager.__table__,
    AgentTeam.__table__,
    AgentWorker.__table__,
    HumanParticipant.__table__,
    AgentChannelPolicy.__table__,
    CapabilityRoute.__table__,
    CapabilityRouteTokenLease.__table__,
    AgentApproval.__table__,
    AgentAuditEvent.__table__,
]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_agent_governance_tables_are_registered_in_metadata():
    assert EXPECTED_TABLES <= set(Base.metadata.tables)
    assert AgentManager.__tablename__ == "agent_managers"
    assert AgentTeam.__tablename__ == "agent_teams"
    assert AgentWorker.__tablename__ == "agent_workers"
    assert HumanParticipant.__tablename__ == "human_participants"
    assert AgentChannelPolicy.__tablename__ == "agent_channel_policies"
    assert CapabilityRoute.__tablename__ == "capability_routes"
    assert CapabilityRouteTokenLease.__tablename__ == "capability_route_token_leases"
    assert AgentApproval.__tablename__ == "agent_approvals"
    assert AgentAuditEvent.__tablename__ == "agent_audit_events"


def test_capability_routes_are_org_scoped_and_do_not_store_provider_secrets():
    columns = set(CapabilityRoute.__table__.columns.keys())

    assert {
        "org_id",
        "route_key",
        "route_type",
        "provider",
        "allowed_consumers",
        "allowed_scopes",
        "token_ttl_seconds",
        "revoked_at",
        "revoked_reason",
    } <= columns
    assert columns.isdisjoint(RAW_SECRET_COLUMN_NAMES)
    assert "token_hash" not in columns
    assert CapabilityRoute.__table__.c.allowed_consumers.default is not None
    assert CapabilityRoute.__table__.c.allowed_scopes.default is not None

    unique_constraints = [
        constraint
        for constraint in CapabilityRoute.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    assert any(
        constraint.name == "uq_capability_routes_org_key"
        and {column.name for column in constraint.columns} == {"org_id", "route_key"}
        for constraint in unique_constraints
    )


def test_capability_route_token_leases_persist_only_hashed_lease_state():
    columns = set(CapabilityRouteTokenLease.__table__.columns.keys())

    assert {
        "org_id",
        "route_id",
        "consumer_id",
        "consumer_type",
        "token_hash",
        "scopes",
        "expires_at",
        "last_validated_at",
        "revoked_at",
        "revoked_reason",
    } <= columns
    assert columns.isdisjoint(RAW_SECRET_COLUMN_NAMES)


def test_agent_approval_and_audit_events_keep_tenant_and_route_context():
    approval_columns = set(AgentApproval.__table__.columns.keys())
    audit_columns = set(AgentAuditEvent.__table__.columns.keys())

    assert {
        "org_id",
        "route_id",
        "requested_by",
        "decided_by",
        "status",
        "expires_at",
    } <= approval_columns
    assert {
        "org_id",
        "team_id",
        "worker_id",
        "route_id",
        "human_participant_id",
        "actor_user_id",
        "actor_snapshot",
        "action",
        "status",
        "reason_code",
        "resource_snapshot",
        "metadata",
        "created_at",
    } <= audit_columns
    assert "updated_at" not in audit_columns
    assert AgentAuditEvent.__table__.c.created_at.default is not None
    assert sqlalchemy_event.contains(
        AgentAuditEvent,
        "before_update",
        _reject_agent_audit_event_mutation,
    )
    assert sqlalchemy_event.contains(
        AgentAuditEvent,
        "before_delete",
        _reject_agent_audit_event_mutation,
    )


def test_agent_channel_policy_defaults_are_fail_closed_contract_inputs():
    columns = AgentChannelPolicy.__table__.columns

    assert columns.view_policy.default is not None
    assert columns.speak_policy.default is not None
    assert columns.assign_policy.default is not None
    assert columns.takeover_policy.default is not None


def test_governance_relationships_use_composite_org_scoped_foreign_keys():
    expected = {
        AgentTeam: ("org_id", "manager_id", "agent_managers"),
        AgentWorker: ("org_id", "team_id", "agent_teams"),
        HumanParticipant: ("org_id", "team_id", "agent_teams"),
        AgentChannelPolicy: ("org_id", "team_id", "agent_teams"),
        CapabilityRouteTokenLease: ("org_id", "route_id", "capability_routes"),
        AgentApproval: ("org_id", "route_id", "capability_routes"),
        AgentAuditEvent: ("org_id", "route_id", "capability_routes"),
    }

    for model, (org_column, scoped_column, referred_table) in expected.items():
        composite_constraints = [
            constraint
            for constraint in model.__table__.constraints
            if isinstance(constraint, ForeignKeyConstraint)
            and {column.name for column in constraint.columns} == {org_column, scoped_column}
        ]
        assert composite_constraints, f"{model.__name__} lacks a composite org-scoped FK"
        assert referred_table in {
            element.column.table.name for element in composite_constraints[0].elements
        }


def test_cross_org_governance_links_fail_database_integrity():
    engine = create_engine("sqlite:///:memory:")

    @sqlalchemy_event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine, tables=TENANT_SCOPED_TABLES)

    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())
    manager_b = str(uuid.uuid4())
    team_b = str(uuid.uuid4())
    worker_b = str(uuid.uuid4())
    route_b = str(uuid.uuid4())
    human_b = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(
            insert(Organization),
            [
                {"id": org_a, "name": "Org A", "is_active": True},
                {"id": org_b, "name": "Org B", "is_active": True},
            ],
        )
        conn.execute(insert(AgentManager).values(id=manager_b, org_id=org_b, name="Manager B"))
        conn.execute(
            insert(AgentTeam).values(id=team_b, org_id=org_b, manager_id=manager_b, name="Team B")
        )
        conn.execute(
            insert(AgentWorker).values(id=worker_b, org_id=org_b, team_id=team_b, name="Worker B")
        )
        conn.execute(
            insert(CapabilityRoute).values(
                id=route_b,
                org_id=org_b,
                route_key="approved-mcp",
                route_type="mcp",
                allowed_consumers=["worker-b"],
                allowed_scopes=["mcp:call"],
            )
        )
        conn.execute(insert(HumanParticipant).values(id=human_b, org_id=org_b, team_id=team_b))

    invalid_rows = [
        (
            AgentTeam,
            {"id": str(uuid.uuid4()), "org_id": org_a, "manager_id": manager_b, "name": "Bad Team"},
        ),
        (
            AgentWorker,
            {"id": str(uuid.uuid4()), "org_id": org_a, "team_id": team_b, "name": "Bad Worker"},
        ),
        (
            AgentApproval,
            {
                "id": str(uuid.uuid4()),
                "org_id": org_a,
                "route_id": route_b,
                "action_type": "mcp.call",
            },
        ),
        (
            AgentAuditEvent,
            {
                "id": str(uuid.uuid4()),
                "org_id": org_a,
                "route_id": route_b,
                "worker_id": worker_b,
                "human_participant_id": human_b,
                "action": "mcp.call",
            },
        ),
    ]

    for model, values in invalid_rows:
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(insert(model).values(**values))


def test_agent_governance_migration_has_upgrade_downgrade_and_no_secret_columns():
    migration = (
        _repo_root()
        / "backend"
        / "alembic"
        / "versions"
        / "040_add_agent_governance_control_plane.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "040_agent_governance_control_plane"' in migration
    assert 'down_revision: str | None = "039_search_cache_org_scope"' in migration
    assert "def upgrade() -> None:" in migration
    assert "def downgrade() -> None:" in migration
    assert "CREATE TRIGGER tr_agent_audit_events_no_update_delete" in migration
    assert "prevent_agent_audit_events_mutation" in migration

    for table in EXPECTED_TABLES:
        assert f'"{table}"' in migration
        assert f'op.drop_table("{table}")' in migration

    column_names = set(re.findall(r'sa\.Column\("([^"]+)"', migration))
    assert column_names.isdisjoint(RAW_SECRET_COLUMN_NAMES)
    assert "token_hash" in column_names
    assert "raw_token" not in column_names
