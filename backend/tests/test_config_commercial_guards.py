from types import SimpleNamespace

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


def test_mcp_allowlist_settings_accept_json_env(monkeypatch):
    monkeypatch.setenv("MCP_STDIO_ALLOWED_COMMANDS", '["uvx"]')
    monkeypatch.setenv("MCP_STDIO_ALLOWED_COMMAND_LINES", '["uvx trusted-mcp"]')
    monkeypatch.setenv("MCP_STDIO_ALLOWED_ENV_KEYS", '["MCP_TOKEN"]')
    monkeypatch.setenv("MCP_SSE_ALLOWED_HOSTS", '["mcp.example.com"]')
    monkeypatch.setenv("MCP_SSE_ALLOWED_SCHEMES", '["https"]')

    settings = Settings(_env_file=None)

    assert settings.MCP_STDIO_ALLOWED_COMMANDS == ["uvx"]
    assert settings.MCP_STDIO_ALLOWED_COMMAND_LINES == ["uvx trusted-mcp"]
    assert settings.MCP_STDIO_ALLOWED_ENV_KEYS == ["MCP_TOKEN"]
    assert settings.MCP_SSE_ALLOWED_HOSTS == ["mcp.example.com"]
    assert settings.MCP_SSE_ALLOWED_SCHEMES == ["https"]


def test_standalone_mcp_is_disabled_in_staging_by_default(monkeypatch):
    from src import mcp_server

    monkeypatch.setattr(mcp_server.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_server.settings, "MCP_STANDALONE_ENABLED", False)

    with pytest.raises(RuntimeError, match="Standalone MCP is disabled"):
        mcp_server._ensure_standalone_mcp_enabled()

    monkeypatch.setattr(mcp_server.settings, "MCP_STANDALONE_ENABLED", True)
    mcp_server._ensure_standalone_mcp_enabled()


def test_stdio_mcp_is_rejected_in_staging_without_explicit_enable(monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ENABLED", False)
    config = SimpleNamespace(type="stdio", command="uvx", env={})

    with pytest.raises(mcp_client_service.McpConfigSecurityError, match="stdio MCP is disabled"):
        mcp_client_service.validate_mcp_server_config(config)


def test_stdio_mcp_requires_command_allowlist_in_staging(monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ENABLED", True)
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ALLOWED_COMMANDS", ["uvx"])
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ALLOWED_ENV_KEYS", [])

    with pytest.raises(mcp_client_service.McpConfigSecurityError, match="command is not"):
        mcp_client_service.validate_mcp_server_config(
            SimpleNamespace(type="stdio", command="python", env={})
        )

    mcp_client_service.validate_mcp_server_config(
        SimpleNamespace(type="stdio", command="uvx", env={})
    )


def test_stdio_mcp_requires_exact_command_line_for_args_in_staging(monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ENABLED", True)
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ALLOWED_COMMANDS", ["uvx"])
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ALLOWED_COMMAND_LINES", [])
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ALLOWED_ENV_KEYS", [])

    with pytest.raises(mcp_client_service.McpConfigSecurityError, match="requires MCP_STDIO_ALLOWED_COMMAND_LINES"):
        mcp_client_service.validate_mcp_server_config(
            SimpleNamespace(type="stdio", command="uvx", args=["trusted-mcp"], env={})
        )

    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ALLOWED_COMMAND_LINES", ["uvx trusted-mcp"])
    mcp_client_service.validate_mcp_server_config(
        SimpleNamespace(type="stdio", command="uvx", args=["trusted-mcp"], env={})
    )


def test_sse_mcp_requires_https_allowed_host_in_staging(monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_SSE_ALLOWED_SCHEMES", ["https"])
    monkeypatch.setattr(mcp_client_service.settings, "MCP_SSE_ALLOWED_HOSTS", ["mcp.example.com"])

    with pytest.raises(mcp_client_service.McpConfigSecurityError, match="scheme is not"):
        mcp_client_service.validate_mcp_server_config(
            SimpleNamespace(type="sse", url="http://mcp.example.com/sse")
        )

    with pytest.raises(mcp_client_service.McpConfigSecurityError, match="host is not"):
        mcp_client_service.validate_mcp_server_config(
            SimpleNamespace(type="sse", url="https://evil.example.com/sse")
        )

    mcp_client_service.validate_mcp_server_config(
        SimpleNamespace(type="sse", url="https://mcp.example.com/sse")
    )


def test_stdio_mcp_child_env_uses_allowlist(monkeypatch):
    from src.services import mcp_client_service

    monkeypatch.setattr(mcp_client_service.settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(mcp_client_service.settings, "MCP_STDIO_ALLOWED_ENV_KEYS", ["MCP_TOKEN"])
    monkeypatch.setenv("DATABASE_URL", "postgresql://should-not-leak")

    env = mcp_client_service.build_stdio_env(
        SimpleNamespace(
            env={
                "MCP_TOKEN": "allowed",
                "DATABASE_URL": "blocked",
            }
        )
    )

    assert env == {"MCP_TOKEN": "allowed"}
