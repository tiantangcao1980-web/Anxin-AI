"""
MCP Server Management Routes
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.core.deps import get_current_user_required, UserRole, require_role
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

class McpConfigResponse(McpConfigCreate):
    id: str
    cached_tools: Optional[List[Dict]] = []

    class Config:
        from_attributes = True

@router.get("/servers", response_model=List[McpConfigResponse])
async def list_servers(
    db: AsyncSession = Depends(get_db),
    user = Depends(require_role(UserRole.ADMIN))
):
    """List all configured MCP servers."""
    result = await db.execute(select(McpServerConfig))
    return result.scalars().all()

@router.post("/servers", response_model=McpConfigResponse)
async def create_server(
    config: McpConfigCreate,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_role(UserRole.ADMIN))
):
    """Add a new MCP server configuration."""
    # Check if name exists
    existing = await db.execute(select(McpServerConfig).where(McpServerConfig.name == config.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Server with this name already exists")

    db_config = McpServerConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    return db_config

@router.put("/servers/{server_id}", response_model=McpConfigResponse)
async def update_server(
    server_id: str,
    config: McpConfigUpdate,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_role(UserRole.ADMIN))
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
    return db_config

@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str,
    db: AsyncSession = Depends(get_db),
    user = Depends(require_role(UserRole.ADMIN))
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
    user = Depends(require_role(UserRole.ADMIN))
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
    user = Depends(get_current_user_required)
):
    """List all available tools from connected servers."""
    return await mcp_client_service.get_all_tools()
