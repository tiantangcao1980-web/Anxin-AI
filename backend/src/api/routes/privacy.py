# -*- coding: utf-8 -*-
"""
数据隐私与个保法（DSAR）API。

端点：
- `GET  /privacy/classification/options` 可选分类值
- `GET  /privacy/export` 触发个人数据导出（异步）
- `GET  /privacy/export/status` 查询导出任务进度
- `POST /privacy/delete` 请求删除账户所有个人数据（异步，含冷静期）
- `POST /privacy/withdraw-consent` 撤回同意（仅云端模式相关授权）

数据分类约定：
- private   仅账户可见，默认存储到 `private-{uid}` MinIO bucket
- shared    仅授权协作人可见（case / contract / document 的分享对象）
- public    公共语料（法规 / 模板 / 判例 / 公开评论）

本文件同时为 DB 模型 `data_classification` 字段提供统一枚举。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ============================================================================
# 数据分类定义
# ============================================================================

PrivacyBucket = Literal["private", "shared", "public"]


class ClassificationOption(BaseModel):
    value: PrivacyBucket
    label: str
    description: str


CLASSIFICATIONS: list[ClassificationOption] = [
    ClassificationOption(
        value="private",
        label="仅自己可见",
        description="最高隐私级别；默认存本地 / 专属 bucket，仅账号本人能访问",
    ),
    ClassificationOption(
        value="shared",
        label="协作共享",
        description="仅指定协作对象可见；后端按 ACL 控制读写，下载带签名有效期",
    ),
    ClassificationOption(
        value="public",
        label="公共语料",
        description="所有登录用户可检索；用于法规库、模板库等公域知识",
    ),
]


@router.get("/classification/options", summary="列出分类选项")
async def list_classification_options():
    return {"items": CLASSIFICATIONS}


# ============================================================================
# DSAR：导出 & 删除
# ============================================================================

# 简化为内存状态机；生产需改为 `privacy_requests` 数据库表 + Celery worker
_export_jobs: dict[str, dict] = {}
_delete_jobs: dict[str, dict] = {}


class PrivacyExportStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str
    download_url: Optional[str] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None


class PrivacyDeleteRequest(BaseModel):
    reason: Optional[str] = Field(None, description="删除原因（可选）")
    confirm_word: str = Field(..., description="必须精确输入「确认删除」")


@router.get("/export", summary="触发个人数据导出（ZIP 打包）")
async def request_export(user: User = Depends(get_current_user_required)):
    """按个保法要求：用户有权获取个人数据副本。

    约束：
    - 每 24 小时最多触发 3 次
    - 下载链接有效期 7 天
    - 包含：profile / sessions / documents / contracts / messages / audit_log 等
    """
    now = datetime.now(timezone.utc).isoformat()
    job_id = f"export-{user.id}-{int(datetime.now(timezone.utc).timestamp())}"
    _export_jobs[job_id] = {
        "user_id": str(user.id),
        "status": "pending",
        "created_at": now,
    }
    # TODO(Phase 4)：扔到 Celery 队列，worker 真实聚合数据并写到 MinIO
    asyncio.create_task(_fake_export_worker(job_id))
    return PrivacyExportStatus(job_id=job_id, status="pending", created_at=now)


@router.get("/export/status", summary="查询导出任务进度")
async def export_status(
    job_id: str = Query(...),
    user: User = Depends(get_current_user_required),
):
    job = _export_jobs.get(job_id)
    if not job or job["user_id"] != str(user.id):
        raise HTTPException(status_code=404, detail="job not found")
    return PrivacyExportStatus(**{"job_id": job_id, **job})


@router.post("/delete", summary="请求删除账户（含 7 天冷静期）")
async def request_delete(
    body: PrivacyDeleteRequest,
    user: User = Depends(get_current_user_required),
):
    """按个保法要求：用户有权注销账户并清除个人数据。

    流程：
    - 校验确认词
    - 写入 `delete_jobs`，状态 pending
    - **7 天冷静期**内用户可通过登录撤回
    - 冷静期后 worker 真实执行数据删除（私有桶清空、消息销毁、关系链脱敏）
    """
    if body.confirm_word.strip() != "确认删除":
        raise HTTPException(status_code=400, detail="请精确输入「确认删除」以继续")

    now = datetime.now(timezone.utc)
    scheduled = now + timedelta(days=7)
    job_id = f"delete-{user.id}-{int(now.timestamp())}"
    _delete_jobs[job_id] = {
        "user_id": str(user.id),
        "status": "pending",
        "reason": body.reason,
        "created_at": now.isoformat(),
        "scheduled_at": scheduled.isoformat(),
    }
    return {
        "job_id": job_id,
        "status": "pending",
        "scheduled_at": scheduled.isoformat(),
        "message": "删除请求已受理。冷静期 7 天内登录账号可撤回；超过冷静期数据将不可恢复。",
    }


@router.post("/delete/cancel", summary="撤回删除请求（冷静期内）")
async def cancel_delete(
    job_id: str = Query(...),
    user: User = Depends(get_current_user_required),
):
    job = _delete_jobs.get(job_id)
    if not job or job["user_id"] != str(user.id):
        raise HTTPException(status_code=404, detail="job not found")
    if job["status"] not in ("pending",):
        raise HTTPException(status_code=409, detail=f"cannot cancel in status: {job['status']}")
    job["status"] = "cancelled"
    return {"status": "cancelled", "message": "已撤回账户删除请求"}


@router.post("/withdraw-consent", summary="撤回云端授权（回退到本地/混合模式）")
async def withdraw_consent(
    scope: Literal["all", "cloud_sync", "ai_training"] = Query("all"),
    user: User = Depends(get_current_user_required),
):
    """撤回特定授权范围：

    - `all`          撤回所有云端服务授权，自动切到 local 模式
    - `cloud_sync`   停止数据同步，保留登录态
    - `ai_training`  不再把您的数据用于 AI 训练（本项目默认即不训练，仅为合规接口）
    """
    # TODO(Phase 4): 写入 `user_consents` 表；触发 mode 切换广播
    return {
        "scope": scope,
        "effective_at": datetime.now(timezone.utc).isoformat(),
        "message": "授权已撤回",
    }


# ============================================================================
# Worker 模拟（生产替换为 Celery）
# ============================================================================


async def _fake_export_worker(job_id: str) -> None:
    job = _export_jobs.get(job_id)
    if not job:
        return
    job["status"] = "running"
    try:
        # 真实实现：聚合用户数据 → 打包 zip → 上传 MinIO private-<uid> → 签名 URL
        await asyncio.sleep(0.2)
        job["status"] = "completed"
        job["download_url"] = f"/api/v1/privacy/export/{job_id}/download"  # 占位
        job["expires_at"] = (
            datetime.now(timezone.utc) + timedelta(days=7)
        ).isoformat()
    except Exception as e:  # noqa: BLE001
        job["status"] = "failed"
        job["error"] = str(e)
