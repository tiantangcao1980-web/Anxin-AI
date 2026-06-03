# -*- coding: utf-8 -*-
"""
CREAO 自愈闭环 Slice 1: Incidents API

- POST /api/v1/incidents/report — 前端错误上报（匿名 / 登录均可，按 IP 限频 5/min）
- GET  /api/v1/admin/incidents  — 管理员分页查询，按 last_seen_at DESC 排序

依赖 Agent A 提供：
- src.models.incident.Incident
- src.schemas.incident.{IncidentSource, IncidentSeverity, IncidentStatus,
                         IncidentRead, IncidentReportIn, IncidentListQuery}
- src.harness.incident_collector.IncidentCollector
"""


from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import get_admin_user, get_current_user, rate_limit
from src.harness.incident_collector import IncidentCollector

# ===== Agent A 契约 =====
from src.models.incident import Incident
from src.models.user import User
from src.schemas.incident import (
    IncidentRead,
    IncidentReportIn,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
)
from src.services.pii_service import pii_service

router = APIRouter(tags=["Incidents"])


# A10 (2026-05-14): 二级限频 (指纹 + 用户) 防 burst
# 第一级是 rate_limit decorator 的 5 req/min/IP (已有, 防匿名爬虫)
# 第二级:
#   - 指纹: 同 (url + message hash) 60s 内 ≥ 20 次 → 429 (单错误反复抖动)
#   - 用户: 同 user_id 60s 内 ≥ 30 次 → 429 (单认证用户失控刷)
# 实现移到 src.utils.rate_limit_burst, 单测可不经 FastAPI 链路独立运行.

from src.utils.rate_limit_burst import (
    _FINGERPRINT_BURST_LIMIT,
    _FINGERPRINT_WINDOW_SECONDS,
    _USER_BURST_LIMIT,
    _USER_WINDOW_SECONDS,
)
from src.utils.rate_limit_burst import (
    check_burst as _check_burst,
)
from src.utils.rate_limit_burst import (
    fingerprint_buckets as _fingerprint_buckets,
)
from src.utils.rate_limit_burst import (
    fingerprint_preview as _fingerprint_preview,
)
from src.utils.rate_limit_burst import (
    rate_lock as _rate_lock,
)
from src.utils.rate_limit_burst import (
    user_buckets as _user_buckets,
)


# ============================================================
# POST /api/v1/incidents/report  — 前端错误上报
# ============================================================
@router.post(
    "/incidents/report",
    status_code=status.HTTP_201_CREATED,
)
async def report_incident(
    payload: IncidentReportIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user),
    # 匿名也允许；按 IP 限频 5 req/min（by_user=False → 全部走 IP）
    _rl: None = Depends(
        rate_limit(limit=5, window=60, endpoint="incidents.report", by_user=False)
    ),
):
    """
    接收前端 / 客户端的错误上报。

    - 鉴权：可选（匿名也允许，匿名时 user_id 为空）
    - 限频：5 次 / 分钟 / IP（沿用项目自带的 rate_limit）
    - source 强制为 FRONTEND_ERROR，severity 强制为 P3（防伪造，与 schema 注释一致）
    """
    collector = IncidentCollector(db, pii_service)

    # A10: 二级限频 — 指纹 + 用户级 burst 防护
    fp_key = _fingerprint_preview(payload.url, payload.message)
    user_key = str(user.id) if user else None
    with _rate_lock:
        if _check_burst(_fingerprint_buckets[fp_key], _FINGERPRINT_WINDOW_SECONDS, _FINGERPRINT_BURST_LIMIT):
            logger.warning(f"[incidents.report] 指纹 burst 限流 fp={fp_key}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="该错误近期重复出现过多, 服务端已暂时屏蔽上报",
            )
        if user_key and _check_burst(_user_buckets[user_key], _USER_WINDOW_SECONDS, _USER_BURST_LIMIT):
            logger.warning(f"[incidents.report] 用户 burst 限流 user_id={user_key}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="单用户上报频率过高, 请稍后再试",
            )

    # 把客户端只允许的几个白名单字段塞进 incident.payload
    inner_payload: dict = {
        "message": payload.message,
        "stack": payload.stack,
        "url": payload.url,
        "user_agent": payload.user_agent or request.headers.get("user-agent", ""),
        "client_ip": request.client.host if request.client else None,
    }
    # 去 None 让 payload 干净
    inner_payload = {k: v for k, v in inner_payload.items() if v is not None}

    try:
        incident = await collector.collect(
            source=IncidentSource.FRONTEND_ERROR,
            title=payload.title[:200],
            payload=inner_payload,
            severity=IncidentSeverity.P3,
            user_id=str(user.id) if user else None,
            session_id=payload.session_id,
            fingerprint_keys=["url", "message"],
        )
    except Exception as exc:
        logger.error(f"[incidents.report] collect failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="incident 上报失败",
        ) from exc

    return {"id": str(getattr(incident, "id", "")) or None}


