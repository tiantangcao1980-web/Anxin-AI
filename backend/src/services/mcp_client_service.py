"""
MCP Client Service
Manages connections to external MCP servers and exposes their tools to agents.
"""

import shlex
from collections.abc import Iterable
from contextlib import AsyncExitStack
from typing import Any
from urllib.parse import urlparse

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from sqlalchemy import select

from src.core.config import settings
from src.core.database import async_session_maker
from src.models.mcp_config import McpServerConfig


class McpConfigSecurityError(ValueError):
    """Raised when an MCP server config violates commercial safety policy."""


def _commercial_environment() -> bool:
    return settings.ENVIRONMENT.lower() in {"staging", "production"}


def _normalized_set(values: Iterable[str]) -> set[str]:
    return {value.strip() for value in values if value.strip()}


def _stdio_args(config: Any) -> list[str]:
    return [str(arg) for arg in (getattr(config, "args", None) or [])]


def _stdio_command_line(command: str, args: list[str]) -> str:
    return shlex.join([command, *args])


def validate_mcp_server_config(config: Any) -> None:
    """Validate MCP connection settings before persisting or connecting."""

    config_type = str(getattr(config, "type", "") or "").lower()
    if config_type not in {"stdio", "sse"}:
        raise McpConfigSecurityError(f"Unsupported MCP server type: {config_type or '<empty>'}")

    if config_type == "stdio":
        command = str(getattr(config, "command", "") or "").strip()
        if not command:
            raise McpConfigSecurityError("stdio MCP requires command")
        allowed_commands = _normalized_set(settings.MCP_STDIO_ALLOWED_COMMANDS)
        if _commercial_environment() and not settings.MCP_STDIO_ENABLED:
            raise McpConfigSecurityError("stdio MCP is disabled in staging/production unless explicitly enabled")
        if allowed_commands and command not in allowed_commands:
            raise McpConfigSecurityError("stdio MCP command is not in MCP_STDIO_ALLOWED_COMMANDS")
        if _commercial_environment() and not allowed_commands:
            raise McpConfigSecurityError("staging/production stdio MCP requires MCP_STDIO_ALLOWED_COMMANDS")
        args = _stdio_args(config)
        allowed_command_lines = _normalized_set(settings.MCP_STDIO_ALLOWED_COMMAND_LINES)
        if allowed_command_lines and _stdio_command_line(command, args) not in allowed_command_lines:
            raise McpConfigSecurityError("stdio MCP command line is not in MCP_STDIO_ALLOWED_COMMAND_LINES")
        if _commercial_environment() and args and not allowed_command_lines:
            raise McpConfigSecurityError("staging/production stdio MCP with args requires MCP_STDIO_ALLOWED_COMMAND_LINES")

        env_keys = set((getattr(config, "env", None) or {}).keys())
        allowed_env = _normalized_set(settings.MCP_STDIO_ALLOWED_ENV_KEYS)
        rejected_env = env_keys - allowed_env
        if _commercial_environment() and rejected_env:
            raise McpConfigSecurityError(
                "stdio MCP env contains keys outside MCP_STDIO_ALLOWED_ENV_KEYS: "
                + ", ".join(sorted(rejected_env))
            )
        return

    raw_url = str(getattr(config, "url", "") or "").strip()
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.hostname:
        raise McpConfigSecurityError("sse MCP requires absolute url")

    allowed_schemes = _normalized_set(settings.MCP_SSE_ALLOWED_SCHEMES)
    if allowed_schemes and parsed.scheme not in allowed_schemes:
        raise McpConfigSecurityError("sse MCP scheme is not in MCP_SSE_ALLOWED_SCHEMES")

    allowed_hosts = _normalized_set(settings.MCP_SSE_ALLOWED_HOSTS)
    if allowed_hosts and parsed.hostname not in allowed_hosts:
        raise McpConfigSecurityError("sse MCP host is not in MCP_SSE_ALLOWED_HOSTS")
    if _commercial_environment() and not allowed_hosts:
        raise McpConfigSecurityError("staging/production sse MCP requires MCP_SSE_ALLOWED_HOSTS")


