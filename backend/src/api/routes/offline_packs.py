"""
离线数据包 API —— LOCAL 运行模式核心支撑。

提供：
1. `GET /offline-packs` 列出可下载的离线包目录
2. `GET /offline-packs/{pack_id}` 获取某个包的详情与下载 URL
3. `GET /offline-packs/{pack_id}/download` 发起下载（302 跳转到 CDN / MinIO 签名 URL）
4. `GET /offline-packs/{pack_id}/manifest` 返回文件清单 + checksum，客户端用于增量更新

包类型：
- regulation_core   核心法规（宪法/民法典/刑法典/劳动法/公司法 等）
- regulation_full   全量法规（~2 GB）
- case_library      判例库（~1.5 GB，可按行业切分）
- template_pack     文书模板（~50 MB）
- knowledge_graph   知识图谱增量（~300 MB）

商业交付原则：
- 包元数据内置版本号 + pub_date + checksum（sha256），便于离线校验
- 客户端通过 manifest 的 files[].sha256 做断点续传与差量
- 所有下载走 HTTPS，URL 带有限时签名（默认 1 小时）
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Path, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

router = APIRouter()


# ============================================================================
# 数据结构
# ============================================================================

PackKind = Literal[
    "regulation_core",
    "regulation_full",
    "case_library",
    "template_pack",
    "knowledge_graph",
]


class PackFile(BaseModel):
    path: str
    size_bytes: int
    sha256: str


class OfflinePack(BaseModel):
    id: str
    kind: PackKind
    title: str
    description: str
    version: str
    pub_date: str
    size_bytes: int
    file_count: int
    checksum: str = Field(..., description="sha256 of the whole archive")
    # 下载入口：支持 CDN 直链或签名 URL
    download_url: str
    # 依赖关系：例如 case_library_industry 需要先装 regulation_core
    requires: list[str] = Field(default_factory=list)
    # 最小客户端版本：防止老客户端装入不兼容的结构
    min_client_version: str | None = None


class PackManifest(BaseModel):
    id: str
    version: str
    files: list[PackFile]
    total_size: int
    generated_at: str


# ============================================================================
# 配置来源：JSON 文件（CI 发版同步更新）
# ============================================================================

_DEFAULT_PACKS_FILE = os.environ.get(
    "OFFLINE_PACKS_FILE",
    os.path.join(
        os.path.dirname(__file__), "..", "..", "..", "..", "offline-packs.json",
    ),
)


def _load_packs() -> list[OfflinePack]:
    """从 JSON 文件加载离线包索引。"""
    if not os.path.exists(_DEFAULT_PACKS_FILE):
        return _built_in_packs()
    try:
        with open(_DEFAULT_PACKS_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        return [OfflinePack(**item) for item in raw.get("packs", [])]
    except Exception:
        return _built_in_packs()


def _built_in_packs() -> list[OfflinePack]:
    """硬编码兜底：便于新环境立即可见"目录"（但下载 URL 留空，需运维填）。"""
    now = datetime.now(UTC).isoformat()
    return [
        OfflinePack(
            id="regulation-core-v1",
            kind="regulation_core",
            title="核心法规库",
            description="宪法、民法典、刑法、劳动法、公司法等核心法律共 30+ 部",
            version="1.0.0",
            pub_date=now,
            size_bytes=50 * 1024 * 1024,
            file_count=33,
            checksum="pending",
            download_url="",  # 运维通过 offline-packs.json 配置
            min_client_version="1.0.0",
        ),
        OfflinePack(
            id="regulation-full-v1",
            kind="regulation_full",
            title="全量法规库",
            description="含部委规章、地方性法规、司法解释，总计 30,000+ 篇",
            version="1.0.0",
            pub_date=now,
            size_bytes=2 * 1024 * 1024 * 1024,
            file_count=33102,
            checksum="pending",
            download_url="",
            requires=["regulation-core-v1"],
            min_client_version="1.0.0",
        ),
        OfflinePack(
            id="template-pack-v1",
            kind="template_pack",
            title="文书模板库",
            description="合同、诉讼、意见、合规四大类共 200+ 模板",
            version="1.0.0",
            pub_date=now,
            size_bytes=50 * 1024 * 1024,
            file_count=218,
            checksum="pending",
            download_url="",
            min_client_version="1.0.0",
        ),
    ]


# ============================================================================
# 路由
# ============================================================================


@router.get("/", summary="列出所有可下载的离线包")
async def list_packs(
    kind: PackKind | None = Query(None, description="按类别筛选"),
) -> dict[str, Any]:
    packs = _load_packs()
    if kind:
        packs = [p for p in packs if p.kind == kind]
    return {"items": packs, "total": len(packs)}


@router.get("/{pack_id}", summary="获取离线包详情")
async def get_pack(pack_id: str = Path(..., min_length=1)) -> OfflinePack:
    packs = _load_packs()
    for p in packs:
        if p.id == pack_id:
            return p
    raise HTTPException(status_code=404, detail=f"pack {pack_id} not found")


@router.get("/{pack_id}/manifest", summary="获取离线包文件清单（用于断点续传/校验）")
async def get_manifest(pack_id: str = Path(..., min_length=1)) -> PackManifest:
    """实际应从对象存储读取每个文件的 sha256。

    当前实现：返回空 files 列表的占位 manifest，方便客户端先跑通骨架。
    离线包机制见 `docs/ARCHITECTURE_V2.md` 的本地模式资源下载设计。
    """
    packs = _load_packs()
    for p in packs:
        if p.id == pack_id:
            return PackManifest(
                id=p.id,
                version=p.version,
                files=[],  # TODO: 从 S3/MinIO listing 生成
                total_size=p.size_bytes,
                generated_at=datetime.now(UTC).isoformat(),
            )
    raise HTTPException(status_code=404, detail=f"pack {pack_id} not found")


@router.get("/{pack_id}/download", summary="请求离线包下载链接（302）")
async def download_pack(pack_id: str = Path(..., min_length=1)) -> RedirectResponse:
    """返回 302 重定向到对象存储的签名 URL。

    生产建议：
    - MinIO/S3 `presigned_get_object` 生成 1 小时签名 URL
    - 配合 CDN 回源
    - 记录下载请求到审计日志
    """
    packs = _load_packs()
    for p in packs:
        if p.id == pack_id:
            if not p.download_url:
                raise HTTPException(
                    status_code=503,
                    detail=f"pack {pack_id} configured but download_url missing; "
                    "contact ops to publish binary asset",
                )
            return RedirectResponse(url=p.download_url, status_code=302)
    raise HTTPException(status_code=404, detail=f"pack {pack_id} not found")


@router.get("/healthz", summary="离线包服务健康检查")
async def healthz() -> dict[str, Any]:
    packs = _load_packs()
    configured = sum(1 for p in packs if p.download_url)
    return {
        "status": "ok" if configured > 0 else "degraded",
        "total_packs": len(packs),
        "configured_packs": configured,
        "unconfigured": [p.id for p in packs if not p.download_url],
        "server_time": datetime.now(UTC).isoformat(),
    }
