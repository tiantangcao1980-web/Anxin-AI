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
async def sync_push(request: SyncPushRequest):
    """
    客户端将本地待同步的数据变更推送到服务端。

    处理流程：
    1. 验证设备身份和用户权限
    2. 检测版本冲突（对比 client.version 和 server.version）
    3. 无冲突记录直接写入数据库
    4. 有冲突记录返回给客户端，由用户决定如何解决
    5. 更新服务端版本号并返回
    """
    accepted = 0
    conflicts = []

    for record in request.records:
        # TODO: 实际的冲突检测和数据写入逻辑
        # 这里先简单接收所有记录
        accepted += 1

    return SyncPushResponse(
        accepted=accepted,
        rejected=len(request.records) - accepted,
        conflicts=conflicts,
        server_version=request.last_sync_version + 1,
    )


@router.get("/pull", response_model=SyncPullResponse, summary="拉取云端增量更新")
async def sync_pull(
    since_version: int = Query(0, description="起始版本号"),
    entity_types: Optional[str] = Query(None, description="实体类型过滤，逗号分隔"),
    limit: int = Query(100, le=1000, description="每次拉取的最大记录数"),
):
    """
    客户端从服务端拉取指定版本之后的增量变更。

    - 支持按实体类型过滤（message,document,case,contract）
    - 分页拉取，has_more=true 时需要继续拉取
    """
    # TODO: 从数据库查询 version > since_version 的变更记录
    records = []

    return SyncPullResponse(
        records=records,
        server_version=since_version,
        has_more=False,
    )


@router.get("/status", response_model=SyncStatusResponse, summary="获取同步状态")
async def sync_status(device_id: Optional[str] = Query(None)):
    """获取当前用户的同步状态信息"""
    return SyncStatusResponse(
        server_version=0,
        last_sync_time=None,
        pending_conflicts=0,
        storage_used_bytes=0,
        storage_limit_bytes=10 * 1024 * 1024 * 1024,  # 10GB
    )


@router.post("/resolve", summary="解决同步冲突")
async def sync_resolve(resolution: SyncConflictResolution):
    """
    解决同步冲突。

    - keep_local: 使用客户端版本覆盖服务端
    - keep_remote: 放弃客户端变更，使用服务端版本
    - merge: 使用合并后的数据
    """
    # TODO: 实际的冲突解决逻辑
    return {
        "success": True,
        "entity_type": resolution.entity_type,
        "entity_id": resolution.entity_id,
        "resolution": resolution.resolution,
    }


@router.post("/full-sync", summary="全量同步（慎用）")
async def full_sync(device_id: str = Query(...)):
    """
    触发全量同步，将服务端所有数据下发到客户端。
    仅在首次安装或数据损坏时使用。
    """
    # TODO: 全量数据导出
    return {
        "success": True,
        "message": "全量同步已触发",
        "entity_counts": {
            "messages": 0,
            "documents": 0,
            "cases": 0,
            "contracts": 0,
        },
    }
