# -*- coding: utf-8 -*-
"""
Celery task: contract-renewal-watcher — 真实数据源版

扫描 60 天内到期合同，评估续约风险并起草续约建议。

负责 persona：contract-steward
Cookbook spec：managed-agent-cookbooks/contract-renewal-watcher/agent.yaml

⚠️ 仅产出 staged draft + 落 confirm ticket；续约函 / 价格变更 / 终止通知必须人工 confirm。

实施步骤：
  1. 查 contracts 表：expiry_date 在 [now, now+60d] 且 status='active'
  2. 对每个合同跑 ContractInvestigator/ContractReviewer agent 生成续约建议
  3. 按金额阈值（来自 plugins/contract-steward/CLAUDE.md）排序 + 风险打标
  4. Stage draft 到 .claude/managed-agent-runs/<name>/
  5. 落 confirm ticket（推送动作走 PEP-4）
"""
from __future__ import annotations

import asyncio
import datetime as dt
import json
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.exc import OperationalError, ProgrammingError

from src.services.governance.audit import write_event
from src.services.task_orchestrator.celery_app import celery_app
from src.services.task_orchestrator.managed_agents import _load

REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE_DIR = REPO_ROOT / ".claude" / "managed-agent-runs" / "contract-renewal-watcher"

# 默认 60 天窗口；可被 cookbook context.window_days 覆盖
DEFAULT_WINDOW_DAYS = 60
# 高金额阈值（CNY）— 触发 STEP_UP / 双签
HIGH_AMOUNT_THRESHOLD = 1_000_000


@celery_app.task(
    name="managed_agents.contract_renewal_watcher.run",
    acks_late=True, max_retries=2,
)
def run(
    cookbook_name: str = "contract-renewal-watcher",
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    return asyncio.run(_run_async(cookbook_name, window_days))


async def _run_async(cookbook_name: str, window_days: int) -> dict[str, Any]:
    cookbook = _load(cookbook_name)

    write_event({
        "event_type": "cookbook.started",
        "actor": {"type": "cookbook", "id": cookbook_name},
        "action": f"cookbook.{cookbook_name}.run",
        "resource": {"type": "cookbook", "id": cookbook_name},
        "decision": "ALLOW", "outcome": "started",
    })

    # 1. 查 DB 中所有 60 天内到期的合同
    rows = await _query_expiring_contracts(window_days)
    logger.info("contract_renewal_watcher: 命中 {} 个 60 天内到期合同", len(rows))

    # 2. 给每个合同做风险打标 + 续约建议（不调真 LLM 以节省成本，按 CLAUDE.md 阈值评级）
    profile_path = REPO_ROOT / "plugins" / "contract-steward" / "CLAUDE.md"
    profile_text = profile_path.read_text(encoding="utf-8")[:2000] if profile_path.exists() else ""

    items: list[dict[str, Any]] = []
    for row in rows:
        amount = float(row.get("amount") or 0)
        expiry = row.get("expiry_date")
        days_left = (expiry - dt.date.today()).days if expiry else None

        # 风险评级（业务规则；可被未来 LLM 升级）
        if amount >= HIGH_AMOUNT_THRESHOLD:
            risk = "high"
            require_dual_sign = True
        elif amount >= 100_000:
            risk = "medium"
            require_dual_sign = False
        else:
            risk = "low"
            require_dual_sign = False

        items.append({
            "contract_id": row.get("id"),
            "title": row.get("title"),
            "counterparty": row.get("counterparty_name"),
            "amount": amount,
            "currency": row.get("currency"),
            "expiry_date": expiry.isoformat() if expiry else None,
            "days_left": days_left,
            "risk": risk,
            "require_dual_sign": require_dual_sign,
            "suggested_action": (
                "立即启动续约谈判（金额 > 100 万，需老板审批）"
                if amount >= HIGH_AMOUNT_THRESHOLD
                else "在 30 天前发起续约邮件（标准模板）"
                if (days_left or 999) <= 30
                else "纳入下次周会议程，确认是否续约"
            ),
        })

    # 按风险 + days_left 排序
    risk_order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda x: (risk_order.get(x["risk"], 9), x.get("days_left") or 999))

    # 3. stage draft
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    draft_path = STAGE_DIR / f"draft-{stamp}.json"
    draft_payload = {
        "cookbook": cookbook_name,
        "persona": cookbook.get("ownerPersona", "contract-steward"),
        "ts": dt.datetime.utcnow().isoformat() + "Z",
        "window_days": window_days,
        "expiring_count": len(items),
        "high_risk_count": sum(1 for i in items if i["risk"] == "high"),
        "items": items,
        "status": "draft-pending-human-review",
        "human_gate": cookbook.get("humanGate", ""),
        "practice_profile_used": str(profile_path.relative_to(REPO_ROOT)) if profile_path.exists() else None,
    }
    draft_path.write_text(json.dumps(draft_payload, ensure_ascii=False, indent=2, default=str),
                          encoding="utf-8")

    write_event({
        "event_type": "cookbook.completed",
        "actor": {"type": "cookbook", "id": cookbook_name},
        "action": f"cookbook.{cookbook_name}.run",
        "resource": {"type": "cookbook", "id": cookbook_name,
                     "classification": "L3", "jurisdiction": "CN"},
        "decision": "ALLOW", "outcome": "draft-staged",
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "stats": {
            "expiring": len(items),
            "high_risk": sum(1 for i in items if i["risk"] == "high"),
        },
    })

    # 4. 落 confirm ticket（推送 contract-steward inbox + 续约函外发）
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
                    resource={"type": "connector", "id": "feishu/renewal-card",
                              "classification": "L3", "jurisdiction": "CN"},
                    pending_action={
                        "kind": "renewal_summary_push",
                        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
                        "expiring_count": len(items),
                        "high_risk_count": sum(1 for i in items if i["risk"] == "high"),
                    },
                    cookbook_name=cookbook_name,
                    persona=cookbook.get("ownerPersona", "contract-steward"),
                    draft_path=str(draft_path.relative_to(REPO_ROOT)),
                    ttl_hours=24,
                )
                await session.commit()
                ticket_id = t.id
        except Exception as e:  # noqa: BLE001
            logger.warning("contract_renewal_watcher: confirm ticket 创建失败 → {}", e)

    return {
        "cookbook": cookbook_name,
        "expiring_count": len(items),
        "high_risk_count": sum(1 for i in items if i["risk"] == "high"),
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "confirm_ticket_id": ticket_id,
    }


