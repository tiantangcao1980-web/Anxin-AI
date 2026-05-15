# -*- coding: utf-8 -*-
"""
ShadowRunner —— Skill REVIEW → PUBLISHED 前的 24h 双跑录制

机制：
  1. start_shadow(skill_id, review_version, window_hours=24) 开启窗口
  2. 真用户每次调 PUBLISHED 版 skill 时，executor 通过 hook 顺便跑一遍 REVIEW 版
  3. 对比输出 / tool 调用 / PII findings / 安全事件
  4. 写 `shadow_runs.samples`（最多保留 200 条样本）
  5. 窗口结束 → finalize_shadow() 计算 PASSED / FAILED
  6. `skill_lifecycle.transition(REVIEW → PUBLISHED)` 的 `shadow_run_clean` gate
     调 ``shadow_passed(skill_id)`` 回查

入口：
  - record_invocation(...)        每次调用顺便录一条
  - start_shadow / finalize_shadow 窗口管理
  - shadow_passed(skill_id) → bool 给 lifecycle gate 用
"""
from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.governance import ShadowRun, ShadowRunStatus
from src.services.governance.audit import write_event
from src.services.governance.policy_loader import get_policy

DEFAULT_WINDOW_HOURS = 24
MAX_SAMPLES = 200


# ─────────────────────────────────────────────────────────────────────
# 窗口管理
# ─────────────────────────────────────────────────────────────────────
async def start_shadow(
    db: AsyncSession,
    *,
    skill_id: str,
    review_version: str,
    baseline_version: str | None = None,
    window_hours: int | None = None,
) -> ShadowRun:
    policy = get_policy().skill_lifecycle.get("thresholds", {})
    window_hours = window_hours or int(policy.get("shadow_run_hours", DEFAULT_WINDOW_HOURS))
    max_err = float(policy.get("shadow_max_error_rate", 0.05))

    now = datetime.now(UTC)
    run = ShadowRun(
        id="shrun_" + secrets.token_hex(16),
        created_at=now,
        skill_id=skill_id,
        review_version=review_version,
        baseline_version=baseline_version,
        window_started_at=now,
        window_ends_at=now + timedelta(hours=window_hours),
        status=ShadowRunStatus.running.value,
        max_error_rate=max_err,
        samples=[],
    )
    db.add(run)
    await db.flush()
    write_event({
        "event_type": "shadow.started",
        "resource": {"type": "skill", "id": skill_id, "version": review_version},
        "decision": "ALLOW",
        "outcome": "started",
        "shadow_run_id": run.id,
        "window_hours": window_hours,
    })
    logger.info("Shadow started skill={} review={} window={}h", skill_id, review_version, window_hours)
    return run


async def finalize_shadow(db: AsyncSession, *, run_id: str) -> ShadowRun:
    run = await _get_run(db, run_id)
    if run.status != ShadowRunStatus.running.value:
        return run

    total = run.total_invocations or 0
    review_err = run.review_errors or 0
    sec_violations = run.security_violations or 0
    err_rate = (review_err / total) if total else 0.0

    passed = (err_rate <= run.max_error_rate) and (sec_violations == 0) and total >= 1
    run.status = (ShadowRunStatus.passed if passed else ShadowRunStatus.failed).value
    run.ended_at = datetime.now(UTC)
    await db.flush()

    write_event({
        "event_type": "shadow.finalized",
        "resource": {"type": "skill", "id": run.skill_id, "version": run.review_version},
        "decision": "ALLOW" if passed else "DENY",
        "outcome": "passed" if passed else "failed",
        "shadow_run_id": run.id,
        "stats": {
            "total_invocations": total,
            "review_errors": review_err,
            "baseline_errors": run.baseline_errors,
            "divergences": run.divergences,
            "security_violations": sec_violations,
            "error_rate": err_rate,
            "max_error_rate": run.max_error_rate,
        },
    })
    logger.info("Shadow finalized skill={} → {} err_rate={:.4f}",
                run.skill_id, run.status, err_rate)
    return run


