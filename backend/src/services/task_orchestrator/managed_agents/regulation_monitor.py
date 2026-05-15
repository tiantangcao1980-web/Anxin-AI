# -*- coding: utf-8 -*-
"""
Celery task: regulation-monitor — 真实数据源版（取代占位实现）

每日扫描人大 / 国务院 / 市场监管总局公告，识别新法规并生成合规变更摘要草稿。

负责 persona：legal-advisor
Cookbook spec：managed-agent-cookbooks/regulation-monitor/agent.yaml

⚠️ 仅产出 staged draft；推送 / 外发动作必须通过 confirm_tickets 走人工 confirm。

实施步骤：
  1. httpx 抓取数据源（egress_allowlist 校验）
  2. 正则抽取条目（不依赖 bs4）
  3. 与历史指纹做 diff，只保留新增条目
  4. 调 LegalResearchAgent 生成中文摘要（注入 plugins/legal-advisor/CLAUDE.md 画像）
  5. Stage draft 到 .claude/managed-agent-runs/<name>/
  6. 落 confirm ticket（推送动作走 PEP-4）
"""
from __future__ import annotations

import asyncio
import datetime as dt
import fnmatch
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from src.services.governance.audit import write_event
from src.services.task_orchestrator.celery_app import celery_app
from src.services.task_orchestrator.managed_agents import _load

REPO_ROOT = Path(__file__).resolve().parents[5]
STAGE_DIR = REPO_ROOT / ".claude" / "managed-agent-runs" / "regulation-monitor"
FINGERPRINT_FILE = STAGE_DIR / ".seen-fingerprints.json"


SOURCES: list[dict[str, str]] = [
    {"name": "国务院公报", "url": "https://www.gov.cn/zhengce/zuixin.htm", "host": "www.gov.cn"},
    {"name": "市场监督管理总局", "url": "https://www.samr.gov.cn/zw/zfxxgk/", "host": "www.samr.gov.cn"},
    {"name": "人大法规库", "url": "http://www.npc.gov.cn/npc/c2/", "host": "www.npc.gov.cn"},
]


