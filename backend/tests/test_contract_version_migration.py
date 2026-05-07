import importlib
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_contract_version_migration_creates_snapshot_table_and_downgrades(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "036_add_contract_versions.py"
    )
    spec = importlib.util.spec_from_file_location("migration_036_contract_versions", migration_path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("users", metadata, sa.Column("id", sa.String, primary_key=True))
    sa.Table("contracts", metadata, sa.Column("id", sa.String, primary_key=True))

    with engine.begin() as conn:
        metadata.create_all(conn)
        operations = Operations(MigrationContext.configure(conn))
        monkeypatch.setattr(migration, "op", operations)

        migration.upgrade()

        contract_columns = {column["name"] for column in sa.inspect(conn).get_columns("contracts")}
        version_columns = {
            column["name"]
            for column in sa.inspect(conn).get_columns("contract_versions")
        }
        assert "version" in contract_columns
        assert {"contract_id", "version", "text", "source", "created_by"} <= version_columns

        conn.execute(sa.text("INSERT INTO users (id) VALUES ('user-1')"))
        conn.execute(sa.text("INSERT INTO contracts (id, version) VALUES ('contract-1', 1)"))
        conn.execute(
            sa.text(
                """
                INSERT INTO contract_versions
                    (id, contract_id, version, text, source, created_by)
                VALUES
                    ('version-1', 'contract-1', 1, '合同正文', 'baseline', 'user-1')
                """
            )
        )

        row = conn.execute(sa.text("SELECT text FROM contract_versions")).scalar_one()
        assert row == "合同正文"

        migration.downgrade()

        contract_columns = {column["name"] for column in sa.inspect(conn).get_columns("contracts")}
        assert "version" not in contract_columns
        assert not sa.inspect(conn).has_table("contract_versions")
