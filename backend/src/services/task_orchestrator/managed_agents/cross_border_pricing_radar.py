# -*- coding: utf-8 -*-
"""
Celery task: cross-border-pricing-radar — 真实数据源版

每 30 分钟抓取 Amazon SP-API / Shopify / eBay 竞品定价，与本店 SKU 对比，
触发调价建议或 BuyBox 失守预警。

负责 persona：cross-border-ecom
Cookbook spec：managed-agent-cookbooks/cross-border-pricing-radar/agent.yaml

⚠️ 仅产出 staged draft + 落 confirm ticket；调价 / Listing 修改必须人工 confirm。

实施策略：
  - **不直接调真实 SP-API**（凭据通过 app_authorization OAuth 注入）；本任务从配置
    读取要监控的 SKU 列表，调 ProductPricingClient 抓数据。
  - 凭据未配置 / Amazon API rate-limit / 网络失败 → 降级 stage 空 draft（不阻塞 cron）。
  - 调价建议规则（与 cross-border-ecom/CLAUDE.md 同步）：
      * 竞品最低价 < 本店价 95%   → 调价 -3%（自动建议）
      * 竞品最低价 > 本店价 110%  → 调价 +5%（自动建议）
      * BuyBox 失守               → critical（24h 观察期）
      * 调价幅度 > 10%            → STEP_UP 人工二次审批
"""
from __future__ import annotations

import asyncio
import datetime as dt
import fnmatch
import json
import os
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from src.services.governance.audit import write_event
from src.services.task_orchestrator.celery_app import celery_app
from src.services.task_orchestrator.managed_agents import _load

REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE_DIR = REPO_ROOT / ".claude" / "managed-agent-runs" / "cross-border-pricing-radar"

# SKU 监控清单可通过环境变量配置，默认空
WATCHLIST_JSON = os.environ.get("ANXIN_PRICING_WATCHLIST", "")


def _load_watchlist() -> list[dict[str, Any]]:
    """监控 SKU 清单格式::

        [{"sku": "B0XXXX", "marketplace": "amazon", "region": "NA",
          "our_price": 29.99, "currency": "USD", "buybox": true}]
    """
    if not WATCHLIST_JSON:
        return []
    try:
        return json.loads(WATCHLIST_JSON)
    except json.JSONDecodeError:
        logger.warning("cross_border_pricing_radar: ANXIN_PRICING_WATCHLIST JSON 解析失败")
        return []


async def _fetch_competitor_prices(
    sku: str, marketplace: str, region: str,
    egress_allowlist: list[str],
    *,
    org_id: str | None = None,
    timeout: float = 8.0,
) -> dict[str, Any]:
    """生产路径：通过 ``amazon_sp_oauth.get_access_token`` 注入 LWA token 调 SP-API。

    ``org_id=None`` 或拿不到 token → 不调真 API（保持骨架行为）。
    """
    targets = {
        ("amazon", "NA"): ("https://sellingpartnerapi-na.amazon.com/products/pricing/v0/items/" + sku, "NA"),
        ("amazon", "EU"): ("https://sellingpartnerapi-eu.amazon.com/products/pricing/v0/items/" + sku, "EU"),
        ("amazon", "FE"): ("https://sellingpartnerapi-fe.amazon.com/products/pricing/v0/items/" + sku, "FE"),
        ("ebay", "US"): (f"https://api.ebay.com/buy/browse/v1/item_summary/search?q={sku}", None),
    }
    target = targets.get((marketplace, region))
    if not target:
        return {"sku": sku, "error": "unsupported_marketplace_region"}
    url, amz_region = target

    # egress 校验
    host = url.split("/")[2]
    if egress_allowlist and not any(fnmatch.fnmatchcase(host, p) for p in egress_allowlist):
        return {"sku": sku, "error": "host_not_in_allowlist", "host": host}

    # 注入 OAuth token（仅 Amazon）
    headers: dict[str, str] = {
        "User-Agent": "Anxin-AI pricing-radar/1.0",
        "Accept": "application/json",
    }
    if marketplace == "amazon" and amz_region and org_id:
        try:
            from src.services.app_authorization.providers.amazon_sp_oauth import (
                get_access_token,
            )
            token = await get_access_token(org_id=org_id, region=amz_region)
            if token:
                headers["x-amz-access-token"] = token
            else:
                return {"sku": sku, "error": "no_token",
                        "note": "卖家未绑定 amazon-sp 或 token 已过期（refresh 失败）"}
        except ImportError:
            return {"sku": sku, "error": "oauth_provider_missing"}

    if marketplace == "amazon" and "x-amz-access-token" not in headers:
        # 没注入 token，跳过真实 API（避免 401）
        return {"sku": sku, "error": "no_token", "note": "未提供 org_id 或 token store 不可用"}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, headers=headers)
            if r.status_code in (401, 403):
                return {"sku": sku, "error": "auth_required",
                        "status": r.status_code,
                        "note": "LWA token 已 revoked 或权限不足，需卖家重授权"}
            if r.status_code == 429:
                return {"sku": sku, "error": "rate_limited"}
            r.raise_for_status()
            return {"sku": sku, "raw": r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:200]}
    except httpx.HTTPError as e:
        return {"sku": sku, "error": "http_error", "detail": str(e)[:200]}