async def _fetch(url: str, timeout: float = 15.0) -> str:
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        r = await client.get(url, headers={
            "User-Agent": "Anxin-AI regulation-monitor/1.0",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        r.raise_for_status()
        return r.text


_TITLE_RX = re.compile(r"<a[^>]+href=['\"]([^'\"]+)['\"][^>]*>([^<]{8,120})</a>", re.IGNORECASE)
_DATE_RX = re.compile(r"20\d{2}[-./年]\d{1,2}[-./月]\d{1,2}")


def _extract_items(html: str, base_url: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in _TITLE_RX.finditer(html):
        url = m.group(1)
        title = m.group(2).strip()
        if len(title) < 10 or not re.search(r"[一-鿿]", title):
            continue
        if url.startswith("//"):
            url = "https:" + url
        elif url.startswith("/"):
            from urllib.parse import urljoin
            url = urljoin(base_url, url)
        elif not url.startswith("http"):
            continue
        if url in seen:
            continue
        seen.add(url)
        ctx = html[max(0, m.start() - 80):min(len(html), m.end() + 80)]
        d = _DATE_RX.search(ctx)
        out.append({"title": title, "url": url, "date": d.group(0) if d else ""})
        if len(out) >= 30:
            break
    return out


def _fingerprint(item: dict[str, str]) -> str:
    return hashlib.sha256(f"{item.get('url','')}|{item.get('title','')}".encode("utf-8")).hexdigest()[:16]


def _load_seen() -> set[str]:
    if not FINGERPRINT_FILE.exists():
        return set()
    try:
        return set(json.loads(FINGERPRINT_FILE.read_text(encoding="utf-8")).get("seen", []))
    except (json.JSONDecodeError, OSError):
        return set()


def _save_seen(seen: set[str]) -> None:
    FINGERPRINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    keep = list(seen)[-5000:]
    FINGERPRINT_FILE.write_text(
        json.dumps({"seen": keep, "updated_at": dt.datetime.utcnow().isoformat() + "Z"},
                   ensure_ascii=False, indent=2), encoding="utf-8")


async def _summarize_with_llm(new_items: list[dict[str, str]]) -> str:
    if not new_items:
        return "本次扫描无新增法规。"

    profile_path = REPO_ROOT / "plugins" / "legal-advisor" / "CLAUDE.md"
    profile_text = profile_path.read_text(encoding="utf-8")[:2000] if profile_path.exists() else ""

    try:
        from src.agents.legal_researcher import LegalResearchAgent
        agent = LegalResearchAgent()
        bullets = "\n".join(f"- {i['date']} {i['title']} ({i['url']})" for i in new_items[:50])
        prompt = (
            f"以下是今日扫描到的中国新法规 / 公告条目（{len(new_items)} 条）：\n\n{bullets}\n\n"
            "请按法律顾问执业画像生成中文合规变更摘要：\n"
            "1. 按重要性排序，标注影响领域（合规 / 财税 / 跨境 / 劳动 / 知识产权）\n"
            "2. 对每条新法规标注：生效日 / 适用主体 / 客户应采取的初步动作\n"
            "3. 全文不超过 800 字\n"
            "4. 不下结论；最终签发由值班律师 confirm\n\n"
            f"执业画像参考：\n{profile_text}\n"
        )
        resp = await agent.process({"task": "regulation_summary", "prompt": prompt})
        return resp.content
    except Exception as e:  # noqa: BLE001
        logger.warning("regulation_monitor: LLM 摘要失败，降级 → {}", e)
        lines = ["# 法规变更摘要（LLM 不可用 — 降级输出）", ""]
        for i in new_items[:30]:
            lines.append(f"- {i['date']} **{i['title']}** — {i['url']}")
        return "\n".join(lines)


@celery_app.task(
    name="managed_agents.regulation_monitor.run", acks_late=True, max_retries=2,
)
def run(cookbook_name: str = "regulation-monitor") -> dict[str, Any]:
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

    # 1. 抓取
    all_items: list[dict[str, str]] = []
    for src in SOURCES:
        if egress and not any(fnmatch.fnmatchcase(src["host"], h) for h in egress):
            logger.warning("regulation_monitor: source {} 未在 egress_allowlist", src["host"])
            continue
        try:
            html = await _fetch(src["url"])
        except (httpx.HTTPError, OSError) as e:
            logger.warning("regulation_monitor: 抓取 {} 失败 → {}", src["url"], e)
            continue
        items = _extract_items(html, src["url"])
        for it in items:
            it["source"] = src["name"]
        all_items.extend(items)

    # 2. diff
    seen = _load_seen()
    new_items: list[dict[str, str]] = []
    for it in all_items:
        fp = _fingerprint(it)
        if fp in seen:
            continue
        seen.add(fp)
        it["_fp"] = fp
        new_items.append(it)
    _save_seen(seen)
    logger.info("regulation_monitor: 新增 {} / 总抓取 {} 条", len(new_items), len(all_items))

    # 3. LLM
    summary = await _summarize_with_llm(new_items)

    # 4. stage
    STAGE_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    draft_path = STAGE_DIR / f"draft-{stamp}.json"
    draft_payload = {
        "cookbook": cookbook_name,
        "persona": cookbook.get("ownerPersona", "legal-advisor"),
        "ts": dt.datetime.utcnow().isoformat() + "Z",
        "new_count": len(new_items),
        "total_scanned": len(all_items),
        "new_items": new_items[:200],
        "summary": summary,
        "status": "draft-pending-human-review",
        "human_gate": cookbook.get("humanGate", ""),
    }
    draft_path.write_text(json.dumps(draft_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    # 5. 审计 + 落 confirm ticket（PEP-4）
    write_event({
        "event_type": "cookbook.completed",
        "actor": {"type": "cookbook", "id": cookbook_name},
        "action": f"cookbook.{cookbook_name}.run",
        "resource": {"type": "cookbook", "id": cookbook_name,
                     "classification": "L2", "jurisdiction": "CN"},
        "decision": "ALLOW", "outcome": "draft-staged",
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "stats": {"new": len(new_items), "total": len(all_items)},
    })

    ticket_id: str | None = None
    if new_items:
        try:
            from src.core.database import async_session_maker
            from src.services.governance import confirm_inbox

            async with async_session_maker() as session:
                t = await confirm_inbox.create_ticket(
                    session,
                    requester={"id": f"cookbook:{cookbook_name}", "role": "system",
                               "tenant_id": "system"},
                    action="connector.feishu.send",
                    resource={"type": "connector", "id": "feishu/regulation-card",
                              "classification": "L2", "jurisdiction": "CN"},
                    pending_action={
                        "kind": "regulation_summary_push",
                        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
                        "new_count": len(new_items),
                    },
                    cookbook_name=cookbook_name,
                    persona=cookbook.get("ownerPersona", "legal-advisor"),
                    draft_path=str(draft_path.relative_to(REPO_ROOT)),
                    ttl_hours=24,
                )
                await session.commit()
                ticket_id = t.id
        except Exception as e:  # noqa: BLE001
            logger.warning("regulation_monitor: confirm ticket 创建失败 → {}", e)

    return {
        "cookbook": cookbook_name,
        "new_items": len(new_items),
        "total_scanned": len(all_items),
        "draft_path": str(draft_path.relative_to(REPO_ROOT)),
        "confirm_ticket_id": ticket_id,
    }
