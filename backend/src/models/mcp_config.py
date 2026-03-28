"""
MCP Server Configuration Model
"""

from sqlalchemy import Column, String, Boolean, JSON
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
    args: Mapped[list] = mapped_column(JSON, default=[], nullable=True)
    env: Mapped[dict] = mapped_column(JSON, default={}, nullable=True)
    
    # For sse
    url: Mapped[str] = mapped_column(String, nullable=True)
    
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Cache of discovered tools to show in UI without connecting
    cached_tools: Mapped[list] = mapped_column(JSON, default=[], nullable=True)
