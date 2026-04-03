# -*- coding: utf-8 -*-
"""
客户端数据同步 API

提供 Tauri 客户端（桌面/移动）与云端之间的增量数据同步。
支持推送本地变更、拉取云端更新、冲突检测与解决。

同步架构：
- 控制面（始终可用）：OTA 更新、许可证验证
- 数据面（按模式）：业务数据的增量同步
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.sync_service import sync_service

router = APIRouter()


# ===== 数据模型 =====

class SyncRecord(BaseModel):
    """单条同步记录"""
    entity_type: str = Field(..., description="实体类型: message/document/case/contract/setting")
    entity_id: str = Field(..., description="实体 ID")
    action: str = Field(..., description="操作: create/update/delete")
    data: dict = Field(default_factory=dict, description="实体数据")
    timestamp: str = Field(..., description="客户端操作时间 (ISO 8601)")
    version: int = Field(default=0, description="客户端版本号")


class SyncPushRequest(BaseModel):
    """同步推送请求"""
    records: List[SyncRecord] = Field(..., description="待同步记录列表")
    device_id: str = Field(..., description="设备唯一标识")
    last_sync_version: int = Field(default=0, description="客户端已知的最新服务端版本")


class SyncPushResponse(BaseModel):
    """同步推送响应"""
    accepted: int = Field(description="成功接收的记录数")
    rejected: int = Field(default=0, description="被拒绝的记录数")
    conflicts: List[dict] = Field(default_factory=list, description="冲突记录列表")
    server_version: int = Field(description="推送后的服务端版本号")


class SyncPullResponse(BaseModel):
    """同步拉取响应"""
    records: List[dict] = Field(default_factory=list, description="增量更新记录")
    server_version: int = Field(description="当前服务端版本号")
    has_more: bool = Field(default=False, description="是否还有更多数据")


class SyncConflictResolution(BaseModel):
    """冲突解决请求"""
    entity_type: str
    entity_id: str
    resolution: str = Field(..., description="keep_local / keep_remote / merge")
    merged_data: Optional[dict] = Field(default=None, description="合并后的数据（resolution=merge 时必填）")


class SyncStatusResponse(BaseModel):
    """同步状态"""
    server_version: int
    last_sync_time: Optional[str] = None
    pending_conflicts: int = 0
    storage_used_bytes: int = 0
    storage_limit_bytes: int = 0


# ===== API 端点 =====

@router.post("/push", response_model=SyncPushResponse, summary="推送本地变更到云端")
async def sync_push(request: SyncPushRequest, user: User = Depends(get_current_user_required)):
    """
    客户端将本地待同步的数据变更推送到服务端。

    处理流程：
    1. 验证设备身份和用户权限
    2. 检测版本冲突（对比 client.version 和 server.version）
    3. 无冲突记录直接写入数据库
    4. 有冲突记录返回给客户端，由用户决定如何解决
    5. 更新服务端版本号并返回
    """
    result = await sync_service.push(
        user_id=str(user.id),
        device_id=request.device_id,
        records=[record.model_dump() for record in request.records],
        last_sync_version=request.last_sync_version,
    )
    return SyncPushResponse(**result)


@router.get("/pull", response_model=SyncPullResponse, summary="拉取云端增量更新")
async def sync_pull(
    since_version: int = Query(0, description="起始版本号"),
    entity_types: Optional[str] = Query(None, description="实体类型过滤，逗号分隔"),
    limit: int = Query(100, le=1000, description="每次拉取的最大记录数"),
    user: User = Depends(get_current_user_required),
):
    """
    客户端从服务端拉取指定版本之后的增量变更。

    - 支持按实体类型过滤（message,document,case,contract）
    - 分页拉取，has_more=true 时需要继续拉取
    """
    parsed_types = [item.strip() for item in entity_types.split(",")] if entity_types else None
    result = await sync_service.pull(
        user_id=str(user.id),
        since_version=since_version,
        entity_types=parsed_types,
        limit=limit,
    )
    return SyncPullResponse(**result)


@router.get("/status", response_model=SyncStatusResponse, summary="获取同步状态")
async def sync_status(
    device_id: Optional[str] = Query(None),
    user: User = Depends(get_current_user_required),
):
    """获取当前用户的同步状态信息"""
    result = await sync_service.status(str(user.id), device_id=device_id)
    return SyncStatusResponse(**result)


@router.post("/resolve", summary="解决同步冲突")
async def sync_resolve(
    resolution: SyncConflictResolution,
    user: User = Depends(get_current_user_required),
):
    """
    解决同步冲突。

    - keep_local: 使用客户端版本覆盖服务端
    - keep_remote: 放弃客户端变更，使用服务端版本
    - merge: 使用合并后的数据
    """
    if resolution.resolution == "merge" and resolution.merged_data is None:
        raise HTTPException(status_code=400, detail="merge 模式必须提供 merged_data")
    return await sync_service.resolve(
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
):
    """
    触发全量同步，将服务端所有数据下发到客户端。
    仅在首次安装或数据损坏时使用。
    """
    return await sync_service.full_sync(str(user.id), device_id=device_id)


# ===== Harness Artifact 同步 =====

class ArtifactPushRequest(BaseModel):
    """推送 Harness Artifact"""
    device_id: str = Field(..., description="设备唯一标识")
    session_id: str = Field(..., description="会话/任务 ID")
    artifacts: dict = Field(..., description="Artifact 数据 {type: data}")


class ArtifactPullRequest(BaseModel):
    """拉取 Harness Artifact"""
    session_id: str = Field(..., description="会话/任务 ID")
    artifact_types: Optional[List[str]] = Field(None, description="要拉取的类型列表")


@router.post("/artifacts/push", summary="推送 Harness Artifact 到云端")
async def push_artifacts(
    request: ArtifactPushRequest,
    user: User = Depends(get_current_user_required),
):
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
    return await sync_service.push_artifacts(
        user_id=str(user.id),
        device_id=request.device_id,
        session_id=request.session_id,
        artifacts=request.artifacts,
    )


@router.post("/artifacts/pull", summary="拉取 Harness Artifact")
async def pull_artifacts(
    request: ArtifactPullRequest,
    user: User = Depends(get_current_user_required),
):
    """
    从云端拉取指定会话的 Harness Artifact。
    用于跨端恢复：桌面端产出 → Web/移动端继续。
    """
    return await sync_service.pull_artifacts(
        user_id=str(user.id),
        session_id=request.session_id,
        artifact_types=request.artifact_types,
    )
