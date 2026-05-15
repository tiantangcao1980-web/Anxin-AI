# -*- coding: utf-8 -*-
"""
Celery 周期任务：审计 JSONL ↔ DB 对账（每小时一次）

入口：
    from src.services.task_orchestrator.managed_agents import audit_reconcile
    audit_reconcile.run.delay()

Beat 调度由 register_beat_schedule 注入（见 __init__.py）。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from loguru import logger

from src.services.governance.audit import _db_write_async
from src.services.task_orchestrator.celery_app import celery_app

REPO_ROOT = Path(__file__).resolve().parents[5]
AUDIT_DIR = REPO_ROOT / ".claude" / "audit"


def _canonical(o: object) -> str:
    return json.dumps(o, sort_keys=True, ensure_ascii=False, default=str)


def _fingerprint(event: dict) -> str:
    payload = {k: v for k, v in event.items() if k != "fingerprint"}
    return "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _iter_recent_events(since_days: int = 1) -> list[dict]:
    if not AUDIT_DIR.exists():
        return []
    since = dt.date.today() - dt.timedelta(days=since_days)
    out: list[dict] = []
    for p in sorted(AUDIT_DIR.glob("*.jsonl")):
        try:
            day = dt.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if day < since:
            continue
        try:
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        except OSError:
            continue
    return out


@celery_app.task(name="managed_agents.audit_reconcile.run", acks_late=True)
def run(since_days: int = 1) -> dict[str, Any]:
    """每小时跑：把过去 1 天 JSONL 中 DB 未写到的事件 backfill 到 DB；
    同时校验 fingerprint，检出篡改立刻告警。"""
    import asyncio

    async def _job() -> dict[str, Any]:
        from sqlalchemy import select

        from src.core.database import async_session_maker
        from src.models.governance import AuditEventDB

        events = _iter_recent_events(since_days)
        if not events:
            return {"scanned": 0}

        # 1. fingerprint 自校
        tampered: list[str] = []
        for ev in events:
            expected = _fingerprint(ev)
            if ev.get("fingerprint") != expected:
                tampered.append(ev.get("event_id", "?"))

        # 2. DB 已存在的 event_id
        ids = [ev.get("event_id") for ev in events if ev.get("event_id")]
        existing: set[str] = set()
        try:
            async with async_session_maker() as session:
                stmt = select(AuditEventDB.event_id).where(AuditEventDB.event_id.in_(ids))
                res = await session.execute(stmt)
                existing = {r for (r,) in res.all()}
        except Exception as e:  # noqa: BLE001
            logger.warning("audit_reconcile: DB 查询失败 → {}", e)

        # 3. backfill missing
        missing = [ev for ev in events if ev.get("event_id") and ev["event_id"] not in existing]
        for ev in missing:
            try:
                await _db_write_async(ev)
            except Exception as e:  # noqa: BLE001
                logger.warning("audit_reconcile: backfill 失败 {} → {}", ev.get("event_id"), e)

        result = {
            "scanned": len(events),
            "tampered": len(tampered),
            "tampered_ids": tampered[:20],
            "backfilled": len(missing),
            "since_days": since_days,
        }
        if tampered:
            logger.error("audit_reconcile: 检出 {} 条 fingerprint 不一致事件 → {}",
                         len(tampered), tampered[:5])
        else:
            logger.info("audit_reconcile: scanned={} backfilled={}",
                        result["scanned"], result["backfilled"])
        return result

    return asyncio.run(_job())
