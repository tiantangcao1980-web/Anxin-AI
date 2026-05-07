"""
MCP Server Management Routes
"""


from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import Permission, require_permission
from src.models.mcp_config import McpServerConfig
from src.models.user import User
from src.services.audit_service import AuditService
from src.services.mcp_client_service import mcp_client_service

router = APIRouter()

class McpConfigCreate(BaseModel):
    name: str
    description: str | None = None
    type: str = "stdio"
    command: str | None = None
    args: list[str] | None = []
    env: dict[str, str] | None = {}
    url: str | None = None
    is_enabled: bool = True

class McpConfigUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None
    is_enabled: bool | None = None

class McpConfigResponse(BaseModel):
    """MCP 服务器响应 — 隐藏 env 中的敏感值"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    type: str = "stdio"
    command: str | None = None
    args: list[str] | None = []
    url: str | None = None
    is_enabled: bool = True
    cached_tools: list[dict[str, Any]] | None = []
    env_keys: list[str] | None = []  # 仅返回键名，不返回值

    @classmethod
    def from_orm_masked(
        cls,
        obj: McpServerConfig,
    ) -> "McpConfigResponse":
        """从 ORM 对象创建响应，遮罩 env 值"""
        data: dict[str, Any] = {
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


def _mcp_audit_value(config: McpServerConfig) -> dict[str, Any]:
    return {
        "name": config.name,
        "description": config.description,
        "type": config.type,
        "command": config.command,
        "args": config.args,
        "url": config.url,
        "is_enabled": config.is_enabled,
        "env_keys": list((config.env or {}).keys()),
    }


@router.get("/servers")
async def list_servers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SYSTEM)),
) -> list[McpConfigResponse]:
    """List all configured MCP servers (env values masked)."""
    result = await db.execute(select(McpServerConfig))
    return [McpConfigResponse.from_orm_masked(s) for s in result.scalars().all()]

@router.post("/servers")
async def create_server(
    config: McpConfigCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SYSTEM)),
) -> McpConfigResponse:
    """Add a new MCP server configuration."""
    existing = await db.execute(select(McpServerConfig).where(McpServerConfig.name == config.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Server with this name already exists")

    db_config = McpServerConfig(**config.model_dump())
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)
    await AuditService(db).log_from_request(
        request,
        action="mcp.server.create",
        resource_type="config",
        resource_id=db_config.id,
        user=user,
        new_value=_mcp_audit_value(db_config),
        extra_data={"source": "mcp"},
    )
    return McpConfigResponse.from_orm_masked(db_config)

@router.put("/servers/{server_id}")
async def update_server(
    server_id: str,
    config: McpConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SYSTEM)),
) -> McpConfigResponse:
    """Update an MCP server configuration."""
    db_config = await db.get(McpServerConfig, server_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Server not found")

    old_value = _mcp_audit_value(db_config)
    update_data = config.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_config, key, value)

    await db.commit()
    await db.refresh(db_config)
    await AuditService(db).log_from_request(
        request,
        action="mcp.server.update",
        resource_type="config",
        resource_id=db_config.id,
        user=user,
        old_value=old_value,
        new_value=_mcp_audit_value(db_config),
        extra_data={"source": "mcp"},
    )
    return McpConfigResponse.from_orm_masked(db_config)

@router.delete("/servers/{server_id}")
async def delete_server(
    server_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SYSTEM)),
) -> dict[str, bool]:
    """Delete an MCP server configuration."""
    db_config = await db.get(McpServerConfig, server_id)
    if not db_config:
        raise HTTPException(status_code=404, detail="Server not found")

    old_value = _mcp_audit_value(db_config)
    await db.delete(db_config)
    await db.commit()
    await AuditService(db).log_from_request(
        request,
        action="mcp.server.delete",
        resource_type="config",
        resource_id=server_id,
        user=user,
        old_value=old_value,
        extra_data={"source": "mcp"},
    )
    return {"success": True}

@router.post("/servers/{server_id}/connect")
async def connect_server(
    server_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission(Permission.MANAGE_SYSTEM)),
) -> dict[str, Any]:
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
        await AuditService(db).log_from_request(
            request,
            action="mcp.server.connect",
            resource_type="config",
            resource_id=config.id,
            user=user,
            status="success",
            extra_data={"source": "mcp", "tools_count": len(tools)},
        )

        return {"status": "connected", "tools_count": len(tools), "tools": tools}
    except Exception as e:
        await AuditService(db).log_from_request(
            request,
            action="mcp.server.connect",
            resource_type="config",
            resource_id=server_id,
            user=user,
            status="failed",
            error_message=str(e),
            extra_data={"source": "mcp"},
        )
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}") from e

@router.get("/tools")
async def list_available_tools(
    user: User = Depends(require_permission(Permission.MANAGE_SYSTEM)),
) -> list[dict[str, Any]]:
    """List all available tools from connected servers."""
    return await mcp_client_service.get_all_tools()
