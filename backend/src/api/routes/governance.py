# -*- coding: utf-8 -*-
"""
治理 Dashboard API —— 给 compliance_officer / org_admin / super_admin 看的治理总览

只读为主；写操作仅限 confirm-tickets approve/reject + policy reload。

挂载点：/api/v1/governance/*
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.deps import UserRole, get_current_user_required
from src.models.governance import (
    AuditEventDB,
    ConfirmTicket,
    ConfirmTicketStatus,
    ShadowRun,
)
from src.models.user import User
from src.services.governance import (
    Decision,
    audit,
    confirm_inbox,
    decide,
    get_policy,
    reload_policy,
    shadow_runner,
)

router = APIRouter(prefix="/governance", tags=["治理 Dashboard"])

REPO_ROOT = Path(__file__).resolve().parents[4]
AUDIT_DIR = REPO_ROOT / ".claude" / "audit"
SNAPSHOT_DIR = REPO_ROOT / ".claude" / "policy-snapshots"
REVOKED_FILE = REPO_ROOT / ".claude" / "builder-hub" / "revoked.json"


# ────────────────────────────────────────────────────────────────────
# 权限守门：只允许 super_admin / org_admin / compliance_officer
# ────────────────────────────────────────────────────────────────────
ALLOWED_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    "admin",
    "org_admin",
    "compliance_officer",
}


def _require_governance_role(user: User = Depends(get_current_user_required)) -> User:
    role = getattr(user, "role", None)
    role_v = role.value if hasattr(role, "value") else role
    if role_v not in {r.value if hasattr(r, "value") else r for r in ALLOWED_ROLES}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "治理 dashboard 仅限管理员 / 合规官访问")
    return user


# ────────────────────────────────────────────────────────────────────
# Policy
# ────────────────────────────────────────────────────────────────────
class PolicySnapshotMeta(BaseModel):
    snapshot_id: str
    loaded_at: str
    files: list[str] = Field(default_factory=list)


@router.get("/policy/current", summary="当前生效的 policy 快照元信息")
async def policy_current(user: User = Depends(_require_governance_role)) -> dict[str, Any]:
    policy = get_policy()
    return {
        "snapshot_id": policy.snapshot_id,
        "loaded_at": policy.loaded_at.isoformat(),
        "files": list(policy.raw.keys()),
        "summary": {
            "roles": list(policy.access_matrix.get("roles", {}).keys()),
            "data_levels": list(policy.data_classification.get("levels", {}).keys()),
            "trust_levels": list(policy.trust_levels.get("levels", {}).keys()),
            "skill_states": policy.skill_lifecycle.get("states", []),
        },
    }


@router.get("/policy/snapshots", summary="历史 policy 快照列表（按时间倒序）",
            response_model=list[PolicySnapshotMeta])
async def policy_snapshots(
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(_require_governance_role),
) -> list[PolicySnapshotMeta]:
    if not SNAPSHOT_DIR.exists():
        return []
    out: list[PolicySnapshotMeta] = []
    for sdir in sorted(SNAPSHOT_DIR.glob("pol_*"), key=lambda p: p.stat().st_mtime, reverse=True):
        meta_file = sdir / "_meta.json"
        if not meta_file.exists():
            continue
        try:
            data = json.loads(meta_file.read_text(encoding="utf-8"))
            out.append(PolicySnapshotMeta(**data))
        except (json.JSONDecodeError, ValueError):
            continue
        if len(out) >= limit:
            break
    return out


@router.get("/policy/files/{filename}", summary="读取 policy yaml 原文")
async def policy_file(filename: str, user: User = Depends(_require_governance_role)) -> dict[str, Any]:
    if "/" in filename or ".." in filename or not filename.endswith(".yaml"):
        raise HTTPException(400, "非法 filename")
    p = REPO_ROOT / "policy" / filename
    if not p.exists():
        raise HTTPException(404, f"{filename} 不存在")
    return {"filename": filename, "content": p.read_text(encoding="utf-8")}


@router.post("/policy/reload", summary="热重载 policy（仅 super_admin）")
async def policy_reload(user: User = Depends(get_current_user_required)) -> dict[str, Any]:
    role = getattr(user, "role", None)
    role_v = role.value if hasattr(role, "value") else role
    if role_v not in (UserRole.SUPER_ADMIN.value, "super_admin"):
        raise HTTPException(403, "仅 super_admin 可重载 policy")
    new_bundle = reload_policy()
    return {
        "snapshot_id": new_bundle.snapshot_id,
        "loaded_at": new_bundle.loaded_at.isoformat(),
    }


# ────────────────────────────────────────────────────────────────────
# Audit
# ────────────────────────────────────────────────────────────────────
@router.get("/audit", summary="查询审计事件（优先 DB；回退 JSONL）")
async def audit_search(
    actor_id: str | None = None,
    action: str | None = None,
    decision: str | None = None,
    event_type: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_governance_role),
) -> dict[str, Any]:
    """先查 DB 镜像；如果 DB 无记录或表不存在，回退 JSONL 文件。"""
    try:
        stmt = select(AuditEventDB).order_by(desc(AuditEventDB.ts))
        if actor_id:
            stmt = stmt.where(AuditEventDB.actor_id == actor_id)
        if action:
            stmt = stmt.where(AuditEventDB.action == action)
        if decision:
            stmt = stmt.where(AuditEventDB.decision == decision)
        if event_type:
            stmt = stmt.where(AuditEventDB.event_type == event_type)
        if since:
            stmt = stmt.where(AuditEventDB.ts >= datetime.fromisoformat(since))
        if until:
            stmt = stmt.where(AuditEventDB.ts <= datetime.fromisoformat(until))
        stmt = stmt.limit(limit)
        res = await db.execute(stmt)
        rows = list(res.scalars())
        if rows:
            return {
                "source": "db",
                "events": [
                    {
                        "event_id": r.event_id,
                        "ts": r.ts.isoformat() if r.ts else None,
                        "event_type": r.event_type,
                        "actor": {"id": r.actor_id, "role": r.actor_role, "tenant_id": r.tenant_id},
                        "action": r.action,
                        "decision": r.decision,
                        "outcome": r.outcome,
                        "duration_ms": r.duration_ms,
                        "trace_id": r.trace_id,
                        "policy_snapshot_id": r.policy_snapshot_id,
                        "fingerprint": r.fingerprint,
                    }
                    for r in rows
                ],
            }
    except Exception as e:  # noqa: BLE001
        logger.warning("audit DB 查询失败，回退 JSONL: {}", e)

    # 回退 JSONL
    if not AUDIT_DIR.exists():
        return {"source": "empty", "events": []}
    events: list[dict] = []
    files = sorted(AUDIT_DIR.glob("*.jsonl"), reverse=True)
    for f in files:
        try:
            for line in reversed(f.read_text(encoding="utf-8").splitlines()):
                if not line.strip():
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if actor_id and (ev.get("actor", {}) or {}).get("id") != actor_id:
                    continue
                if action and ev.get("action") != action:
                    continue
                if decision and ev.get("decision") != decision:
                    continue
                if event_type and ev.get("event_type") != event_type:
                    continue
                events.append(ev)
                if len(events) >= limit:
                    break
        except OSError:
            continue
        if len(events) >= limit:
            break
    return {"source": "jsonl", "events": events}


@router.get("/audit/stats", summary="审计概览统计")
async def audit_stats(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_governance_role),
) -> dict[str, Any]:
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        # 按 decision / event_type 统计
        by_decision = await db.execute(
            select(AuditEventDB.decision, func.count())
            .where(AuditEventDB.ts >= since)
            .group_by(AuditEventDB.decision)
        )
        by_event = await db.execute(
            select(AuditEventDB.event_type, func.count())
            .where(AuditEventDB.ts >= since)
            .group_by(AuditEventDB.event_type)
        )
        return {
            "window_days": days,
            "by_decision": {k or "null": v for k, v in by_decision.all()},
            "by_event_type": {k or "null": v for k, v in by_event.all()},
        }
    except Exception:  # noqa: BLE001
        return {"window_days": days, "by_decision": {}, "by_event_type": {}, "note": "DB 未就绪"}


# ────────────────────────────────────────────────────────────────────
# Confirm Tickets
# ────────────────────────────────────────────────────────────────────
class ApproveBody(BaseModel):
    note: str | None = None
    cosigner_id: str | None = None


class RejectBody(BaseModel):
    reason: str = Field(..., min_length=1, max_length=2000)


@router.get("/confirm-tickets", summary="待 confirm ticket 列表")
async def list_confirm_tickets(
    status_: str | None = Query(None, alias="status"),
    persona: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_governance_role),
) -> dict[str, Any]:
    tenant_id = getattr(user, "tenant_id", None) or getattr(user, "organization_id", None)
    items = await confirm_inbox.list_tickets(
        db,
        tenant_id=str(tenant_id) if tenant_id else None,
        status=status_,
        persona=persona,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            {
                "id": t.id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "expires_at": t.expires_at.isoformat() if t.expires_at else None,
                "requester_id": t.requester_id,
                "requester_role": t.requester_role,
                "persona": t.persona,
                "skill_id": t.skill_id,
                "cookbook_name": t.cookbook_name,
                "action": t.action,
                "resource": t.resource,
                "status": t.status,
                "approver_id": t.approver_id,
                "decision_at": t.decision_at.isoformat() if t.decision_at else None,
                "decision_note": t.decision_note,
                "policy_snapshot_id": t.policy_snapshot_id,
            }
            for t in items
        ],
        "count": len(items),
    }


@router.post("/confirm-tickets/{ticket_id}/approve", summary="批准 ticket")
async def approve_ticket(
    ticket_id: str,
    body: ApproveBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_governance_role),
) -> dict[str, Any]:
    approver = {
        "id": str(getattr(user, "id", "")),
        "role": getattr(user, "role", None) and (user.role.value if hasattr(user.role, "value") else user.role),
        "tenant_id": str(getattr(user, "tenant_id", "") or getattr(user, "organization_id", "")),
    }
    cosigner = None
    if body.cosigner_id:
        cosigner = {"id": body.cosigner_id}
    try:
        result = await confirm_inbox.approve(
            db, ticket_id, approver=approver, note=body.note, cosigner=cosigner,
        )
        await db.commit()
        return result
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except (ValueError, PermissionError) as e:
        raise HTTPException(400, str(e)) from e


@router.post("/confirm-tickets/{ticket_id}/reject", summary="拒绝 ticket")
async def reject_ticket(
    ticket_id: str,
    body: RejectBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_governance_role),
) -> dict[str, Any]:
    approver = {
        "id": str(getattr(user, "id", "")),
        "role": getattr(user, "role", None) and (user.role.value if hasattr(user.role, "value") else user.role),
    }
    try:
        result = await confirm_inbox.reject(db, ticket_id, approver=approver, reason=body.reason)
        await db.commit()
        return result
    except LookupError as e:
        raise HTTPException(404, str(e)) from e
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


# ────────────────────────────────────────────────────────────────────
# Revoked Skills
# ────────────────────────────────────────────────────────────────────
@router.get("/revoked", summary="撤回 skill 列表")
async def revoked_list(user: User = Depends(_require_governance_role)) -> dict[str, Any]:
    if not REVOKED_FILE.exists():
        return {"items": []}
    try:
        items = json.loads(REVOKED_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        items = []
    return {"items": items}


# ────────────────────────────────────────────────────────────────────
# Shadow Runs
# ────────────────────────────────────────────────────────────────────
@router.get("/shadow-runs", summary="Shadow 运行记录列表")
async def shadow_list(
    skill_id: str | None = None,
    status_: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_require_governance_role),
) -> dict[str, Any]:
    try:
        runs = await shadow_runner.list_runs(db, skill_id=skill_id, status=status_, limit=limit)
    except Exception:  # noqa: BLE001
        return {"items": [], "note": "shadow_runs 表未就绪"}
    return {
        "items": [
            {
                "id": r.id,
                "skill_id": r.skill_id,
                "review_version": r.review_version,
                "baseline_version": r.baseline_version,
                "status": r.status,
                "created_at": r.created_at.isoformat(),
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "window_ends_at": r.window_ends_at.isoformat(),
                "total_invocations": r.total_invocations,
                "review_errors": r.review_errors,
                "baseline_errors": r.baseline_errors,
                "divergences": r.divergences,
                "security_violations": r.security_violations,
                "max_error_rate": r.max_error_rate,
            }
            for r in runs
        ],
    }


# ────────────────────────────────────────────────────────────────────
# Decision Dry-Run（合规官在 dashboard 上试跑某个决策路径）
# ────────────────────────────────────────────────────────────────────
class DecideTestBody(BaseModel):
    subject: dict[str, Any]
    action: str
    resource: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)


@router.post("/decide-test", summary="试跑一次 authz.decide（不写审计）")
async def decide_test(
    body: DecideTestBody,
    user: User = Depends(_require_governance_role),
) -> dict[str, Any]:
    res = decide(
        subject=body.subject,
        action=body.action,
        resource=body.resource,
        context=body.context,
    )
    return res.to_dict()


# ────────────────────────────────────────────────────────────────────
# WebSocket — 实时推送 ticket / audit / shadow / lifecycle 事件
# 协议：连接后客户端首条消息发 {"type": "auth", "token": "<bearer>"}；
#       通过认证 + governance role 后进入广播流。
# ────────────────────────────────────────────────────────────────────
@router.websocket("/ws")
async def governance_ws(websocket: WebSocket) -> None:
    """治理 dashboard 实时推送通道。

    认证流程（与 collaboration_ws 同构）：
      1. 客户端连接后立即发 ``{"type": "auth", "token": "..."}``
      2. 服务端校验 token + 角色（super_admin / org_admin / compliance_officer）
      3. 通过 → 推送 ``{"type": "ready"}``；进入广播 loop
      4. 失败 → 推送错误 + close(1008)
    """
    from src.core.security import verify_token  # 延迟 import
    from src.services.governance.realtime import get_broadcaster

    await websocket.accept()

    # 1. auth message
    try:
        msg = await websocket.receive_json()
    except (WebSocketDisconnect, ValueError):
        await websocket.close(code=1008, reason="auth required")
        return

    if not isinstance(msg, dict) or msg.get("type") != "auth" or not msg.get("token"):
        await websocket.send_json({"type": "error", "message": "first message must be {type: auth, token: ...}"})
        await websocket.close(code=1008)
        return

    try:
        payload = verify_token(msg["token"])
    except Exception:  # noqa: BLE001
        await websocket.send_json({"type": "error", "message": "invalid token"})
        await websocket.close(code=1008)
        return

    role = payload.get("role") if isinstance(payload, dict) else getattr(payload, "role", None)
    role_v = role.value if hasattr(role, "value") else role
    allowed = {"super_admin", "admin", "org_admin", "compliance_officer"}
    if role_v not in allowed:
        await websocket.send_json({"type": "error", "message": "role not allowed"})
        await websocket.close(code=1008)
        return

    tenant_id = (payload.get("tenant_id") if isinstance(payload, dict) else None) or None
    bc = get_broadcaster()
    queue = bc.subscribe(queue_size=200)

    await websocket.send_json({
        "type": "ready",
        "subscriber_count": bc.subscriber_count,
        "your_role": role_v,
        "tenant_filter": tenant_id,
    })

    try:
        while True:
            event = await queue.get()
            if tenant_id and event.tenant_id and event.tenant_id != tenant_id:
                continue
            try:
                await websocket.send_text(event.to_json())
            except (WebSocketDisconnect, RuntimeError):
                break
    finally:
        bc.unsubscribe(queue)
        logger.info("governance_ws: disconnect role={} tenant={}", role_v, tenant_id)
