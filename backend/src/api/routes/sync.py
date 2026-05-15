"""
客户端数据同步 API

提供 Tauri 客户端（桌面/移动）与云端之间的增量数据同步。
支持推送本地变更、拉取云端更新、冲突检测与解决。

同步架构：
- 控制面（始终可用）：OTA 更新、许可证验证
- 数据面（按模式）：业务数据的增量同步
"""

from typing import Any, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.remote_control_service import (
    REMOTE_CONTROL_REQUIRED_SCOPE,
    REMOTE_CONTROL_ROUTE_KEY,
    RemoteControlError,
    RemoteControlService,
)
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
    merged_data: dict[str, Any] | None = Field(
        default=None, description="合并后的数据（resolution=merge 时必填）"
    )


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

REMOTE_CONTROL_BLOCKED_PRIVACY_MODES = {
    "local",
    "top-secret",
    "top_secret",
    "local-only",
    "local_only",
}
REMOTE_CONTROL_HIGH_RISK_LEVELS = {"l4", "high", "critical"}


class RemoteControlStatusResponse(BaseModel):
    """移动远控桌面状态"""

    available: bool = False
    status: str = "not_configured"
    desktop_device_id: str | None = None
    pairing_id: str | None = None
    queued_command_count: int = 0
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
    expires_in_seconds: int = Field(default=300, ge=30, le=3600)


class RemoteControlPairingConfirmRequest(BaseModel):
    """桌面端确认移动远控配对"""

    desktop_device_id: str = Field(..., min_length=1, max_length=128)


class RemoteControlRouteTokenRequest(BaseModel):
    """为已确认的远控配对签发短期 route token"""

    pairing_id: str = Field(..., min_length=1, max_length=128)
    ttl_seconds: int = Field(default=300, ge=30, le=1800)


class RemoteControlCancelCommandRequest(BaseModel):
    """取消尚未执行的远控命令"""

    reason: str = Field(..., min_length=1, max_length=500)


class RemoteControlHostClaimRequest(BaseModel):
    """桌面 host 拉取待执行命令"""

    desktop_device_id: str = Field(..., min_length=1, max_length=128)
    pairing_id: str = Field(..., min_length=1, max_length=128)
    route_token: str = Field(..., min_length=1, max_length=512)
    host_instance_id: str = Field(..., min_length=1, max_length=160)
    limit: int = Field(default=10, ge=1, le=50)


class RemoteControlCommandStatusUpdateRequest(BaseModel):
    """桌面 host 回传命令执行状态"""

    desktop_device_id: str = Field(..., min_length=1, max_length=128)
    pairing_id: str = Field(..., min_length=1, max_length=128)
    route_token: str = Field(..., min_length=1, max_length=512)
    host_instance_id: str = Field(..., min_length=1, max_length=160)
    status: str = Field(..., min_length=1, max_length=40)
    result_summary: dict[str, Any] = Field(default_factory=dict)
    failure_reason: str | None = Field(default=None, max_length=1000)


def _normalize_remote_control_mode(mode: str | None) -> str:
    return (mode or "hybrid").strip().lower()


def _remote_control_denied(status_code: int, code: str, message: str) -> NoReturn:
    raise HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
            "required_controls": REMOTE_CONTROL_REQUIRED_CONTROLS,
        },
    )


def _org_id_for(user: User) -> str:
    if not user.org_id:
        _remote_control_denied(
            403,
            "remote_control_org_required",
            "移动远控必须绑定组织后才能使用。",
        )
    return str(user.org_id)


def _remote_control_error(error: RemoteControlError) -> NoReturn:
    _remote_control_denied(error.status_code, error.reason_code, error.human_message)


def _pairing_payload(pairing: Any) -> dict[str, Any]:
    return {
        "pairing_id": pairing.id,
        "mobile_device_id": pairing.mobile_device_id,
        "desktop_device_id": pairing.desktop_device_id,
        "requested_scopes": pairing.requested_scopes,
        "privacy_mode": pairing.privacy_mode,
        "status": pairing.status,
        "expires_at": _iso(pairing.expires_at),
        "confirmed_at": _iso(pairing.confirmed_at),
    }


