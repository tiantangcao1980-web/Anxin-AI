"""
客户端数据同步 API

提供 Tauri 客户端（桌面/移动）与云端之间的增量数据同步。
支持推送本地变更、拉取云端更新、冲突检测与解决。

同步架构：
- 控制面（始终可用）：OTA 更新、许可证验证
- 数据面（按模式）：业务数据的增量同步
"""


from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.sync_service import SyncService

router = APIRouter()


# ===== 数据模型 =====

class SyncRecord(BaseModel):
    """单条同步记录"""
    entity_type: str = Field(..., description="实体类型: message/document/case/contract/setting")
    entity_id: str = Field(..., description="实体 ID")
    action: str = Field(..., description="操作: create/update/delete")
    data: dict[str, Any] = Field(default_factory=dict, description="实体数据")
    timestamp: str = Field(..., description="客户端操作时间 (ISO 8601)")
    version: int = Field(default=0, description="客户端版本号")


class SyncPushRequest(BaseModel):
    """同步推送请求"""
    records: list[SyncRecord] = Field(..., description="待同步记录列表")
    device_id: str = Field(..., description="设备唯一标识")
    last_sync_version: int = Field(default=0, description="客户端已知的最新服务端版本")


class SyncPushResponse(BaseModel):
    """同步推送响应"""
    accepted: int = Field(description="成功接收的记录数")
    rejected: int = Field(default=0, description="被拒绝的记录数")
    conflicts: list[dict[str, Any]] = Field(default_factory=list, description="冲突记录列表")
    server_version: int = Field(description="推送后的服务端版本号")


class SyncPullResponse(BaseModel):
    """同步拉取响应"""
    records: list[dict[str, Any]] = Field(default_factory=list, description="增量更新记录")
    server_version: int = Field(description="当前服务端版本号")
    has_more: bool = Field(default=False, description="是否还有更多数据")


class SyncConflictResolution(BaseModel):
    """冲突解决请求"""
    entity_type: str
    entity_id: str
    resolution: str = Field(..., description="keep_local / keep_remote / merge")
    merged_data: dict[str, Any] | None = Field(default=None, description="合并后的数据（resolution=merge 时必填）")


class SyncStatusResponse(BaseModel):
    """同步状态"""
    server_version: int
    last_sync_time: str | None = None
    pending_conflicts: int = 0
    storage_used_bytes: int = 0
    storage_limit_bytes: int = 0


REMOTE_CONTROL_REQUIRED_CONTROLS = [
    "device_pairing",
    "desktop_confirmation",
    "capability_route_token",
    "second_confirmation_for_high_risk_commands",
    "command_expiry_and_revocation",
    "audit_log",
]

REMOTE_CONTROL_BLOCKED_PRIVACY_MODES = {"local", "top-secret", "top_secret", "local-only", "local_only"}
REMOTE_CONTROL_HIGH_RISK_LEVELS = {"l4", "high", "critical"}


class RemoteControlStatusResponse(BaseModel):
    """移动远控桌面状态"""
    available: bool = False
    status: str = "not_configured"
    desktop_device_id: str | None = None
    required_controls: list[str] = Field(default_factory=list)
    message: str


class RemoteControlPairingRequest(BaseModel):
    """移动端发起桌面配对请求"""
    mobile_device_id: str = Field(..., min_length=1, max_length=128)
    desktop_device_id: str = Field(..., min_length=1, max_length=128)
    requested_scopes: list[str] = Field(default_factory=list, max_length=20)
    privacy_mode: str = Field(default="hybrid", max_length=40)
    expires_in_seconds: int = Field(default=600, ge=60, le=3600)


class RemoteControlCommandRequest(BaseModel):
    """移动端远控命令请求"""
    desktop_device_id: str = Field(..., min_length=1, max_length=128)
    command_type: str = Field(..., min_length=1, max_length=80)
    payload: dict[str, Any] = Field(default_factory=dict)
    pairing_id: str | None = Field(default=None, max_length=128)
    route_token: str | None = Field(default=None, max_length=512)
    privacy_mode: str = Field(default="hybrid", max_length=40)
    risk_level: str = Field(default="l3", max_length=40)
    second_confirmed: bool = False


