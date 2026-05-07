import pytest

from src.core.config import Settings


def test_staging_rejects_default_jwt_secret():
    with pytest.raises(ValueError, match="生产/预发环境必须设置安全的 JWT_SECRET_KEY"):
        Settings(
            ENVIRONMENT="staging",
            JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-production",
            _env_file=None,
        )


def test_development_generates_jwt_secret_from_default():
    settings = Settings(
        ENVIRONMENT="development",
        JWT_SECRET_KEY="your-super-secret-jwt-key-change-in-production",
        _env_file=None,
    )

    assert settings.JWT_SECRET_KEY != "your-super-secret-jwt-key-change-in-production"


def test_standalone_mcp_is_disabled_in_staging_by_default(monkeypatch):
    from src import mcp_server

    monkeypatch.setattr(mcp_server.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_server.settings, "MCP_STANDALONE_ENABLED", False)

    with pytest.raises(RuntimeError, match="Standalone MCP is disabled"):
        mcp_server._ensure_standalone_mcp_enabled()

    monkeypatch.setattr(mcp_server.settings, "MCP_STANDALONE_ENABLED", True)
    mcp_server._ensure_standalone_mcp_enabled()
