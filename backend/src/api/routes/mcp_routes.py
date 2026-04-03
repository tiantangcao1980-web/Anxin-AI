"""
MCP Server Management Routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.deps import UserRole, get_admin_user, require_role
from src.services.mcp_client_service import mcp_client_service
from src.models.mcp_config import McpServerConfig
from src.core.database import get_db

router = APIRouter()

class McpConfigCreate(BaseModel):
    name: str
    description: Optional[str] = None
    type: str = "stdio"
    command: Optional[str] = None
    args: Optional[List[str]] = []
    env: Optional[Dict[str, str]] = {}
    url: Optional[str] = None
    is_enabled: bool = True

class McpConfigUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    is_enabled: Optional[bool] = None

class McpConfigResponse(BaseModel):
    """MCP 服务器响应 — 隐藏 env 中的敏感值"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: Optional[str] = None
    type: str = "stdio"
    command: Optional[str] = None
    args: Optional[List[str]] = []
    url: Optional[str] = None
    is_enabled: bool = True
    cached_tools: Optional[List[Dict]] = []
    env_keys: Optional[List[str]] = []  # 仅返回键名，不返回值

    @classmethod
    def from_orm_masked(cls, obj):
        """从 ORM 对象创建响应，遮罩 env 值"""
        data = {
            "id": obj.id,
            "name": obj.name,
            "description": obj.description,
            "type": obj.type,
            "command": obj.command,
            "args": obj.args,
            "url": obj.url,
            "is_enabled": obj.is_enabled,
            "cached_tools": obj.cached_tools,
            "env_keys": list((obj.env or {}).keys()),
        }
        return cls(**data)

@router.get("/servers")
async def list_servers(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_admin_user)
):
    """List all configured MCP servers (env values masked)."""
    result = await db.execute(select(McpServerConfig))
    return [McpConfigResponse.from_orm_masked(s) for s in result.scalars().all()]

@router.post("/servers")
async def create_server(
    config: McpConfigCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_admin_user)
):
    """Add a new MCP server configuration."""
    existing = await db.execute(select(McpServerConfig).where(McpServerConfig.name == config.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Server with this name already exists")

    db_config = McpServerConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return McpConfigResponse.from_orm_masked(db_config)

@router.put("/servers/{server_id}")
async def update_server(
    server_id: str,
    config: McpConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_admin_user)
):
    """Update an MCP server configuration."""
    db_config = await db.get(McpServerConfig, server_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Server not found")

    update_data = config.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)

    await db.commit()
    await db.refresh(db_config)
    return McpConfigResponse.from_orm_masked(db_config)

@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_admin_user)
):
    """Delete an MCP server configuration."""
    db_config = await db.get(McpServerConfig, server_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Server not found")

    await db.delete(db_config)
    await db.commit()
    return {"success": True}

@router.post("/servers/{server_id}/connect")
async def connect_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_admin_user)
):
    """Test connection and refresh tools."""
    config = await db.get(McpServerConfig, server_id)
    if not config:
        raise HTTPException(status_code=404, detail="Server not found")
    
    try:
        await mcp_client_service.connect_server(config)
        
        # Update cache
        tools = mcp_client_service._tools_cache.get(config.name, [])
        config.cached_tools = tools
        await db.commit()
        
        return {"status": "connected", "tools_count": len(tools), "tools": tools}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@router.get("/tools")
async def list_available_tools(
    user = Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))
):
    """List all available tools from connected servers."""
    return await mcp_client_service.get_all_tools()
