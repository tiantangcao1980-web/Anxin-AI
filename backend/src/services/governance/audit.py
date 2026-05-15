# -*- coding: utf-8 -*-
"""
Audit —— 审计日志双写：JSONL 文件 + DB

JSONL 是法证级真相源（append-only，按天文件，签名）；DB 是查询性能层。
约定见 docs/governance/AUDIT-LOG-SPEC.md。

后续 P10：用 `scripts/audit-reconcile.py` 做 JSONL ↔ DB 对账。
"""
from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from loguru import logger

REPO_ROOT = Path(__file__).resolve().parents[4]
AUDIT_DIR = REPO_ROOT / ".claude" / "audit"
SCHEMA_VERSION = 1

_LOCK = threading.Lock()


def _ulid_like() -> str:
    """轻量 ULID 类 event_id（不是真 ULID，避免新依赖）。"""
    return "evt_" + secrets.token_hex(16)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, default=str)


def _fingerprint(event: dict) -> str:
    payload = {k: v for k, v in event.items() if k != "fingerprint"}
    return "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _today_path() -> Path:
    now = datetime.now(timezone.utc)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    return AUDIT_DIR / f"{now.strftime('%Y-%m-%d')}.jsonl"


def write_event(event: dict) -> str:
    """写一条审计事件到 JSONL（DB 写入由调用方触发或后台 worker 异步同步）。"""
    event = {
        "schema_version": SCHEMA_VERSION,
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_id": event.get("event_id") or _ulid_like(),
        **event,
    }
    event["fingerprint"] = _fingerprint(event)

    line = _canonical(event) + "\n"
    path = _today_path()
    with _LOCK:
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
    # DB 异步写（如果 event loop 在跑）
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_db_write_async(event))
    except RuntimeError:
        # 没在 async context — 单跑 JSONL 即可；DB 由后台 reconcile worker 补
        pass
    # 治理 dashboard 实时推送
    try:
        from src.services.governance.realtime import publish_audit_event
        publish_audit_event(event)
    except Exception:  # noqa: BLE001 — 推送失败不影响审计写入
        pass
    return event["event_id"]


async def _db_write_async(event: dict) -> None:
    """异步写 DB。失败降级到 JSONL（已写）；不阻塞调用方。

    `audit_events` 表 ORM 见 ``src.models.governance.AuditEventDB``。
    """
    try:
        # 延迟 import 避免循环依赖 + 表未建好时的 import 失败
        import uuid

        from sqlalchemy.exc import OperationalError, ProgrammingError

        from src.core.database import async_session_maker
        from src.models.governance import AuditEventDB

        actor = event.get("actor") or {}
        resource = event.get("resource") or {}
        ts_str = event.get("ts")
        ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now(timezone.utc)

        try:
            async with async_session_maker() as session:
                row = AuditEventDB(
                    id=str(uuid.uuid4()),
                    event_id=event["event_id"],
                    ts=ts_dt,
                    event_type=event.get("event_type", "unknown"),
                    schema_version=event.get("schema_version", SCHEMA_VERSION),
                    actor_id=str(actor.get("id")) if actor.get("id") is not None else None,
                    actor_role=actor.get("role"),
                    tenant_id=str(actor.get("tenant_id")) if actor.get("tenant_id") else None,
                    trace_id=event.get("trace_id"),
                    action=event.get("action"),
                    resource_type=resource.get("type"),
                    resource_id=str(resource.get("id")) if resource.get("id") is not None else None,
                    decision=event.get("decision"),
                    outcome=event.get("outcome"),
                    duration_ms=event.get("duration_ms"),
                    policy_snapshot_id=event.get("policy_snapshot_id"),
                    fingerprint=event["fingerprint"],
                    payload=event,
                )
                session.add(row)
                await session.commit()
        except (OperationalError, ProgrammingError) as e:
            # 表还没建（migration 未跑） / DB 暂不可用 — JSONL 已写，跳过
            logger.warning("audit DB write skipped (table missing or DB down): {}", e.orig if hasattr(e, "orig") else e)
        except (ConnectionError, OSError) as e:
            # 连接失败 — JSONL 已写，跳过
            logger.warning("audit DB write skipped (connection failure): {}", e)
    except Exception:  # noqa: BLE001
        logger.exception("audit DB write 异常（JSONL 仍有完整记录）")


# ──────────────────────────────────────────────────────────────────────
# 装饰器
# ──────────────────────────────────────────────────────────────────────
def audit_log(
    *,
    event_type: str,
    extract_resource: Callable[..., dict] | None = None,
) -> Callable:
    """业务函数装饰器：自动写审计。

    用法::

        @audit_log(event_type="skill.execute")
        async def run_skill(*, subject: dict, skill_id: str, ...) -> dict:
            ...

    业务返回 `{"decision": "ALLOW", "outcome": "success", "resource": {...}}` 形式时
    会自动提取这些字段写审计。
    """
    def deco(fn: Callable) -> Callable:
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def aw(*args: Any, **kwargs: Any) -> Any:
                started = datetime.now(timezone.utc)
                event: dict = {
                    "event_type": event_type,
                    "actor": kwargs.get("subject") or {},
                    "trace_id": kwargs.get("trace_id"),
                }
                try:
                    result = await fn(*args, **kwargs)
                    event.update({
                        "decision": (result or {}).get("decision"),
                        "outcome": (result or {}).get("outcome", "success"),
                        "resource": (result or {}).get("resource")
                                    or (extract_resource(*args, **kwargs) if extract_resource else None),
                        "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                    })
                    write_event(event)
                    return result
                except Exception as e:  # noqa: BLE001
                    event.update({
                        "outcome": "failure",
                        "error": repr(e),
                        "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                    })
                    write_event(event)
                    raise
            return aw

        @functools.wraps(fn)
        def sw(*args: Any, **kwargs: Any) -> Any:
            started = datetime.now(timezone.utc)
            event: dict = {
                "event_type": event_type,
                "actor": kwargs.get("subject") or {},
                "trace_id": kwargs.get("trace_id"),
            }
            try:
                result = fn(*args, **kwargs)
                event.update({
                    "decision": (result or {}).get("decision") if isinstance(result, dict) else None,
                    "outcome": "success",
                    "resource": (result or {}).get("resource") if isinstance(result, dict) else None,
                    "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                })
                write_event(event)
                return result
            except Exception as e:  # noqa: BLE001
                event.update({
                    "outcome": "failure",
                    "error": repr(e),
                    "duration_ms": int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
                })
                write_event(event)
                raise
        return sw
    return deco


__all__ = ["audit_log", "write_event"]