def _normalize_remote_control_mode(mode: str | None) -> str:
    return (mode or "hybrid").strip().lower()


def _remote_control_denied(status_code: int, code: str, message: str) -> None:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "required_controls": REMOTE_CONTROL_REQUIRED_CONTROLS,
        },
    )


# ===== API 端点 =====

@router.post("/push", response_model=SyncPushResponse, summary="推送本地变更到云端")
async def sync_push(
    request: SyncPushRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> SyncPushResponse:
    """
    客户端将本地待同步的数据变更推送到服务端。

    处理流程：
    1. 验证设备身份和用户权限
    2. 检测版本冲突（对比 client.version 和 server.version）
    3. 无冲突记录直接写入数据库
    4. 有冲突记录返回给客户端，由用户决定如何解决
    5. 更新服务端版本号并返回
    """
    result = await SyncService(db).push(
        user_id=str(user.id),
        device_id=request.device_id,
        records=[record.model_dump() for record in request.records],
        last_sync_version=request.last_sync_version,
    )
    return SyncPushResponse(**result)


@router.get("/pull", response_model=SyncPullResponse, summary="拉取云端增量更新")
async def sync_pull(
    since_version: int = Query(0, description="起始版本号"),
    entity_types: str | None = Query(None, description="实体类型过滤，逗号分隔"),
    limit: int = Query(100, le=1000, description="每次拉取的最大记录数"),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> SyncPullResponse:
    """
    客户端从服务端拉取指定版本之后的增量变更。

    - 支持按实体类型过滤（message,document,case,contract）
    - 分页拉取，has_more=true 时需要继续拉取
    """
    parsed_types = [item.strip() for item in entity_types.split(",")] if entity_types else None
    result = await SyncService(db).pull(
        user_id=str(user.id),
        since_version=since_version,
        entity_types=parsed_types,
        limit=limit,
    )
    return SyncPullResponse(**result)


@router.get("/status", response_model=SyncStatusResponse, summary="获取同步状态")
async def sync_status(
    device_id: str | None = Query(None),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> SyncStatusResponse:
    """获取当前用户的同步状态信息"""
    result = await SyncService(db).status(str(user.id), device_id=device_id)
    return SyncStatusResponse(**result)


@router.get(
    "/remote-control/status",
    response_model=RemoteControlStatusResponse,
    summary="获取移动远控桌面能力状态",
)
async def remote_control_status(
    desktop_device_id: str | None = Query(None, max_length=128),
    user: User = Depends(get_current_user_required),
) -> RemoteControlStatusResponse:
    """返回远控能力的真实就绪状态；未完成协议闭环前只允许显式不可用。"""
    _ = user
    return RemoteControlStatusResponse(
        available=False,
        status="not_configured",
        desktop_device_id=desktop_device_id,
        required_controls=REMOTE_CONTROL_REQUIRED_CONTROLS,
        message="移动远控桌面尚未配置持久化设备配对、命令队列、撤销和审计闭环，默认不可用。",
    )


@router.post("/remote-control/pairings", summary="申请移动端与桌面端配对")
async def request_remote_control_pairing(
    request: RemoteControlPairingRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """远控配对必须 fail-closed，直到桌面确认、持久化存储和审计闭环全部接入。"""
    _ = user
    privacy_mode = _normalize_remote_control_mode(request.privacy_mode)
    if privacy_mode in REMOTE_CONTROL_BLOCKED_PRIVACY_MODES:
        _remote_control_denied(
            403,
            "remote_control_privacy_mode_blocked",
            "本地/绝密模式下禁止移动端发起桌面远控配对；必须先在桌面端显式授权。",
        )

    _remote_control_denied(
        409,
        "remote_control_pairing_store_missing",
        "远控配对持久化、桌面端确认和审计链路尚未完成，不能创建临时或假成功配对。",
    )
    return {}


@router.post("/remote-control/commands", summary="下发移动远控桌面命令")
async def enqueue_remote_control_command(
    request: RemoteControlCommandRequest,
    user: User = Depends(get_current_user_required),
) -> dict[str, Any]:
    """远控命令在未配对、未授权或未审计时一律拒绝，不进入队列。"""
    _ = user
    privacy_mode = _normalize_remote_control_mode(request.privacy_mode)
    if privacy_mode in REMOTE_CONTROL_BLOCKED_PRIVACY_MODES:
        _remote_control_denied(
            403,
            "remote_control_privacy_mode_blocked",
            "本地/绝密模式下禁止移动端下发桌面远控命令。",
        )

    if request.risk_level.strip().lower() in REMOTE_CONTROL_HIGH_RISK_LEVELS and not request.second_confirmed:
        _remote_control_denied(
            403,
            "remote_control_second_confirmation_required",
            "高风险桌面远控命令必须完成二次确认后才能进入命令队列。",
        )

    if not request.pairing_id:
        _remote_control_denied(
            403,
            "remote_control_pairing_required",
            "缺少已确认的设备配对，远控命令不会入队。",
        )

    if not request.route_token:
        _remote_control_denied(
            403,
            "remote_control_route_token_required",
            "缺少短期 CapabilityRoute token，远控命令不会入队。",
        )

    _remote_control_denied(
        409,
        "remote_control_command_queue_missing",
        "远控命令队列、执行状态回传、撤销和审计链路尚未完成，不能接受命令。",
    )
    return {}


@router.post("/resolve", summary="解决同步冲突")
async def sync_resolve(
    resolution: SyncConflictResolution,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    解决同步冲突。

    - keep_local: 使用客户端版本覆盖服务端
    - keep_remote: 放弃客户端变更，使用服务端版本
    - merge: 使用合并后的数据
    """
    if resolution.resolution == "merge" and resolution.merged_data is None:
        raise HTTPException(status_code=400, detail="merge 模式必须提供 merged_data")
    return await SyncService(db).resolve(
        user_id=str(user.id),
        entity_type=resolution.entity_type,
        entity_id=resolution.entity_id,
        resolution=resolution.resolution,
        merged_data=resolution.merged_data,
    )


@router.post("/full-sync", summary="全量同步（慎用）")
async def full_sync(
    device_id: str = Query(...),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    触发全量同步，将服务端所有数据下发到客户端。
    仅在首次安装或数据损坏时使用。
    """
    return await SyncService(db).full_sync(str(user.id), device_id=device_id)


# ===== Harness Artifact 同步 =====

class ArtifactPushRequest(BaseModel):
    """推送 Harness Artifact"""
    device_id: str = Field(..., description="设备唯一标识")
    session_id: str = Field(..., description="会话/任务 ID")
    artifacts: dict[str, Any] = Field(..., description="Artifact 数据 {type: data}")


class ArtifactPullRequest(BaseModel):
    """拉取 Harness Artifact"""
    session_id: str = Field(..., description="会话/任务 ID")
    artifact_types: list[str] | None = Field(None, description="要拉取的类型列表")


@router.post("/artifacts/push", summary="推送 Harness Artifact 到云端")
async def push_artifacts(
    request: ArtifactPushRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    桌面端完成任务后，将 Harness 中间产物（摘要、引用、风险标记等）推送到云端。
    其他端（Web/移动端）打开同一会话时可拉取这些结论。

    Artifact 类型：
    - summary: 任务执行摘要
    - citations: 法条/案例引用列表
    - risk_marks: 风险标记
    - validation_result: 输出校验结果
    - task_state: 任务状态快照
    """
    return await SyncService(db).push_artifacts(
        user_id=str(user.id),
        device_id=request.device_id,
        session_id=request.session_id,
        artifacts=request.artifacts,
    )


@router.post("/artifacts/pull", summary="拉取 Harness Artifact")
async def pull_artifacts(
    request: ArtifactPullRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    从云端拉取指定会话的 Harness Artifact。
    用于跨端恢复：桌面端产出 → Web/移动端继续。
    """
    return await SyncService(db).pull_artifacts(
        user_id=str(user.id),
        session_id=request.session_id,
        artifact_types=request.artifact_types,
    )
