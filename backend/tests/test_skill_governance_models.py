"""Skill governance persistence model and migration regressions."""

import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint, create_engine, insert
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.exc import IntegrityError

from src.models import (
    Base,
    Organization,
    SkillConnectorConfig,
    SkillEnabledVersion,
    SkillGovernanceAuditEvent,
    SkillGovernanceProposal,
)
from src.models.agent_governance import _reject_skill_governance_audit_event_mutation

EXPECTED_SKILL_GOVERNANCE_TABLES = {
    "skill_governance_proposals",
    "skill_connector_configs",
    "skill_enabled_versions",
    "skill_governance_audit_events",
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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_skill_governance_tables_are_registered_in_metadata():
    assert EXPECTED_SKILL_GOVERNANCE_TABLES <= set(Base.metadata.tables)
    assert SkillGovernanceProposal.__tablename__ == "skill_governance_proposals"
    assert SkillConnectorConfig.__tablename__ == "skill_connector_configs"
    assert SkillEnabledVersion.__tablename__ == "skill_enabled_versions"
    assert SkillGovernanceAuditEvent.__tablename__ == "skill_governance_audit_events"


def test_skill_governance_tables_are_org_scoped_and_secret_free():
    proposal_columns = set(SkillGovernanceProposal.__table__.columns.keys())
    connector_columns = set(SkillConnectorConfig.__table__.columns.keys())
    enabled_columns = set(SkillEnabledVersion.__table__.columns.keys())
    audit_columns = set(SkillGovernanceAuditEvent.__table__.columns.keys())

    assert {
        "org_id",
        "skill_name",
        "connector_name",
        "connector_type",
        "endpoint_url",
        "auth_type",
        "encrypted_fields",
        "is_enabled",
        "created_by",
        "updated_by",
    } <= connector_columns
    assert {
        "org_id",
        "skill_name",
        "current_version",
        "proposed_version",
        "status",
        "eval_results",
        "approved_by",
        "gray_percentage",
        "rolled_back_at",
    } <= proposal_columns
    assert {
        "org_id",
        "skill_name",
        "version",
        "status",
        "proposal_id",
        "enabled_at",
    } <= enabled_columns
    assert {
        "org_id",
        "proposal_id",
        "actor",
        "action",
        "status",
        "reason_code",
        "resource_snapshot",
        "metadata",
        "created_at",
    } <= audit_columns
    assert proposal_columns.isdisjoint(RAW_SECRET_COLUMN_NAMES)
    assert connector_columns.isdisjoint(RAW_SECRET_COLUMN_NAMES)
    assert enabled_columns.isdisjoint(RAW_SECRET_COLUMN_NAMES)
    assert audit_columns.isdisjoint(RAW_SECRET_COLUMN_NAMES)

    connector_unique_constraints = [
        constraint
        for constraint in SkillConnectorConfig.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    assert any(
        constraint.name == "uq_skill_connector_configs_org_skill_connector"
        and {column.name for column in constraint.columns}
        == {"org_id", "skill_name", "connector_name"}
        for constraint in connector_unique_constraints
    )

    unique_constraints = [
        constraint
        for constraint in SkillEnabledVersion.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]
    assert any(
        constraint.name == "uq_skill_enabled_versions_org_skill"
        and {column.name for column in constraint.columns} == {"org_id", "skill_name"}
        for constraint in unique_constraints
    )


def test_skill_governance_relationships_use_composite_org_scoped_foreign_keys():
    expected = {
        SkillEnabledVersion: ("org_id", "proposal_id", "skill_governance_proposals"),
        SkillGovernanceAuditEvent: ("org_id", "proposal_id", "skill_governance_proposals"),
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


def test_skill_governance_audit_events_are_append_only():
    audit_columns = set(SkillGovernanceAuditEvent.__table__.columns.keys())

    assert "updated_at" not in audit_columns
    assert SkillGovernanceAuditEvent.__table__.c.created_at.default is not None
    assert sqlalchemy_event.contains(
        SkillGovernanceAuditEvent,
        "before_update",
        _reject_skill_governance_audit_event_mutation,
    )
    assert sqlalchemy_event.contains(
        SkillGovernanceAuditEvent,
        "before_delete",
        _reject_skill_governance_audit_event_mutation,
    )


def test_cross_org_skill_governance_links_fail_database_integrity():
    engine = create_engine("sqlite:///:memory:")

    @sqlalchemy_event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(
        engine,
        tables=[
            Organization.__table__,
            SkillGovernanceProposal.__table__,
            SkillConnectorConfig.__table__,
            SkillEnabledVersion.__table__,
            SkillGovernanceAuditEvent.__table__,
        ],
    )

    org_a = str(uuid.uuid4())
    org_b = str(uuid.uuid4())
    proposal_b = str(uuid.uuid4())

    with engine.begin() as conn:
        conn.execute(
            insert(Organization),
            [
                {"id": org_a, "name": "Org A", "is_active": True},
                {"id": org_b, "name": "Org B", "is_active": True},
            ],
        )
        conn.execute(
            insert(SkillGovernanceProposal).values(
                id=proposal_b,
                org_id=org_b,
                skill_name="contract-review",
                current_version="1.0.0",
                proposed_version="1.1.0",
                source="eval:nightly",
                created_by="agent-1",
                created_by_role="agent",
                risk_level="medium",
                status="draft",
                eval_results={},
            )
        )

    invalid_rows = [
        (
            SkillEnabledVersion,
            {
                "id": str(uuid.uuid4()),
                "org_id": org_a,
                "skill_name": "contract-review",
                "version": "1.1.0",
                "status": "enabled",
                "proposal_id": proposal_b,
            },
        ),
        (
            SkillGovernanceAuditEvent,
            {
                "id": str(uuid.uuid4()),
                "org_id": org_a,
                "proposal_id": proposal_b,
                "actor": "release-manager",
                "action": "skill_governance.release.gray",
                "status": "success",
                "reason_code": "gray_released",
            },
        ),
    ]

    for model, values in invalid_rows:
        with pytest.raises(IntegrityError):
            with engine.begin() as conn:
                conn.execute(insert(model).values(**values))


def test_skill_governance_migration_has_upgrade_downgrade_and_no_secret_columns():
    migration = (
        _repo_root()
        / "backend"
        / "alembic"
        / "versions"
        / "041_add_skill_governance_persistence.py"
    ).read_text(encoding="utf-8")
    connector_migration = (
        _repo_root() / "backend" / "alembic" / "versions" / "044_add_skill_connector_configs.py"
    ).read_text(encoding="utf-8")

    assert 'revision: str = "041_skill_governance_persistence"' in migration
    assert 'down_revision: str | None = "040_agent_governance_control_plane"' in migration
    assert "def upgrade() -> None:" in migration
    assert "def downgrade() -> None:" in migration
    assert "CREATE TRIGGER tr_skill_governance_audit_events_no_update_delete" in migration
    assert "prevent_skill_governance_audit_events_mutation" in migration

    for table in EXPECTED_SKILL_GOVERNANCE_TABLES:
        source = connector_migration if table == "skill_connector_configs" else migration
        assert f'"{table}"' in source
        assert f'op.drop_table("{table}")' in source

    column_names = set(re.findall(r'sa\.Column\("([^"]+)"', migration))
    column_names |= set(re.findall(r'sa\.Column\("([^"]+)"', connector_migration))
    assert column_names.isdisjoint(RAW_SECRET_COLUMN_NAMES)
