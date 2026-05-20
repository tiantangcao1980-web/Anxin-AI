# -*- coding: utf-8 -*-
"""
Celery task: ar-aging-watcher — 真实数据源版

对接 invoices 表抓取应收账款，按账龄分级生成催收草稿。

负责 persona：finance-tax-advisor
Cookbook spec：managed-agent-cookbooks/ar-aging-watcher/agent.yaml

⚠️ 仅产出 staged draft + 落 confirm ticket；催收函外发必须人工 confirm。

账龄分级：
  0-30 d   : 正常
  31-60 d  : 一级提醒（电话 / 邮件）
  61-90 d  : 二级提醒（律师函）
  > 90 d   : 法律风险 — 升级 lead_counsel + 评估诉讼
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.services.governance.audit import write_event
from src.services.task_orchestrator.celery_app import celery_app
from src.services.task_orchestrator.managed_agents import _load

REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE_DIR = REPO_ROOT / ".claude" / "managed-agent-runs" / "ar-aging-watcher"

# 账龄分桶
AGING_BUCKETS = [
    (0, 30, "current", "low", "正常账期，无需催收"),
    (31, 60, "30d", "medium", "一级提醒：电话 + 邮件确认付款时间"),
    (61, 90, "60d", "high", "二级提醒：发律师函，CC 客户负责人"),
    (91, 180, "90d", "critical", "评估诉讼可行性；升级 lead_counsel 决策"),
    (181, 99999, "180d+", "critical", "高诉讼优先级；考虑保全 / 强制执行"),
]


def _bucket(days_overdue: int) -> tuple[str, str, str]:
    for lo, hi, name, risk, action in AGING_BUCKETS:
        if lo <= days_overdue <= hi:
            return name, risk, action
    return "180d+", "critical", "立即升级"


@celery_app.task(
    name="managed_agents.ar_aging_watcher.run",
    acks_late=True, max_retries=2,
)
def run(cookbook_name: str = "ar-aging-watcher") -> dict[str, Any]:
    return asyncio.run(_run_async(cookbook_name))


async def _run_async(cookbook_name: str) -> dict[str, Any]:
    cookbook = _load(cookbook_name)
    write_event({
        "event_type": "cookbook.started",
        "actor": {"type": "cookbook", "id": cookbook_name},
        "action": f"cookbook.{cookbook_name}.run",
        "resource": {"type": "cookbook", "id": cookbook_name},
        "decision": "ALLOW", "outcome": "started",
    })

    rows = await _query_overdue_invoices()
    logger.info("ar_aging_watcher: 命中 {} 个已开未付发票", len(rows))

    today = dt.date.today()
    items: list[dict[str, Any]] = []
    by_bucket: dict[str, int] = defaultdict(int)
    by_bucket_amount: dict[str, float] = defaultdict(float)
    high_risk_amount = 0.0

    for r in rows:
        due = r.get("due_date")
        days_overdue = (today - due).days if due else 0
        if days_overdue < 0:
            continue  # 未到期跳过
        bucket, risk, action_text = _bucket(days_overdue)
        amount = float(r.get("total_amount") or 0)
        by_bucket[bucket] += 1
        by_bucket_amount[bucket] += amount
        if risk in ("high", "critical"):
            high_risk_amount += amount

        items.append({
            "invoice_id": r.get("id"),
            "invoice_number": r.get("number"),
            "client_name": r.get("client_name"),
            "amount": amount,
            "due_date": due.isoformat() if due else None,
            "days_overdue": days_overdue,
            "bucket": bucket,
            "risk": risk,
            "suggested_action": action_text,
            "status": r.get("status"),
        })

    risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items.sort(key=lambda x: (risk_order.get(x["risk"], 9), -(x["days_overdue"] or 0)))

    # Stage draft
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    draft_path = STAGE_DIR / f"draft-{stamp}.json"
    draft_payload = {
        "cookbook": cookbook_name,
        "persona": cookbook.get("ownerPersona", "finance-tax-advisor"),
        "ts": dt.datetime.utcnow().isoformat() + "Z",
        "total_overdue": len(items),
        "high_risk_count": sum(1 for i in items if i["risk"] in ("high", "critical")),
        "high_risk_amount_cny": high_risk_amount,
        "by_bucket_count": dict(by_bucket),
        "by_bucket_amount": {k: float(v) for k, v in by_bucket_amount.items()},
        "items": items,
        "status": "draft-pending-human-review",
        "human_gate": cookbook.get("humanGate", ""),
    }
    draft_path.write_text(
        json.dumps(draft_payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    write_event({
        "event_type": "cookbook.completed",
        "actor": {"type": "cookbook", "id": cookbook_name},
        "action": f"cookbook.{cookbook_name}.run",
        "resource": {"type": "cookbook", "id": cookbook_name,
                     "classification": "L3", "jurisdiction": "CN"},
        "decision": "ALLOW", "outcome": "draft-staged",
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "stats": {
            "total_overdue": len(items),
            "high_risk_count": sum(1 for i in items if i["risk"] in ("high", "critical")),
            "high_risk_amount_cny": high_risk_amount,
        },
    })

    ticket_id: str | None = None
    if items:
        try:
            from src.core.database import async_session_maker
            from src.services.governance import confirm_inbox

            async with async_session_maker() as session:
                t = await confirm_inbox.create_ticket(
                    session,
                    requester={"id": f"cookbook:{cookbook_name}", "role": "system",
                               "tenant_id": "system"},
                    action="connector.feishu.send",
                    resource={"type": "connector", "id": "feishu/ar-aging-card",
                              "classification": "L3", "jurisdiction": "CN"},
                    pending_action={
                        "kind": "ar_aging_summary_push",
                        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
                        "total_overdue": len(items),
                        "high_risk_count": sum(1 for i in items if i["risk"] in ("high", "critical")),
                        "high_risk_amount_cny": high_risk_amount,
                    },
                    context={"amount_cny": int(high_risk_amount)},
                    cookbook_name=cookbook_name,
                    persona=cookbook.get("ownerPersona", "finance-tax-advisor"),
                    draft_path=str(draft_path.relative_to(REPO_ROOT)),
                    ttl_hours=24,
                )
                await session.commit()
                ticket_id = t.id
        except Exception as e:  # noqa: BLE001
            logger.warning("ar_aging_watcher: confirm ticket 创建失败 → {}", e)

    return {
        "cookbook": cookbook_name,
        "total_overdue": len(items),
        "high_risk_count": sum(1 for i in items if i["risk"] in ("high", "critical")),
        "high_risk_amount_cny": high_risk_amount,
        "by_bucket_count": dict(by_bucket),
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "confirm_ticket_id": ticket_id,
    }


async def _query_overdue_invoices() -> list[dict[str, Any]]:
    try:
        from src.core.database import async_session_maker
        from src.models.firm_management import Invoice
    except ImportError:
        return []

    try:
        async with async_session_maker() as session:
            stmt = select(Invoice).where(Invoice.status.in_(["sent", "overdue"]))
            res = await session.execute(stmt)
            rows: list[dict[str, Any]] = []
            for inv in res.scalars():
                rows.append({
                    "id": str(getattr(inv, "id", "")),
                    "number": getattr(inv, "number", ""),
                    "client_name": getattr(inv, "client_name", ""),
                    "total_amount": float(getattr(inv, "total_amount", 0) or 0),
                    "due_date": getattr(inv, "due_date", None),
                    "status": getattr(inv, "status", ""),
                })
            return rows
    except (OperationalError, ProgrammingError, ConnectionError, OSError) as e:
        logger.warning("ar_aging_watcher: DB 查询失败 → {}", e)
        return []
    except Exception as e:  # noqa: BLE001
        logger.exception("ar_aging_watcher: 意外错误 → {}", e)
        return []