# ─────────────────────────────────────────────────────────────────────
# 录入：在 skill_executor 调用 PUBLISHED 版后，把对照 REVIEW 版的结果写入
# ─────────────────────────────────────────────────────────────────────
async def record_invocation(
    db: AsyncSession,
    *,
    skill_id: str,
    input_hash: str,
    review_output_hash: str | None,
    baseline_output_hash: str | None,
    review_error: bool = False,
    baseline_error: bool = False,
    divergence_type: str | None = None,
    security_violation: bool = False,
    pii_findings: list[str] | None = None,
    trace_id: str | None = None,
) -> ShadowRun | None:
    """录一条 shadow 样本（如果当前 skill 有 running 窗口）。"""
    stmt = (
        select(ShadowRun)
        .where(
            ShadowRun.skill_id == skill_id,
            ShadowRun.status == ShadowRunStatus.running.value,
        )
        .order_by(ShadowRun.created_at.desc())
    )
    try:
        res = await db.execute(stmt)
    except (OperationalError, ProgrammingError):
        # 表没建好 — 跳过
        return None
    run = res.scalars().first()
    if run is None:
        return None

    # 过期了？顺手 finalize
    if datetime.now(UTC) >= run.window_ends_at:
        return await finalize_shadow(db, run_id=run.id)

    run.total_invocations = (run.total_invocations or 0) + 1
    if review_error:
        run.review_errors = (run.review_errors or 0) + 1
    if baseline_error:
        run.baseline_errors = (run.baseline_errors or 0) + 1
    if divergence_type:
        run.divergences = (run.divergences or 0) + 1
    if security_violation:
        run.security_violations = (run.security_violations or 0) + 1

    samples: list[dict[str, Any]] = list(run.samples or [])
    if len(samples) < MAX_SAMPLES:
        samples.append({
            "trace_id": trace_id,
            "input_hash": input_hash,
            "review_output_hash": review_output_hash,
            "baseline_output_hash": baseline_output_hash,
            "divergence_type": divergence_type,
            "review_error": review_error,
            "baseline_error": baseline_error,
            "security_violation": security_violation,
            "pii_findings": pii_findings or [],
            "ts": datetime.now(UTC).isoformat(),
        })
        run.samples = samples
    await db.flush()
    return run


# ─────────────────────────────────────────────────────────────────────
# lifecycle gate 入口
# ─────────────────────────────────────────────────────────────────────
async def shadow_passed(db: AsyncSession, *, skill_id: str, version: str) -> bool:
    """`skill_lifecycle.transition` 的 ``shadow_run_clean`` gate 调用。"""
    stmt = (
        select(ShadowRun)
        .where(
            ShadowRun.skill_id == skill_id,
            ShadowRun.review_version == version,
        )
        .order_by(ShadowRun.created_at.desc())
    )
    res = await db.execute(stmt)
    run = res.scalars().first()
    if run is None:
        return False
    if run.status == ShadowRunStatus.running.value:
        # 还没结束 → finalize 看是否能放行
        run = await finalize_shadow(db, run_id=run.id)
    return run.status == ShadowRunStatus.passed.value


# ─────────────────────────────────────────────────────────────────────
# query
# ─────────────────────────────────────────────────────────────────────
async def list_runs(
    db: AsyncSession,
    *,
    skill_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[ShadowRun]:
    stmt = select(ShadowRun).order_by(ShadowRun.created_at.desc())
    if skill_id:
        stmt = stmt.where(ShadowRun.skill_id == skill_id)
    if status:
        stmt = stmt.where(ShadowRun.status == status)
    stmt = stmt.limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars())


async def _get_run(db: AsyncSession, run_id: str) -> ShadowRun:
    stmt = select(ShadowRun).where(ShadowRun.id == run_id)
    res = await db.execute(stmt)
    run = res.scalar_one_or_none()
    if run is None:
        raise LookupError(f"ShadowRun not found: {run_id}")
    return run


__all__ = [
    "start_shadow",
    "finalize_shadow",
    "record_invocation",
    "shadow_passed",
    "list_runs",
]
