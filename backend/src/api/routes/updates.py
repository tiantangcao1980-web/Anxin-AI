# -*- coding: utf-8 -*-
"""
OTA 更新 API —— Tauri 客户端自动更新端点。

Tauri Updater 协议：
- 返回 200 + JSON manifest 表示有新版本
- 返回 204 No Content 表示已是最新版本

数据源：
- 主路径：`UPDATER_MANIFEST_PATH` 指向的 JSON 文件（CI 发版时更新）
- 兜底：内存常量 `CURRENT_RELEASES`
- 未来可扩展为 `software_releases` 数据库表

manifest 示例见 docs/DEPLOYMENT_DESKTOP.md 2.3。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, Response
from pydantic import BaseModel, Field

router = APIRouter()


# ============================================================================
# 配置：manifest 文件位置
# ============================================================================

# 仓库根目录下的 updater-latest.json；CI 发版后会 `gh release upload` 到这里
_DEFAULT_MANIFEST_PATH = os.environ.get(
    "UPDATER_MANIFEST_PATH",
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "updater-latest.json",
    ),
)


# ============================================================================
# Pydantic Schemas
# ============================================================================


class UpdateManifest(BaseModel):
    """Tauri Updater 每次检查返回的结构（单平台）"""

    version: str = Field(..., description="新版本号")
    notes: str = Field(default="", description="更新说明（Markdown）")
    pub_date: str = Field(..., description="发布日期 (RFC 3339)")
    url: str = Field(..., description="更新包下载 URL")
    signature: str = Field(..., description="更新包签名")


class PlatformAsset(BaseModel):
    signature: str
    url: str


class FullManifest(BaseModel):
    """全量 manifest（CI 写入 JSON 文件的结构）"""

    version: str
    notes: str = ""
    pub_date: str
    platforms: dict[str, PlatformAsset] = Field(default_factory=dict)
    # 若客户端版本 < min_version 则强制更新（不允许"跳过此版本"）
    min_version: Optional[str] = None


# ============================================================================
# 工具函数
# ============================================================================


def _load_manifest_from_disk() -> Optional[FullManifest]:
    """优先读 JSON 文件。失败返回 None。"""
    path = _DEFAULT_MANIFEST_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return FullManifest(**data)
    except Exception:
        return None


def _normalize_arch(arch: str) -> str:
    """统一 Tauri 发送的 arch 标识：arm64 → aarch64。"""
    return "aarch64" if arch in ("aarch64", "arm64") else arch


def _compare_versions(v1: str, v2: str) -> int:
    """比较语义化版本号：返回 -1 / 0 / 1。"""
    try:
        # 去掉预发布后缀（1.2.3-beta.1 → 1.2.3）
        core1 = v1.split("-", 1)[0]
        core2 = v2.split("-", 1)[0]
        parts1 = [int(x) for x in core1.split(".") if x.isdigit()]
        parts2 = [int(x) for x in core2.split(".") if x.isdigit()]
        # 补齐到 3 位
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


# ============================================================================
# 路由
# ============================================================================


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
    target: str = Path(
        ..., pattern="^(darwin|windows|linux)$", description="目标平台"
    ),
    arch: str = Path(
        ..., pattern="^(x86_64|aarch64|arm64|i686)$", description="CPU 架构"
    ),
    current_version: str = Path(..., min_length=1, max_length=32),
):
    """Tauri Updater 插件定期调用此端点检查更新。

    无可用更新或配置缺失时返回 204。
    """
    manifest = _load_manifest_from_disk()
    if manifest is None:
        return Response(status_code=204)

    arch_key = _normalize_arch(arch)
    platform_key = f"{target}-{arch_key}"

    if platform_key not in manifest.platforms:
        # 该平台未发布：不推更
        return Response(status_code=204)

    if _compare_versions(current_version, manifest.version) >= 0:
        # 已是最新
        return Response(status_code=204)

    asset = manifest.platforms[platform_key]
    return UpdateManifest(
        version=manifest.version,
        notes=manifest.notes,
        pub_date=manifest.pub_date,
        url=asset.url,
        signature=asset.signature,
    )


@router.get("/", summary="运维接口：查看当前 manifest")
async def read_manifest():
    """供运维 / CI 验证 manifest 是否已生效。生产应加 admin 鉴权。"""
    m = _load_manifest_from_disk()
    if m is None:
        raise HTTPException(status_code=404, detail="updater manifest not configured")
    return m


@router.get("/latest", summary="前端展示：最新版本摘要")
async def get_latest_release():
    """给用户在 UI 上展示最新版本的简化结构。"""
    m = _load_manifest_from_disk()
    if m is None:
        return {"current_release": None, "platforms": {}}
    return {
        "current_release": {
            "version": m.version,
            "notes": m.notes,
            "pub_date": m.pub_date,
            "min_version": m.min_version,
        },
        "platforms": {k: {"url": v.url} for k, v in m.platforms.items()},
    }


@router.get("/changelog", summary="获取更新日志")
async def get_changelog(
    limit: int = Query(10, le=50),
    offset: int = Query(0),
):
    """返回版本历史列表。当前只返回最新一条（来自 manifest），
    未来可接入 `software_releases` 表提供完整历史。
    """
    m = _load_manifest_from_disk()
    if m is None:
        return {"total": 0, "versions": []}
    return {
        "total": 1,
        "versions": [
            {"version": m.version, "notes": m.notes, "pub_date": m.pub_date},
        ][offset : offset + limit],
    }


@router.get("/healthz", summary="Updater 服务健康检查")
async def healthz():
    m = _load_manifest_from_disk()
    return {
        "status": "ok" if m is not None else "degraded",
        "has_manifest": m is not None,
        "manifest_path": _DEFAULT_MANIFEST_PATH,
        "latest_version": m.version if m else None,
        "server_time": datetime.now(timezone.utc).isoformat(),
    }


# 供测试/手动发布使用的内存常量；文件源优先。
CURRENT_RELEASES: dict[str, dict] = {}
