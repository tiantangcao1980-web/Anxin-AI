"""
MCP Client Service
Manages connections to external MCP servers and exposes their tools to agents.
"""

import asyncio
import os
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack

from sqlalchemy import select
from loguru import logger

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client

from src.core.database import async_session_maker
from src.models.mcp_config import McpServerConfig

class McpClientService:
    """
    Manages MCP clients (connections to external servers).
    """
    
    def __init__(self):
        self._sessions: Dict[str, ClientSession] = {}
        self._exit_stack = AsyncExitStack()
        self._tools_cache: Dict[str, List[Dict]] = {}
        self._initialized = False

    async def initialize(self):
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

    async def connect_server(self, config: McpServerConfig):
        """Connect to a specific MCP server."""
        logger.info(f"Connecting to MCP server: {config.name} ({config.type})")
        
        try:
            if config.type == "stdio":
                # Create server parameters
                server_params = StdioServerParameters(
                    command=config.command,
                    args=config.args or [],
                    env={**os.environ, **(config.env or {})},
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

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """
        Get all available tools from all connected servers.
        Formats them as OpenAI-compatible tool definitions.
        """
        if not self._initialized:
            await self.initialize()

        openai_tools = []
        
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

    async def call_tool(self, unique_tool_name: str, arguments: Dict[str, Any]) -> Any:
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

    async def close(self):
        """Close all connections."""
        await self._exit_stack.aclose()
        self._sessions.clear()
        self._initialized = False

# Global instance
mcp_client_service = McpClientService()
