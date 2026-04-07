"""
数据库结构兼容性测试
"""

from types import SimpleNamespace

import pytest

from src.core import database


class _CaptureConnection:
    def __init__(self) -> None:
        self.executed_statements: list[str] = []

    async def execute(self, statement) -> None:
        self.executed_statements.append(str(statement))


class _BeginContext:
    def __init__(self, connection: _CaptureConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> _CaptureConnection:
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@pytest.mark.asyncio
async def test_ensure_additive_schema_columns_adds_contract_text_fields(monkeypatch: pytest.MonkeyPatch):
    connection = _CaptureConnection()

    monkeypatch.setattr(database.settings, "DATABASE_URL", "postgresql://test", raising=False)
    monkeypatch.setattr(
        database,
        "engine",
        SimpleNamespace(begin=lambda: _BeginContext(connection)),
    )

    await database._ensure_additive_schema_columns()

    assert "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS original_text TEXT" in connection.executed_statements
    assert "ALTER TABLE contracts ADD COLUMN IF NOT EXISTS modified_text TEXT" in connection.executed_statements


@pytest.mark.asyncio
async def test_ensure_additive_schema_columns_adds_knowledge_document_fields(
    monkeypatch: pytest.MonkeyPatch,
):
    connection = _CaptureConnection()

    monkeypatch.setattr(database.settings, "DATABASE_URL", "postgresql://test", raising=False)
    monkeypatch.setattr(
        database,
        "engine",
        SimpleNamespace(begin=lambda: _BeginContext(connection)),
    )

    await database._ensure_additive_schema_columns()

    assert "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS external_id VARCHAR(255)" in connection.executed_statements
    assert "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64)" in connection.executed_statements
    assert "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS version INTEGER DEFAULT 1 NOT NULL" in connection.executed_statements
    assert "ALTER TABLE knowledge_documents ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active' NOT NULL" in connection.executed_statements
    assert "CREATE INDEX IF NOT EXISTS ix_knowledge_documents_external_id ON knowledge_documents (external_id)" in connection.executed_statements