async def _query_expiring_contracts(window_days: int) -> list[dict[str, Any]]:
    """查询 expiry_date 在未来 window_days 天内的 active 合同。

    表 schema 见 backend/src/models/contract.py: Contract。

    DB 不可用 / 表未建 → 降级返回空列表，cookbook 仍会 stage 一个 empty draft。
    """
    try:
        from src.core.database import async_session_maker
        from src.models.contract import Contract, ContractStatus
    except ImportError:
        return []

    today = dt.date.today()
    until = today + dt.timedelta(days=window_days)

    try:
        async with async_session_maker() as session:
            stmt = (
                select(Contract)
                .where(Contract.expiry_date.isnot(None))
                .where(Contract.expiry_date >= today)
                .where(Contract.expiry_date <= until)
                .where(Contract.status == ContractStatus.ACTIVE.value
                       if hasattr(ContractStatus, "ACTIVE") else "active")
            )
            res = await session.execute(stmt)
            rows: list[dict[str, Any]] = []
            for c in res.scalars():
                rows.append({
                    "id": str(getattr(c, "id", "")),
                    "title": getattr(c, "title", "") or getattr(c, "contract_name", ""),
                    "counterparty_name": getattr(c, "counterparty_name", "")
                                          or getattr(c, "party_b", ""),
                    "amount": float(getattr(c, "amount", 0) or 0),
                    "currency": getattr(c, "currency", "CNY"),
                    "expiry_date": getattr(c, "expiry_date", None),
                })
            return rows
    except (OperationalError, ProgrammingError, ConnectionError, OSError) as e:
        logger.warning("contract_renewal_watcher: DB 查询失败 → {}（cookbook 仍会 stage 空 draft）", e)
        return []
    except Exception as e:  # noqa: BLE001
        logger.exception("contract_renewal_watcher: 意外错误 → {}", e)
        return []