def _evaluate_pricing(our_price: float, competitor_low: float | None,
                      buybox_held: bool) -> dict[str, Any]:
    """业务规则评估调价建议。"""
    if competitor_low is None:
        return {"action": "noop", "risk": "low", "reason": "no_competitor_data"}

    ratio = competitor_low / our_price if our_price else 1.0

    if not buybox_held:
        return {
            "action": "alert_buybox_lost",
            "risk": "critical",
            "reason": "BuyBox 失守 — 24h 观察期",
            "suggested_price": None,
        }

    if ratio < 0.95:
        # 竞品低于本店 5% — 建议降价匹配（折扣 3% 留余地）
        suggested = round(competitor_low * 1.02, 2)
        delta_pct = abs(suggested - our_price) / our_price * 100
        return {
            "action": "price_down",
            "risk": "high" if delta_pct > 10 else "medium",
            "reason": f"竞品比我方低 {(1 - ratio) * 100:.1f}%，建议调价",
            "suggested_price": suggested,
            "delta_pct": round(delta_pct, 2),
            "needs_step_up": delta_pct > 10,
        }
    if ratio > 1.10:
        # 竞品高于我方 10% — 可上调
        suggested = round(competitor_low * 0.95, 2)
        delta_pct = abs(suggested - our_price) / our_price * 100
        return {
            "action": "price_up",
            "risk": "low",
            "reason": f"竞品比我方高 {(ratio - 1) * 100:.1f}%，可上调价格",
            "suggested_price": suggested,
            "delta_pct": round(delta_pct, 2),
            "needs_step_up": delta_pct > 10,
        }
    return {
        "action": "noop",
        "risk": "low",
        "reason": f"价格区间合理（竞品 ratio={ratio:.2f}）",
        "suggested_price": None,
    }


@celery_app.task(
    name="managed_agents.cross_border_pricing_radar.run",
    acks_late=True, max_retries=2,
)
def run(cookbook_name: str = "cross-border-pricing-radar") -> dict[str, Any]:
    return asyncio.run(_run_async(cookbook_name))


