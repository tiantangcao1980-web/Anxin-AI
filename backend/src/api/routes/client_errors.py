"""
客户端错误聚合上报端点（P19-B 三端可观测层 / Backend）

接收来自三端（Web / Mobile / Mini-Program）的：
  - 运行时错误（crash / unhandled_rejection）
  - Web Vitals 性能指标
  - 业务自定义事件

特性：
  - rate limit：每 IP 100 次 / 分钟，防滥用
  - 与 P19-A 后端 error_classifier 对齐：如果存在则调用其 hash 方法做二次归一化，
    保证三端 + 后端共用同一份错误指纹
  - 落库可选：检测到 ClientError model 则写库，否则只 log（不阻断）
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Request, status
from loguru import logger
from pydantic import BaseModel, Field

from src.core.deps import rate_limit
from src.core.responses import UnifiedResponse

router = APIRouter()


# ──────────────── Schema ────────────────


class Breadcrumb(BaseModel):
    ts: int | None = None
    category: str | None = None
    data: Any | None = None


class ClientErrorIn(BaseModel):
    """三端通用上报载荷。所有字段都是可选，因为不同 type 字段集不一样。"""

    source: str = Field(..., description="web | mobile | miniprogram")
    type: str | None = Field(
        default=None,
        description="crash | unhandled_rejection | web-vital | event | perf",
    )
    error: str | None = None
    stack: str | None = None
    name: str | None = None  # web-vital 名 / event 名
    value: float | None = None  # web-vital 数值
    rating: str | None = None  # web-vital good/needs-improvement/poor
    context: dict[str, Any] | None = None
    breadcrumbs: list[Breadcrumb] | None = None
    fingerprint: list[str] | None = None
    url: str | None = None
    ts: int | None = None


# ──────────────── Hash 对齐 P19-A 后端 error_classifier ────────────────


def _compute_hash(payload: ClientErrorIn) -> str:
    """
    计算与后端 error_classifier 同结构的 fingerprint hash。

    优先使用上报方提供的 fingerprint（前端已按 [client_source, module, errType, fn] 构造）。
    否则在服务端组合 (source, type, error, name, url) 兜底。

    若项目内已有 src.services.error_classifier.compute_fingerprint，则委托给它，
    确保前后端、三端共用同一种 hash 算法 → 同一种错误聚类视图。
    """
    try:
        # 尝试委托给 P19-A 的 classifier（如果已经存在）
        from src.services.error_classifier import compute_fingerprint  # type: ignore

        return compute_fingerprint(
            source=payload.source,
            error_type=(payload.type or "unknown"),
            module=(payload.fingerprint[1] if payload.fingerprint and len(payload.fingerprint) > 1 else (payload.url or "")),
            message=(payload.error or payload.name or ""),
        )
    except Exception:
        # 内置兜底：MD5(source|type|fingerprint|name|error)
        parts = [
            payload.source or "",
            payload.type or "",
            "|".join(payload.fingerprint or []),
            payload.name or "",
            (payload.error or "")[:200],
        ]
        return hashlib.md5("".join(parts).encode("utf-8")).hexdigest()


# ──────────────── 落库（可选） ────────────────


async def _try_persist(payload: ClientErrorIn, fingerprint_hash: str) -> bool:
    """
    若项目存在 ClientError model + session，则写库；否则返回 False（仅 log）。
    保持 best-effort，不让上报路径因为落库失败而 5xx。
    """
    try:
        from src.core.database import async_session_maker  # type: ignore
        from src.models.client_error import ClientError  # type: ignore

        async with async_session_maker() as session:
            row = ClientError(
                source=payload.source,
                error_type=payload.type or "unknown",
                message=(payload.error or payload.name or "")[:500],
                stack=(payload.stack or "")[:4000] if payload.stack else None,
                url=payload.url,
                context=payload.context or {},
                fingerprint_hash=fingerprint_hash,
                created_at=datetime.utcnow(),
            )
            session.add(row)
            await session.commit()
        return True
    except Exception as exc:
        # ClientError 表不存在或落库失败 → 仅 log，不报错
        logger.debug(f"[client_errors] persist skipped/failed: {exc}")
        return False


# ──────────────── Endpoint ────────────────


@router.post(
    "/client-errors",
    status_code=status.HTTP_202_ACCEPTED,
    summary="三端客户端错误 / 性能 / 事件聚合上报",
)
async def report_client_error(
    payload: ClientErrorIn,
    request: Request,
    # 100 次 / 60s, 按 IP 限速（无需登录态）
    _: None = Depends(
        rate_limit(limit=100, window=60, endpoint="client_errors", by_user=False)
    ),
) -> UnifiedResponse:
    """
    三端均可调用：
      - 不需要登录态（部分 Web Vitals 在用户登录前就触发）
      - 速率限制：每 IP 100 / min
      - 失败不返回业务错误，统一 202 Accepted（best-effort）
    """
    # 1) 计算 fingerprint hash（与 P19-A 对齐）
    fingerprint_hash = _compute_hash(payload)

    # 2) 写库（best-effort）
    persisted = await _try_persist(payload, fingerprint_hash)

    # 3) 结构化日志：让 Promtail / Loki / Grafana 即使在无 ClientError 表时也能聚合
    logger.bind(
        client_source=payload.source,
        client_type=payload.type,
        fingerprint_hash=fingerprint_hash,
        url=payload.url,
        client_ip=(request.client.host if request.client else None),
        persisted=persisted,
    ).info(
        f"[client_errors] {payload.source}/{payload.type} {payload.name or payload.error or ''}"[:300]
    )

    return UnifiedResponse(
        code=202,
        message="accepted",
        data={
            "accepted": True,
            "fingerprint_hash": fingerprint_hash,
            "persisted": persisted,
        },
    )
