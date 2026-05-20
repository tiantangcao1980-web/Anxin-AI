import importlib
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_document_object_storage_migration_backfills_and_downgrades(monkeypatch):
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "029_add_document_object_storage_fields.py"
    )
    spec = importlib.util.spec_from_file_location(
        "migration_029_document_object_storage", migration_path
    )
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    documents = sa.Table(
        "documents",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("file_path", sa.String(500), nullable=False),
    )
    versions = sa.Table(
        "document_versions",
        metadata,
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("document_id", sa.String, nullable=False),
        sa.Column("file_path", sa.String(500), nullable=False),
    )

    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            documents.insert(),
            {"id": "doc-1", "file_path": "documents/org-1/legacy.txt"},
        )
        conn.execute(
            versions.insert(),
            {
                "id": "ver-1",
                "document_id": "doc-1",
                "file_path": "documents/org-1/legacy-v1.txt",
            },
        )

        operations = Operations(MigrationContext.configure(conn))
        monkeypatch.setattr(migration, "op", operations)

        migration.upgrade()

        document_row = conn.execute(sa.text("SELECT * FROM documents")).mappings().one()
        version_row = conn.execute(sa.text("SELECT * FROM document_versions")).mappings().one()
        assert document_row["storage_backend"] == "local"
        assert document_row["object_key"] == "documents/org-1/legacy.txt"
        assert version_row["storage_backend"] == "local"
        assert version_row["object_key"] == "documents/org-1/legacy-v1.txt"

        migration.downgrade()

        document_columns = {column["name"] for column in sa.inspect(conn).get_columns("documents")}
        version_columns = {
            column["name"] for column in sa.inspect(conn).get_columns("document_versions")
        }
        assert "storage_backend" not in document_columns
        assert "object_key" not in document_columns
        assert "storage_backend" not in version_columns
        assert "object_key" not in version_columns
