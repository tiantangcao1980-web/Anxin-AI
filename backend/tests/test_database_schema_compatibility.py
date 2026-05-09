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


@pytest.mark.asyncio
async def test_ensure_additive_schema_columns_repairs_user_login_columns(
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

    expected_user_columns = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT false",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS department VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS user_type VARCHAR(30) DEFAULT 'internal' NOT NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS wechat_openid VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS wechat_unionid VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS alipay_user_id VARCHAR(100)",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS login_type VARCHAR(20) DEFAULT 'email' NOT NULL",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_profile JSONB DEFAULT '{}'",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS primary_client VARCHAR(20) DEFAULT 'needer' NOT NULL",
    ]

    for statement in expected_user_columns:
        assert statement in connection.executed_statements


@pytest.mark.asyncio
async def test_api_lifespan_fails_fast_when_database_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
):
    from src.api import main as api_main

    async def fail_init_db() -> None:
        raise RuntimeError("users.department missing")

    monkeypatch.setattr(api_main, "init_db", fail_init_db)

    with pytest.raises(RuntimeError, match="users.department missing"):
        async with api_main.lifespan(api_main.app):
            pass