def build_stdio_env(config: Any) -> dict[str, str]:
    """Build a minimal child process environment for stdio MCP."""

    configured_env = dict(getattr(config, "env", None) or {})
    allowed_env = _normalized_set(settings.MCP_STDIO_ALLOWED_ENV_KEYS)
    if allowed_env:
        return {key: value for key, value in configured_env.items() if key in allowed_env}
    if _commercial_environment():
        return {}
    return configured_env


class McpClientService:
    """
    Manages MCP clients (connections to external servers).
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self._tools_cache: dict[str, list[dict[str, Any]]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize connections to enabled MCP servers."""
        if self._initialized:
            return

        logger.info("Initializing MCP Client Service...")
        async with async_session_maker() as db:
            result = await db.execute(select(McpServerConfig).where(McpServerConfig.is_enabled == True))
            configs = result.scalars().all()

            for config in configs:
                try:
                    await self.connect_server(config)
                except Exception as e:
                    logger.error(f"Failed to connect to MCP server {config.name}: {e}")

        self._initialized = True

    async def connect_server(self, config: McpServerConfig) -> None:
        """Connect to a specific MCP server."""
        logger.info(f"Connecting to MCP server: {config.name} ({config.type})")

        try:
            validate_mcp_server_config(config)
            if config.type == "stdio":
                # Create server parameters
                server_params = StdioServerParameters(
                    command=config.command,
                    args=config.args or [],
                    env=build_stdio_env(config),
                )

                # We need to maintain the context manager alive
                # using AsyncExitStack to manage these long-lived connections
                transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
                read, write = transport
                session = await self._exit_stack.enter_async_context(ClientSession(read, write))

            elif config.type == "sse":
                transport = await self._exit_stack.enter_async_context(sse_client(config.url))
                read, write = transport
                session = await self._exit_stack.enter_async_context(ClientSession(read, write))
            else:
                raise ValueError(f"Unknown MCP server type: {config.type}")

            await session.initialize()

            # Cache tools
            result = await session.list_tools()
            tools = [tool.model_dump() for tool in result.tools]

            self._sessions[config.name] = session
            self._tools_cache[config.name] = tools

            logger.info(f"Connected to {config.name}. Discovered {len(tools)} tools.")

            # Update cache in DB (background task usually, but here simple)
            # async with async_session_maker() as db:
            #     config_item = await db.get(McpServerConfig, config.id)
            #     if config_item:
            #         config_item.cached_tools = tools
            #         await db.commit()

        except Exception as e:
            logger.error(f"Error connecting to {config.name}: {e}")
            raise

    async def get_all_tools(self) -> list[dict[str, Any]]:
        """
        Get all available tools from all connected servers.
        Formats them as OpenAI-compatible tool definitions.
        """
        if not self._initialized:
            await self.initialize()

        openai_tools: list[dict[str, Any]] = []

        for server_name, tools in self._tools_cache.items():
            for tool in tools:
                # Format for OpenAI: { "type": "function", "function": { ... } }
                # MCP tool schema is already JSON Schema compatible

                # Create a unique name to avoid collisions: server__tool
                unique_name = f"{server_name}__{tool['name']}"

                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": unique_name,
                        "description": tool.get("description", ""),
                        "parameters": tool.get("inputSchema", {})
                    }
                })

        return openai_tools

    async def call_tool(self, unique_tool_name: str, arguments: dict[str, Any]) -> Any:
        """
        Call a tool by its unique name (server__tool).
        """
        if "__" not in unique_tool_name:
            raise ValueError(f"Invalid tool name format: {unique_tool_name}")

        server_name, tool_name = unique_tool_name.split("__", 1)

        session = self._sessions.get(server_name)
        if not session:
            raise ValueError(f"Server {server_name} not connected")

        result = await session.call_tool(tool_name, arguments)
        return result

    async def close(self) -> None:
        """Close all connections."""
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._initialized = False

# Global instance
mcp_client_service = McpClientService()