def _command_payload(command: Any) -> dict[str, Any]:
    return {
        "command_id": command.id,
        "pairing_id": command.pairing_id,
        "desktop_device_id": command.desktop_device_id,
        "command_type": command.command_type,
        "risk_level": command.risk_level,
        "status": command.status,
        "route_id": command.route_id,
        "route_consumer_id": command.route_consumer_id,
        "route_scopes": command.route_scopes,
        "second_confirmed": command.second_confirmed,
        "expires_at": _iso(command.expires_at),
        "claimed_at": _iso(command.claimed_at),
        "claimed_by_host": command.claimed_by_host,
        "started_at": _iso(command.started_at),
        "completed_at": _iso(command.completed_at),
        "failed_at": _iso(command.failed_at),
        "failure_reason": command.failure_reason,
        "result_summary": command.result_summary,
        "cancelled_at": _iso(command.cancelled_at),
    }


def _host_command_payload(command: Any) -> dict[str, Any]:
    payload = _command_payload(command)
    payload["payload"] = command.payload
    return payload


def _audit_payload(event: Any) -> dict[str, Any]:
    return {
        "id": event.id,
        "pairing_id": event.pairing_id,
        "command_id": event.command_id,
        "action": event.action,
        "status": event.status,
        "reason_code": event.reason_code,
        "resource_snapshot": event.resource_snapshot,
        "metadata": event.metadata_json,
        "created_at": _iso(event.created_at),
    }


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


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
    db: AsyncSession = Depends(get_db),
) -> RemoteControlStatusResponse:
    """返回远控控制面的真实就绪状态；桌面执行证据未完成前不声称已执行。"""
    org_id = _org_id_for(user)
    result = await RemoteControlService(db).status(
        org_id=org_id,
        user_id=str(user.id),
        desktop_device_id=desktop_device_id,
    )
    return RemoteControlStatusResponse(**result)


