# -*- coding: utf-8 -*-
"""
OTA 更新 API

为 Tauri 客户端提供自动更新支持。
属于控制面，所有运行模式下都可用。

Tauri Updater 协议：
- 返回 200 + JSON manifest 表示有新版本
- 返回 204 No Content 表示已是最新版本
"""

import os
import platform
from typing import Optional
from fastapi import APIRouter, HTTPException, Path, Query
from pydantic import BaseModel, Field

router = APIRouter()

# ===== 版本信息配置 =====
# 实际生产中应从数据库或配置服务读取

CURRENT_RELEASES = {
    # "target/arch": { version, url, signature, notes, mandatory }
    # target: darwin, linux, windows
    # arch: x86_64, aarch64
}


class UpdateManifest(BaseModel):
    """Tauri Updater 标准响应格式"""
    version: str = Field(..., description="新版本号")
    notes: str = Field(default="", description="更新说明（Markdown）")
    pub_date: str = Field(..., description="发布日期 (RFC 3339)")
    url: str = Field(..., description="更新包下载 URL")
    signature: str = Field(..., description="更新包签名")


class ReleaseInfo(BaseModel):
    """完整版本信息"""
    version: str
    notes: str
    pub_date: str
    platforms: dict = Field(default_factory=dict, description="各平台下载信息")
    mandatory: bool = False
    min_supported_version: Optional[str] = None


# ===== API 端点 =====

@router.get(
    "/{target}/{arch}/{current_version}",
    summary="检查客户端更新",
    response_model=UpdateManifest,
    responses={
        200: {"description": "有新版本可用"},
        204: {"description": "已是最新版本"},
    },
)
async def check_update(
    target: str = Path(..., description="目标平台: darwin/linux/windows"),
    arch: str = Path(..., description="CPU 架构: x86_64/aarch64"),
    current_version: str = Path(..., description="客户端当前版本号"),
):
    """
    检查是否有新版本可用。

    Tauri Updater 插件会自动调用此接口：
    - 返回 200 + 更新清单：提示用户更新
    - 返回 204：无更新
    """
    platform_key = f"{target}/{arch}"

    # 查找该平台的最新版本
    release = CURRENT_RELEASES.get(platform_key)

    if not release:
        # 没有该平台的发布记录，返回无更新
        raise HTTPException(status_code=204)

    latest_version = release.get("version", "0.0.0")

    # 版本比较（简单的语义化版本对比）
    if _compare_versions(current_version, latest_version) >= 0:
        # 当前版本 >= 最新版本，无需更新
        raise HTTPException(status_code=204)

    # 有新版本
    return UpdateManifest(
        version=latest_version,
        notes=release.get("notes", ""),
        pub_date=release.get("pub_date", ""),
        url=release.get("url", ""),
        signature=release.get("signature", ""),
    )


@router.get("/latest", summary="获取最新版本信息")
async def get_latest_release():
    """获取所有平台的最新版本信息"""
    return {
        "current_release": None,  # TODO: 从数据库读取
        "platforms": {
            "darwin/aarch64": {"status": "planned"},
            "darwin/x86_64": {"status": "planned"},
            "windows/x86_64": {"status": "planned"},
            "windows/aarch64": {"status": "planned"},
            "android": {"status": "planned"},
            "ios": {"status": "planned"},
        },
    }


@router.get("/changelog", summary="获取更新日志")
async def get_changelog(
    limit: int = Query(10, le=50),
    offset: int = Query(0),
):
    """获取版本更新日志列表"""
    # TODO: 从数据库读取版本历史
    return {
        "total": 0,
        "versions": [],
    }


def _compare_versions(v1: str, v2: str) -> int:
    """
    比较两个语义化版本号。
    返回: -1 (v1 < v2), 0 (v1 == v2), 1 (v1 > v2)
    """
    try:
        parts1 = [int(x) for x in v1.split(".")]
        parts2 = [int(x) for x in v2.split(".")]

        # 补齐长度
        while len(parts1) < 3:
            parts1.append(0)
        while len(parts2) < 3:
            parts2.append(0)

        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            if p1 > p2:
                return 1
        return 0
    except (ValueError, AttributeError):
        return 0
