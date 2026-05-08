"""
CLI 命令接口

提供终端级别的系统操作能力，支持桌面端 Tauri CLI 和 API Key 认证。
所有操作经过 policy_engine 权限校验 + audit_service 审计。

安全约束（Harness policy_engine 控制）：
- CLI 使用 API Key 认证（非 JWT），独立于浏览器会话
- Key 权限是用户权限的子集（不可超越用户角色）
- 每条命令记录到 AuditLog，source="cli"
- 高危操作（删除/支付/签约）需二次确认或禁止
- CLI 频率限制：30 req/min
"""

import hashlib
import time
import uuid
from datetime import UTC, datetime
from typing import Any, TypedDict

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.core.deps import Permission, get_current_user_required, has_permission
from src.models.user import User
from src.services.audit_service import AuditService

router = APIRouter(prefix="/cli", tags=["CLI"])

COMMERCIAL_ENVIRONMENTS = {"staging", "production"}
CLI_ROUTE_SCOPE_PREFIX = "cli:"


class APIKeyRecord(TypedDict):
    key_id: str
    key_hash: str
    name: str
    user_id: str
    org_id: str | None
    scopes: list[str]
    expires_at: str
    created_at: str
    last_used_at: str | None


# ===== API Key 存储（内存版，生产环境应持久化到数据库） =====
_api_keys: dict[str, APIKeyRecord] = {}

# CLI 命令频率限制
_rate_limits: dict[str, list[float]] = {}
CLI_RATE_LIMIT = 30  # 每分钟最多 30 条
ALLOWED_SCOPES = {"read", "chat", "export"}


# ===== 数据模型 =====

class APIKeyCreateRequest(BaseModel):
    """创建 API Key"""
    name: str = Field(..., description="Key 名称（用于标识）")
    scopes: list[str] = Field(default=["read", "chat"], description="权限范围")
    expires_days: int = Field(default=90, le=90, description="有效期（天），最长90天")


class APIKeyResponse(BaseModel):
    """API Key 响应（仅创建时返回明文）"""
    key_id: str
    api_key: str | None = None  # 仅创建时返回
    name: str
    scopes: list[str]
    expires_at: str
    created_at: str


class CLICommandRequest(BaseModel):
    """CLI 命令请求"""
    command: str = Field(..., description="命令: consult/review/draft/search/template/status")
    args: dict[str, Any] = Field(default_factory=dict, description="命令参数")


class CLIRouteTokenRequest(BaseModel):
    """CLI route-token 签发请求"""
    scope: str = Field(default="read", description="CLI 权限范围: read/chat/export")
    route_key: str | None = Field(default=None, description="可选 route key；默认 cli:{key_id}")


class CLIRouteTokenResponse(BaseModel):
    """CLI route-token 签发响应"""
    success: bool
    required: bool
    route_key: str | None = None
    scope: str | None = None
    route_token: str | None = None
    expires_at: str | None = None
    error: str | None = None


class CLICommandResponse(BaseModel):
    """CLI 命令响应"""
    success: bool
    command: str
    result: Any = None
    error: str | None = None
    execution_time_ms: float = 0


# ===== API Key 认证 =====

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> APIKeyRecord:
    """验证 API Key"""
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()

    key_data = _api_keys.get(key_hash)
    if not key_data:
        raise HTTPException(status_code=401, detail="无效的 API Key")

    # 检查过期
    if datetime.fromisoformat(key_data["expires_at"]) < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="API Key 已过期，请重新生成")

    # 频率限制
    user_id = key_data["user_id"]
    now = time.time()
    if user_id not in _rate_limits:
        _rate_limits[user_id] = []
    _rate_limits[user_id] = [t for t in _rate_limits[user_id] if now - t < 60]
    if len(_rate_limits[user_id]) >= CLI_RATE_LIMIT:
        raise HTTPException(status_code=429, detail=f"CLI 频率超限（{CLI_RATE_LIMIT}/min）")
    _rate_limits[user_id].append(now)

    # 更新最后使用时间
    key_data["last_used_at"] = datetime.now(UTC).isoformat()

    return key_data


# ===== API Key 管理 =====


def _validate_requested_scopes(scopes: list[str], user: User) -> list[str]:
    normalized = []
    for scope in scopes:
        value = scope.strip().lower()
        if value and value not in normalized:
            normalized.append(value)
    if not normalized:
        raise HTTPException(status_code=400, detail="至少需要选择一个 CLI 权限范围")
    invalid = [scope for scope in normalized if scope not in ALLOWED_SCOPES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"无效 CLI 权限范围: {', '.join(invalid)}")
    if "export" in normalized and not has_permission(user.role, Permission.EXPORT_DATA):
        raise HTTPException(status_code=403, detail="当前角色不能创建 export 权限的 CLI Key")
    return normalized