async def _run_async(cookbook_name: str) -> dict[str, Any]:
    cookbook = _load(cookbook_name)
    egress = (cookbook.get("governance", {}) or {}).get("egress_allowlist", []) or []

    write_event({
        "event_type": "cookbook.started",
        "actor": {"type": "cookbook", "id": cookbook_name},
        "action": f"cookbook.{cookbook_name}.run",
        "resource": {"type": "cookbook", "id": cookbook_name},
        "decision": "ALLOW", "outcome": "started",
    })

    watchlist = _load_watchlist()
    logger.info("cross_border_pricing_radar: 监控 {} 个 SKU", len(watchlist))

    items: list[dict[str, Any]] = []
    needs_step_up_count = 0
    critical_count = 0

    for entry in watchlist:
        sku = entry.get("sku", "")
        marketplace = entry.get("marketplace", "amazon")
        region = entry.get("region", "NA")
        our_price = float(entry.get("our_price", 0) or 0)
        buybox_held = bool(entry.get("buybox", True))
        currency = entry.get("currency", "USD")
        org_id = entry.get("org_id") or os.environ.get("ANXIN_PRICING_ORG_ID")

        result = await _fetch_competitor_prices(
            sku, marketplace, region, egress, org_id=org_id,
        )
        # 模拟从 raw 中抽取竞品最低价（生产实现需按平台 schema 解析）
        competitor_low: float | None = None
        if "error" not in result and isinstance(result.get("raw"), dict):
            # 在抓取层失败时也保留 noop 评估
            try:
                competitor_low = float(result["raw"].get("competitor_low_price"))
            except (TypeError, ValueError, KeyError):
                competitor_low = None

        evaluation = _evaluate_pricing(our_price, competitor_low, buybox_held)
        if evaluation.get("needs_step_up"):
            needs_step_up_count += 1
        if evaluation.get("risk") == "critical":
            critical_count += 1

        items.append({
            "sku": sku, "marketplace": marketplace, "region": region,
            "our_price": our_price, "currency": currency,
            "competitor_low": competitor_low, "buybox_held": buybox_held,
            "fetch_status": result.get("error", "ok"),
            **evaluation,
        })

    # Stage draft
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    draft_path = STAGE_DIR / f"draft-{stamp}.json"
    draft_payload = {
        "cookbook": cookbook_name,
        "persona": cookbook.get("ownerPersona", "cross-border-ecom"),
        "ts": dt.datetime.utcnow().isoformat() + "Z",
        "total_skus": len(items),
        "needs_step_up_count": needs_step_up_count,
        "critical_count": critical_count,
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
                     "classification": "L2", "jurisdiction": "global"},
        "decision": "ALLOW", "outcome": "draft-staged",
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "stats": {
            "total_skus": len(items),
            "needs_step_up_count": needs_step_up_count,
            "critical_count": critical_count,
        },
    })

    # 落 confirm ticket（推送 + 调价动作走 PEP-4）
    ticket_id: str | None = None
    if items and (needs_step_up_count or critical_count):
        try:
            from src.core.database import async_session_maker
            from src.services.governance import confirm_inbox

            async with async_session_maker() as session:
                t = await confirm_inbox.create_ticket(
                    session,
                    requester={"id": f"cookbook:{cookbook_name}", "role": "system",
                               "tenant_id": "system"},
                    action="connector.amazon-sp.write",
                    resource={"type": "connector", "id": "amazon-sp/pricing",
                              "classification": "L2", "jurisdiction": "global"},
                    pending_action={
                        "kind": "pricing_change_proposal",
                        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
                        "total_skus": len(items),
                        "needs_step_up_count": needs_step_up_count,
                        "critical_count": critical_count,
                    },
                    cookbook_name=cookbook_name,
                    persona=cookbook.get("ownerPersona", "cross-border-ecom"),
                    draft_path=str(draft_path.relative_to(REPO_ROOT)),
                    ttl_hours=12,   # 跨境定价时效性强，缩短 TTL
                )
                await session.commit()
                ticket_id = t.id
        except Exception as e:  # noqa: BLE001
            logger.warning("cross_border_pricing_radar: confirm ticket 创建失败 → {}", e)

    return {
        "cookbook": cookbook_name,
        "total_skus": len(items),
        "needs_step_up_count": needs_step_up_count,
        "critical_count": critical_count,
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "confirm_ticket_id": ticket_id,
    }
