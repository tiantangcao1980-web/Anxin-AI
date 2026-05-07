"""
MCP Server Configuration Model
"""

from typing import Any

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class McpServerConfig(Base, TimestampMixin):
    __tablename__ = "mcp_server_configs"

    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    # Connection type: 'stdio' or 'sse'
    type: Mapped[str] = mapped_column(String, default="stdio", nullable=False)

    # For stdio
    command: Mapped[str] = mapped_column(String, nullable=True)
    args: Mapped[list[str]] = mapped_column(JSON, default=[], nullable=True)
    env: Mapped[dict[str, str]] = mapped_column(JSON, default={}, nullable=True)

    # For sse
    url: Mapped[str] = mapped_column(String, nullable=True)

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Cache of discovered tools to show in UI without connecting
    cached_tools: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=[], nullable=True)
