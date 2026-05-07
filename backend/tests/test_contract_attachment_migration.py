import importlib
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_contract_attachment_migration_creates_table_and_downgrades(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "037_add_contract_attachments.py"
    )
    spec = importlib.util.spec_from_file_location("migration_037_contract_attachments", migration_path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table("organizations", metadata, sa.Column("id", sa.String, primary_key=True))
    sa.Table("users", metadata, sa.Column("id", sa.String, primary_key=True))
    sa.Table(
        "contracts",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("org_id", sa.String),
    )

    with engine.begin() as conn:
        metadata.create_all(conn)
        operations = Operations(MigrationContext.configure(conn))
        monkeypatch.setattr(migration, "op", operations)

        migration.upgrade()

        assert sa.inspect(conn).has_table("contract_attachments")
        columns = {column["name"] for column in sa.inspect(conn).get_columns("contract_attachments")}
        assert {
            "contract_id",
            "org_id",
            "original_filename",
            "content_type",
            "storage_backend",
            "object_key",
            "file_size",
            "file_hash",
            "uploaded_by",
        } <= columns

        conn.execute(sa.text("INSERT INTO organizations (id) VALUES ('org-1')"))
        conn.execute(sa.text("INSERT INTO users (id) VALUES ('user-1')"))
        conn.execute(sa.text("INSERT INTO contracts (id, org_id) VALUES ('contract-1', 'org-1')"))
        conn.execute(
            sa.text(
                """
                INSERT INTO contract_attachments
                    (
                        id, contract_id, org_id, original_filename, content_type,
                        storage_backend, object_key, file_size, file_hash, uploaded_by
                    )
                VALUES
                    (
                        'attachment-1', 'contract-1', 'org-1', '附件.txt', 'text/plain',
                        'local', 'contracts/org-1/contract-1/attachments/a.txt', 12,
                        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
                        'user-1'
                    )
                """
            )
        )

        row = conn.execute(sa.text("SELECT original_filename FROM contract_attachments")).scalar_one()
        assert row == "附件.txt"

        migration.downgrade()

        assert not sa.inspect(conn).has_table("contract_attachments")
