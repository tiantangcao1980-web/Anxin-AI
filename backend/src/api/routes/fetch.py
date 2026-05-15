"""
fetch 路由 — P6-A 信息获取栈对外 API。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/fetch"`` 注册）::

    POST   /api/v1/fetch                       通用抓取
    POST   /api/v1/fetch/batch                 批量抓取
    GET    /api/v1/fetch/audit                 审计日志（admin only）
    GET    /api/v1/fetch/compliance/check      检查域名合规性（不发请求）

权限：
- ``/fetch`` / ``/fetch/batch`` / ``/fetch/compliance/check`` — 任何登录用户
- ``/fetch/audit`` — 管理员（``user.role == 'admin'``）
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.api.routes.schemas.fetch import (
    AuditQueryOut,
    AuditRecordOut,
    ComplianceCheckOut,
    FetchBatchIn,
    FetchRequestIn,
    FetchResponseOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User
from src.services.fetch import (
    ExtractConfig,
    ExtractFormat,
    FetchRequest,
    FetchResponse,
    FetchTier,
    fetch_service,
)
from src.services.fetch.ssrf_guard import SSRFError, validate_url

router = APIRouter()


# ---------------------------------------------------------------------------
# 序列化辅助
# ---------------------------------------------------------------------------


def _to_request(payload: FetchRequestIn, user: User) -> FetchRequest:
    extract: ExtractConfig | None = None
    if payload.extract is not None:
        extract = ExtractConfig(
            css_selectors=payload.extract.css_selectors,
            xpath=payload.extract.xpath,
            schema=payload.extract.schema_,
            format=ExtractFormat(payload.extract.format),
        )
    tier_hint: FetchTier | None = (
        FetchTier(payload.tier_hint) if payload.tier_hint else None
    )
    return FetchRequest(
        url=str(payload.url),
        method=payload.method,
        headers=payload.headers,
        timeout=payload.timeout,
        tier_hint=tier_hint,
        extract=extract,
        user_id=str(user.id),
        bypass_cache=payload.bypass_cache,
        extra=payload.extra,
    )


def _to_response_out(resp: FetchResponse) -> FetchResponseOut:
    # 文本太大时截断防止 API 返回过大
    text = resp.text
    if text and len(text) > 200_000:
        text = text[:200_000]
    return FetchResponseOut(
        url=resp.request.url,
        status_code=resp.status_code,
        tier_used=resp.tier_used.value,
        duration_ms=resp.duration_ms,
        text=text,
        headers=resp.headers,
        extracted=resp.extracted,
        cached=resp.cached,
        error=resp.error,
        blocked_reason=resp.blocked_reason,
        ok=resp.ok,
    )


def _require_admin(user: User) -> None:
    if (getattr(user, "role", None) or "").lower() not in {"admin", "super_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可访问审计日志",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", response_model=FetchResponseOut, summary="通用抓取")
async def fetch_one(
    payload: FetchRequestIn,
    user: User = Depends(get_current_user_required),
) -> FetchResponseOut:
    """单次抓取 — 自动路由到合适的 Tier，支持合规检查 / 限流 / 降级 / 审计。"""
    request = _to_request(payload, user)
    try:
        validate_url(request.url)
    except SSRFError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": "URL rejected by SSRF policy"},
        ) from exc
    response = await fetch_service.fetch(request)
    return _to_response_out(response)


@router.post("/batch", response_model=list[FetchResponseOut], summary="批量抓取")
async def fetch_batch(
    payload: FetchBatchIn,
    user: User = Depends(get_current_user_required),
) -> list[FetchResponseOut]:
    """批量抓取 — 受信号量并发控制 + per-domain 限流仍生效。"""
    if not payload.requests:
        return []
    if len(payload.requests) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="单批最多 100 个请求",
        )
    requests = [_to_request(p, user) for p in payload.requests]
    for req in requests:
        try:
            validate_url(req.url)
        except SSRFError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": exc.code, "url": req.url, "message": "URL rejected by SSRF policy"},
            ) from exc
    responses = await fetch_service.fetch_batch(
        requests, concurrency=max(1, min(payload.concurrency, 20))
    )
    return [_to_response_out(r) for r in responses]


@router.get("/audit", response_model=AuditQueryOut, summary="抓取审计日志（管理员）")
async def fetch_audit(
    user_id: str | None = Query(None, description="按用户过滤"),
    tier: str | None = Query(None, description="按 Tier 过滤"),
    blocked_only: bool = Query(False, description="只看被拦截的"),
    limit: int = Query(100, ge=1, le=1000),
    user: User = Depends(get_current_user_required),
) -> AuditQueryOut:
    _require_admin(user)
    tier_enum: FetchTier | None = None
    if tier:
        try:
            tier_enum = FetchTier(tier)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效 tier: {tier}",
            ) from e
    records = await fetch_service.get_audit_logs(
        user_id=user_id,
        tier=tier_enum,
        blocked_only=blocked_only,
        limit=limit,
    )
    stats = await fetch_service.get_audit_stats()
    return AuditQueryOut(
        items=[
            AuditRecordOut(
                request_ts=r.request_ts.isoformat(),
                user_id=r.user_id,
                url=r.url,
                tier_used=r.tier_used.value,
                status_code=r.status_code,
                duration_ms=r.duration_ms,
                blocked_reason=r.blocked_reason,
                error=r.error,
            )
            for r in records
        ],
        total=len(records),
        stats=stats,
    )


@router.get(
    "/compliance/check",
    response_model=ComplianceCheckOut,
    summary="检查域名合规性（不发请求）",
)
async def compliance_check(
    url: str = Query(..., description="完整 URL"),
    user: User = Depends(get_current_user_required),  # noqa: ARG001 — 仅鉴权
) -> ComplianceCheckOut:
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL 必须以 http:// 或 https:// 开头",
        )
    result = fetch_service.check_compliance(url)
    return ComplianceCheckOut(**result)