@router.post("/remote-control/pairings", summary="申请移动端与桌面端配对")
async def request_remote_control_pairing(
    request: RemoteControlPairingRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """创建持久化配对请求；确认前仍不能下发命令。"""
    org_id = _org_id_for(user)
    privacy_mode = _normalize_remote_control_mode(request.privacy_mode)
    if privacy_mode in REMOTE_CONTROL_BLOCKED_PRIVACY_MODES:
        _remote_control_denied(
            403,
            "remote_control_privacy_mode_blocked",
            "本地/绝密模式下禁止移动端发起桌面远控配对；必须先在桌面端显式授权。",
        )

    try:
        pairing = await RemoteControlService(db).create_pairing(
            org_id=org_id,
            user_id=str(user.id),
            mobile_device_id=request.mobile_device_id,
            desktop_device_id=request.desktop_device_id,
            requested_scopes=request.requested_scopes,
            privacy_mode=privacy_mode,
            expires_in_seconds=request.expires_in_seconds,
        )
    except RemoteControlError as exc:
        _remote_control_error(exc)
    payload = _pairing_payload(pairing)
    await db.commit()
    return payload


@router.post("/remote-control/pairings/{pairing_id}/confirm", summary="桌面端确认移动远控配对")
async def confirm_remote_control_pairing(
    pairing_id: str,
    request: RemoteControlPairingConfirmRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """桌面端确认配对后，移动端才可以申请短期 route token。"""
    org_id = _org_id_for(user)
    try:
        pairing = await RemoteControlService(db).confirm_pairing(
            org_id=org_id,
            user_id=str(user.id),
            pairing_id=pairing_id,
            desktop_device_id=request.desktop_device_id,
        )
    except RemoteControlError as exc:
        _remote_control_error(exc)
    payload = _pairing_payload(pairing)
    await db.commit()
    return payload


@router.post("/remote-control/route-token", summary="签发移动远控短期 route token")
async def issue_remote_control_route_token(
    request: RemoteControlRouteTokenRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """为已确认配对签发短期 token；失败时不返回任何 raw token。"""
    org_id = _org_id_for(user)
    result = await RemoteControlService(db).issue_route_token(
        org_id=org_id,
        user_id=str(user.id),
        pairing_id=request.pairing_id,
        ttl_seconds=request.ttl_seconds,
    )
    await db.commit()
    return {
        "allowed": result.allowed,
        "reason_code": result.reason_code,
        "human_message": result.human_message,
        "route_token": result.token,
        "route_id": result.route_id,
        "pairing_id": result.pairing_id,
        "required_scope": REMOTE_CONTROL_REQUIRED_SCOPE,
        "route_key": REMOTE_CONTROL_ROUTE_KEY,
        "expires_at": _iso(result.expires_at),
    }


@router.post("/remote-control/commands", summary="下发移动远控桌面命令")
async def enqueue_remote_control_command(
    request: RemoteControlCommandRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """远控命令在未配对、未授权或未审计时一律拒绝；成功只代表入队。"""
    org_id = _org_id_for(user)
    privacy_mode = _normalize_remote_control_mode(request.privacy_mode)
    if privacy_mode in REMOTE_CONTROL_BLOCKED_PRIVACY_MODES:
        _remote_control_denied(
            403,
            "remote_control_privacy_mode_blocked",
            "本地/绝密模式下禁止移动端下发桌面远控命令。",
        )

    if (
        request.risk_level.strip().lower() in REMOTE_CONTROL_HIGH_RISK_LEVELS
        and not request.second_confirmed
    ):
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

    try:
        command = await RemoteControlService(db).enqueue_command(
            org_id=org_id,
            user_id=str(user.id),
            desktop_device_id=request.desktop_device_id,
            command_type=request.command_type,
            payload=request.payload,
            pairing_id=request.pairing_id,
            route_token=request.route_token,
            risk_level=request.risk_level,
            second_confirmed=request.second_confirmed,
            expires_in_seconds=request.expires_in_seconds,
        )
    except RemoteControlError as exc:
        _remote_control_error(exc)
    payload = _command_payload(command)
    await db.commit()
    return payload


@router.post("/remote-control/commands/claim", summary="桌面 host 拉取待执行远控命令")
async def claim_remote_control_commands(
    request: RemoteControlHostClaimRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """桌面 host 领取 queued 命令；返回命令不等于已执行。"""
    org_id = _org_id_for(user)
    try:
        commands = await RemoteControlService(db).claim_commands(
            org_id=org_id,
            user_id=str(user.id),
            desktop_device_id=request.desktop_device_id,
            pairing_id=request.pairing_id,
            route_token=request.route_token,
            host_instance_id=request.host_instance_id,
            limit=request.limit,
        )
    except RemoteControlError as exc:
        _remote_control_error(exc)
    payload = {
        "items": [_host_command_payload(command) for command in commands],
        "total": len(commands),
        "status": "claimed" if commands else "empty",
    }
    await db.commit()
    return payload


@router.post("/remote-control/commands/{command_id}/cancel", summary="取消未执行的远控命令")
async def cancel_remote_control_command(
    command_id: str,
    request: RemoteControlCancelCommandRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """用户撤销 queued 命令，桌面端后续拉取时不得执行。"""
    org_id = _org_id_for(user)
    try:
        command = await RemoteControlService(db).cancel_command(
            org_id=org_id,
            user_id=str(user.id),
            command_id=command_id,
            reason=request.reason,
        )
    except RemoteControlError as exc:
        _remote_control_error(exc)
    payload = _command_payload(command)
    await db.commit()
    return payload


@router.post("/remote-control/commands/{command_id}/status", summary="桌面 host 回传远控命令状态")
async def update_remote_control_command_status(
    command_id: str,
    request: RemoteControlCommandStatusUpdateRequest,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """记录桌面 host 的 running/completed/failed 状态回传和脱敏结果摘要。"""
    org_id = _org_id_for(user)
    try:
        command = await RemoteControlService(db).update_command_status(
            org_id=org_id,
            user_id=str(user.id),
            command_id=command_id,
            desktop_device_id=request.desktop_device_id,
            pairing_id=request.pairing_id,
            route_token=request.route_token,
            host_instance_id=request.host_instance_id,
            status=request.status,
            result_summary=request.result_summary,
            failure_reason=request.failure_reason,
        )
    except RemoteControlError as exc:
        _remote_control_error(exc)
    payload = _command_payload(command)
    await db.commit()
    return payload


@router.get("/remote-control/audit-events", summary="获取移动远控审计事件")
async def list_remote_control_audit_events(
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """返回当前用户/组织可见的远控控制面审计事件。"""
    org_id = _org_id_for(user)
    events = await RemoteControlService(db).audit_events(
        org_id=org_id, user_id=str(user.id), limit=limit
    )
    return {
        "items": [_audit_payload(event) for event in events],
        "total": len(events),
    }


@router.get("/remote-control/commands/{command_id}", summary="获取远控命令状态")
async def get_remote_control_command(
    command_id: str,
    user: User = Depends(get_current_user_required),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """查询 queued/cancelled 等命令状态，供移动端轮询。"""
    org_id = _org_id_for(user)
    command = await RemoteControlService(db).get_command(
        org_id=org_id,
        user_id=str(user.id),
        command_id=command_id,
    )
    if command is None:
        _remote_control_denied(
            404, "remote_control_command_not_found", "远控命令不存在或不属于当前组织。"
        )
    return _command_payload(command)


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