@router.post("/keys", summary="创建 API Key")
async def create_api_key(
    request: APIKeyCreateRequest,
    http_request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> APIKeyResponse:
    """
    创建新的 CLI API Key。

    注意：API Key 仅在创建时显示一次，请妥善保存。
    有效期最长 90 天，到期后需重新创建。
    """

    # 生成 Key
    raw_key = f"anxin_cli_{uuid.uuid4().hex}"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_id = uuid.uuid4().hex[:12]

    from datetime import timedelta
    expires_at = datetime.now(UTC) + timedelta(days=request.expires_days)

    scopes = _validate_requested_scopes(request.scopes, user)
    key_data: APIKeyRecord = {
        "key_id": key_id,
        "key_hash": key_hash,
        "name": request.name,
        "user_id": str(user.id),
        "org_id": str(user.org_id) if user.org_id else None,
        "scopes": scopes,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(UTC).isoformat(),
        "last_used_at": None,
    }

    _api_keys[key_hash] = key_data
    await AuditService(db).log_from_request(
        http_request,
        action="cli.key.create",
        resource_type="token",
        resource_id=key_id,
        user=user,
        new_value={
            "name": request.name,
            "scopes": scopes,
            "expires_at": expires_at.isoformat(),
        },
        extra_data={"source": "cli"},
    )

    logger.info(f"[CLI] 创建 API Key: {key_id} ({request.name}), user={user.id}, 有效期 {request.expires_days} 天")

    return APIKeyResponse(
        key_id=key_id,
        api_key=raw_key,  # 仅此一次返回明文
        name=request.name,
        scopes=scopes,
        expires_at=expires_at.isoformat(),
        created_at=key_data["created_at"],
    )


@router.get("/keys", summary="列出 API Keys")
async def list_api_keys(
    user: User = Depends(get_current_user_required),
) -> dict[str, str | list[APIKeyResponse]]:
    """列出所有有效的 API Keys（不返回 key 值）"""
    keys = []
    for key_data in _api_keys.values():
        if key_data["user_id"] != str(user.id):
            continue
        keys.append(APIKeyResponse(
            key_id=key_data["key_id"],
            name=key_data["name"],
            scopes=key_data["scopes"],
            expires_at=key_data["expires_at"],
            created_at=key_data["created_at"],
        ))
    return {"status": "ok", "data": keys}


@router.delete("/keys/{key_id}", summary="撤销 API Key")
async def revoke_api_key(
    key_id: str,
    http_request: Request,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """撤销指定的 API Key"""
    for key_hash, key_data in list(_api_keys.items()):
        if key_data["key_id"] == key_id and key_data["user_id"] == str(user.id):
            del _api_keys[key_hash]
            await AuditService(db).log_from_request(
                http_request,
                action="cli.key.revoke",
                resource_type="token",
                resource_id=key_id,
                user=user,
                old_value={
                    "name": key_data["name"],
                    "scopes": key_data["scopes"],
                    "expires_at": key_data["expires_at"],
                },
                extra_data={"source": "cli"},
            )
            logger.info(f"[CLI] 撤销 API Key: {key_id}")
            return {"status": "ok", "message": f"Key {key_id} 已撤销"}
    raise HTTPException(status_code=404, detail="Key 不存在")


# ===== CLI 命令执行 =====

# 命令→权限 scope 映射
COMMAND_SCOPES = {
    "consult": "chat",
    "review": "chat",
    "draft": "chat",
    "search": "read",
    "template": "read",
    "status": "read",
    "cost": "read",
    "export": "export",  # 高权限
}

# 禁止通过 CLI 执行的高危命令
BLOCKED_COMMANDS = {"delete", "payment", "sign", "admin"}


def cli_route_governance_required() -> bool:
    return bool(settings.CLI_ROUTE_TOKEN_REQUIRED or settings.ENVIRONMENT.lower() in COMMERCIAL_ENVIRONMENTS)


def _cli_route_scope(required_scope: str) -> str:
    return f"{CLI_ROUTE_SCOPE_PREFIX}{required_scope.strip().lower()}"


def _default_cli_route_key(key_data: APIKeyRecord) -> str:
    return f"cli:{key_data['key_id']}"


@router.post("/route-token", response_model=CLIRouteTokenResponse, summary="签发 CLI route token")
async def issue_cli_route_token(
    request: CLIRouteTokenRequest,
    key_data: APIKeyRecord = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> CLIRouteTokenResponse:
    """签发短期 CLI route token，供桌面端在 `/cli/execute` 前获取并传递。"""
    required = cli_route_governance_required()
    requested_scope = request.scope.strip().lower()
    if requested_scope not in ALLOWED_SCOPES:
        return CLIRouteTokenResponse(
            success=False,
            required=required,
            scope=requested_scope or None,
            error=f"无效 CLI 权限范围: {requested_scope or '<empty>'}",
        )
    if requested_scope not in key_data["scopes"]:
        return CLIRouteTokenResponse(
            success=False,
            required=required,
            scope=requested_scope,
            error=f"API Key 缺少 '{requested_scope}' 权限",
        )

    route_key = (request.route_key or _default_cli_route_key(key_data)).strip()
    org_id = key_data.get("org_id")
    if not org_id:
        return CLIRouteTokenResponse(
            success=False,
            required=required,
            route_key=route_key,
            scope=requested_scope,
            error="CLI route token requires an organization-bound API Key",
        )

    from src.services.agent_governance_service import AgentGovernanceService

    issued = await AgentGovernanceService(db).issue_route_token(
        org_id=org_id,
        route_key=route_key,
        consumer_id=key_data["key_id"],
        requested_scopes=[_cli_route_scope(requested_scope)],
        actor_user_id=key_data["user_id"],
        actor_type="cli_api_key",
    )
    if not issued.allowed:
        return CLIRouteTokenResponse(
            success=False,
            required=required,
            route_key=route_key,
            scope=requested_scope,
            error=f"CLI route token denied: {issued.reason_code}",
        )

    return CLIRouteTokenResponse(
        success=True,
        required=required,
        route_key=route_key,
        scope=requested_scope,
        route_token=issued.token,
        expires_at=issued.expires_at.isoformat() if issued.expires_at else None,
    )


@router.post("/execute", response_model=CLICommandResponse, summary="执行 CLI 命令")
async def execute_command(
    request: CLICommandRequest,
    http_request: Request,
    x_capability_route_token: str | None = Header(None, alias="X-Capability-Route-Token"),
    key_data: APIKeyRecord = Depends(verify_api_key),
    db: AsyncSession = Depends(get_db),
) -> CLICommandResponse:
    """
    执行 CLI 命令。

    支持的命令：
    - consult <question>: 法律咨询
    - review <file_path>: 合同审查
    - draft <doc_type>: 文书起草
    - search <query>: 法律检索
    - template list: 列出模板
    - template download <id>: 下载模板
    - status: 查看系统状态
    - cost: 查看 token 消耗

    安全：所有命令经过权限校验和审计记录。
    """
    start_time = time.time()
    command = request.command.lower().strip()
    args = request.args

    # 安全检查1：阻止高危命令
    if command in BLOCKED_COMMANDS:
        error = f"命令 '{command}' 不允许通过 CLI 执行（安全限制）"
        await _audit_cli_execute(db, http_request, key_data, command, status="failed", error_message=error)
        return CLICommandResponse(
            success=False,
            command=command,
            error=error,
        )

    # 安全检查2：权限 scope 校验
    required_scope = COMMAND_SCOPES.get(command, "read")
    if required_scope not in key_data["scopes"]:
        error = f"API Key 缺少 '{required_scope}' 权限"
        await _audit_cli_execute(db, http_request, key_data, command, status="failed", error_message=error)
        return CLICommandResponse(
            success=False,
            command=command,
            error=error,
        )

    route_denial = await _authorize_cli_route(
        db=db,
        http_request=http_request,
        key_data=key_data,
        command=command,
        route_token=x_capability_route_token,
        required_scope=required_scope,
    )
    if route_denial is not None:
        return route_denial

    # 审计记录
    logger.info(f"[CLI] 执行命令: {command} | key={key_data['key_id']} | args={args}")

    try:
        result = await _dispatch_command(command, args)
        elapsed = round((time.time() - start_time) * 1000, 2)
        await _audit_cli_execute(
            db,
            http_request,
            key_data,
            command,
            status="success",
            extra_data={"execution_time_ms": elapsed},
        )
        return CLICommandResponse(
            success=True,
            command=command,
            result=result,
            execution_time_ms=elapsed,
        )
    except Exception as e:
        elapsed = round((time.time() - start_time) * 1000, 2)
        logger.error(f"[CLI] 命令执行失败: {command} | {e}")
        await _audit_cli_execute(
            db,
            http_request,
            key_data,
            command,
            status="failed",
            error_message=str(e),
            extra_data={"execution_time_ms": elapsed},
        )
        return CLICommandResponse(
            success=False,
            command=command,
            error=str(e),
            execution_time_ms=elapsed,
        )


async def _authorize_cli_route(
    *,
    db: AsyncSession,
    http_request: Request,
    key_data: APIKeyRecord,
    command: str,
    route_token: str | None,
    required_scope: str,
) -> CLICommandResponse | None:
    if not cli_route_governance_required():
        return None

    route_scope = _cli_route_scope(required_scope)
    org_id = key_data.get("org_id")
    consumer_id = key_data["key_id"]
    if not org_id or not route_token:
        error = "CLI route token required before command execution"
        await _audit_cli_execute(
            db,
            http_request,
            key_data,
            command,
            status="failed",
            error_message=error,
            extra_data={
                "route_governance": "denied",
                "route_reason": "missing_route_token",
                "route_scope": route_scope,
                "route_consumer_id": consumer_id,
            },
        )
        return CLICommandResponse(success=False, command=command, error=error)

    from src.services.agent_governance_service import AgentGovernanceService

    decision = await AgentGovernanceService(db).validate_route_token(
        org_id=org_id,
        raw_token=route_token,
        required_scope=route_scope,
        consumer_id=consumer_id,
        actor_user_id=key_data["user_id"],
        actor_type="cli_api_key",
    )
    if decision.allowed:
        return None

    error = f"CLI route token denied: {decision.reason_code}"
    await _audit_cli_execute(
        db,
        http_request,
        key_data,
        command,
        status="failed",
        error_message=error,
        extra_data={
            "route_governance": "denied",
            "route_reason": decision.reason_code,
            "route_scope": route_scope,
            "route_consumer_id": consumer_id,
            "route_audit_event_id": decision.audit_event_id,
        },
    )
    return CLICommandResponse(success=False, command=command, error=error)


async def _audit_cli_execute(
    db: AsyncSession,
    http_request: Request,
    key_data: APIKeyRecord,
    command: str,
    *,
    status: str,
    error_message: str | None = None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    actor = await db.get(User, key_data["user_id"])
    audit_extra = {
        "source": "cli",
        "command": command,
        "key_id": key_data["key_id"],
        "scopes": key_data["scopes"],
    }
    if extra_data:
        audit_extra.update(extra_data)
    await AuditService(db).log_from_request(
        http_request,
        action="cli.execute",
        resource_type="config",
        resource_id=key_data["key_id"],
        user=actor,
        status=status,
        error_message=error_message,
        extra_data=audit_extra,
    )


async def _dispatch_command(command: str, args: dict[str, Any]) -> Any:
    """命令路由分发"""

    if command == "status":
        return {
            "system": "ok",
            "version": "v0.9.8-beta",
            "harness_modules": 8,
            "agents": 19,
            "uptime": "running",
        }

    elif command == "cost":
        from src.harness.cost_tracker import cost_tracker
        return cost_tracker.get_stats()

    elif command == "template":
        sub = args.get("sub", "list")
        if sub == "list":
            from src.agents.template_librarian import TEMPLATE_CATALOG
            return [{"name": t["name"], "category": t["category"], "id": t["id"]} for t in TEMPLATE_CATALOG]
        elif sub == "download":
            template_id = args.get("id", "")
            from src.agents.template_librarian import TEMPLATE_CATALOG
            tpl = next((t for t in TEMPLATE_CATALOG if t["id"] == template_id), None)
            if tpl:
                return {"template": tpl, "download_url": tpl.get("download_path")}
            return {"error": f"模板 {template_id} 不存在"}

    elif command == "search":
        query = args.get("query", "")
        if not query:
            return {"error": "请提供搜索关键词"}
        return {
            "query": query,
            "message": "法律检索功能需要在完整运行环境中执行",
            "hint": "请使用 Web 端或桌面端进行法律检索",
        }

    elif command in ("consult", "review", "draft"):
        content = args.get("content", args.get("query", ""))
        if not content:
            return {"error": f"请提供{command}的内容"}
        return {
            "command": command,
            "content": content[:100],
            "message": f"{command} 任务已接收，请在 Web 端查看结果",
            "hint": "完整的 AI 交互需要在 Web 端或桌面端进行",
        }

    else:
        return {"error": f"未知命令: {command}", "available": list(COMMAND_SCOPES.keys())}