# ============================================================
# GET /api/v1/admin/incidents  — 管理员列表
# ============================================================
@router.get("/admin/incidents")
async def list_incidents(
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=200, description="每页条数"),
    source: IncidentSource | None = Query(None),
    severity: IncidentSeverity | None = Query(None),
    status_: IncidentStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
):
    """管理员分页查询 incidents 列表，按 last_seen_at DESC 排序。"""
    stmt = select(Incident)
    count_stmt = select(func.count()).select_from(Incident)

    if source is not None:
        stmt = stmt.where(Incident.source == source.value)
        count_stmt = count_stmt.where(Incident.source == source.value)
    if severity is not None:
        stmt = stmt.where(Incident.severity == severity.value)
        count_stmt = count_stmt.where(Incident.severity == severity.value)
    if status_ is not None:
        stmt = stmt.where(Incident.status == status_.value)
        count_stmt = count_stmt.where(Incident.status == status_.value)

    # 排序：last_seen_at DESC（契约要求）
    stmt = stmt.order_by(Incident.last_seen_at.desc())

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    total_result = await db.execute(count_stmt)
    total = int(total_result.scalar() or 0)

    rows_result = await db.execute(stmt)
    rows = rows_result.scalars().all()

    items: list[dict] = []
    for row in rows:
        item = IncidentRead.model_validate(row)
        items.append(item.model_dump(mode="json"))

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ============================================================
# Slice 2 Triage API (A3, 2026-05-14)
# ============================================================

from src.harness.triage_service import (
    get_triage_overview,
    triage_open_incidents,
)


@router.post("/admin/incidents/triage/run")
async def admin_run_triage(
    *,
    limit: int = Query(200, ge=1, le=1000, description="单次处理上限"),
    dry_run: bool = Query(False, description="True=仅返回聚类不写库, False=同时 transition open→triaged"),
    enable_llm_summary: bool = Query(False, description="G7: P0/P1 cluster 调 LLM 给根因猜测 (花 token)"),
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """A3: 手动触发 Slice 2 Triage 处理。

    返回:
        {
            "scanned": int,
            "clusters": [...],   # 按 severity / 总频次排序; 含 llm_root_cause_hint 字段 (若启用)
            "transitioned": int,
            "generated_at": iso,
            "llm_calls": int,
        }
    """
    logger.info(
        f"[Admin] triage triggered by {user.email} "
        f"(limit={limit}, dry_run={dry_run}, llm={enable_llm_summary})"
    )
    return await triage_open_incidents(
        db, limit=limit, transition_state=not dry_run,
        enable_llm_summary=enable_llm_summary,
    )


@router.get("/admin/incidents/triage/overview")
async def admin_triage_overview(
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """A3: incidents 全局统计 (按状态 / 严重度 / 来源)。"""
    return await get_triage_overview(db)


# ============================================================
# Slice 3 Builder API (A9, 2026-05-14)
# ============================================================

from pydantic import BaseModel

from src.harness.builder_service import (
    build_drafts_for_incident,
    link_github_issue,
)


@router.get("/admin/incidents/{incident_id}/builder/drafts")
async def admin_get_builder_drafts(
    incident_id: str,
    repo: str = Query("anxin-ai/anxin-assistant", description="GitHub repo full name"),
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """A9: 为指定 incident 生成回归测试草稿 + GitHub Issue 草稿 (仅返回字符串, 不落库)。"""
    logger.info(f"[Admin] builder drafts requested by {user.email} for incident {incident_id}")
    return await build_drafts_for_incident(db, incident_id, repo_full_name=repo)


class LinkIssueIn(BaseModel):
    issue_url: str


@router.post("/admin/incidents/{incident_id}/builder/link-issue")
async def admin_link_issue(
    incident_id: str,
    payload: LinkIssueIn,
    user: User = Depends(get_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """A9: admin 把人工提交的 GitHub Issue URL 回填到 incident, 状态推进 → linked。"""
    logger.info(f"[Admin] link issue {payload.issue_url} → incident {incident_id} by {user.email}")
    return await link_github_issue(db, incident_id, payload.issue_url)
