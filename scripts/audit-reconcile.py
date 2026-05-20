#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安心智能助手 · 审计 JSONL ↔ DB 对账

JSONL 是法证级真相源，DB 是性能查询层。两者应一致；如有 drift 必须告警。

检测：
  1. JSONL 中存在但 DB 没有的 event_id  → MISSING_IN_DB（DB 写丢失）
  2. DB 中存在但 JSONL 没有的 event_id  → MISSING_IN_JSONL（异常，不该出现）
  3. 同 event_id 双边 fingerprint 不一致 → FINGERPRINT_DRIFT（被篡改）
  4. JSONL 内任一行 fingerprint 自校失败 → FINGERPRINT_INVALID

输出：
  - stdout JSON 报告
  - 退出码：0 一致 / 1 有 drift / 2 错误
  - 涉及 incident 时发飞书 #ops-security（环境变量 ANXIN_OPS_FEISHU_WEBHOOK）

用法：
  python3 scripts/audit-reconcile.py                          # 最近 7 天
  python3 scripts/audit-reconcile.py --since 2026-05-01
  python3 scripts/audit-reconcile.py --since 2026-05-01 --until 2026-05-13 --json
  python3 scripts/audit-reconcile.py --backfill               # 把 JSONL 中缺的写回 DB
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / ".claude" / "audit"


def _canonical(o: object) -> str:
    return json.dumps(o, sort_keys=True, ensure_ascii=False, default=str)


def _fingerprint(event: dict) -> str:
    payload = {k: v for k, v in event.items() if k != "fingerprint"}
    return "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def iter_jsonl(since: dt.date | None, until: dt.date | None):
    if not AUDIT_DIR.exists():
        return
    for p in sorted(AUDIT_DIR.glob("*.jsonl")):
        try:
            day = dt.date.fromisoformat(p.stem)
        except ValueError:
            continue
        if since and day < since:
            continue
        if until and day > until:
            continue
        with p.open("r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield p.name, line_no, json.loads(line)
                except json.JSONDecodeError:
                    continue


async def collect_db(since: dt.datetime | None, until: dt.datetime | None) -> dict[str, dict]:
    """从 audit_events 表收集 {event_id: row}。"""
    try:
        sys.path.insert(0, str(ROOT / "backend"))
        from sqlalchemy import select  # noqa
        from src.core.database import async_session_maker  # noqa
        from src.models.governance import AuditEventDB  # noqa
    except ImportError as e:
        print(f"⚠ 无法 import backend 模块（需在仓库根运行）：{e}", file=sys.stderr)
        return {}

    db_rows: dict[str, dict] = {}
    try:
        async with async_session_maker() as session:
            stmt = select(AuditEventDB)
            if since:
                stmt = stmt.where(AuditEventDB.ts >= since)
            if until:
                stmt = stmt.where(AuditEventDB.ts <= until)
            res = await session.execute(stmt)
            for row in res.scalars():
                db_rows[row.event_id] = {
                    "event_id": row.event_id,
                    "fingerprint": row.fingerprint,
                    "ts": row.ts.isoformat() if row.ts else None,
                }
    except Exception as e:  # noqa: BLE001
        print(f"⚠ DB 查询失败（视作 DB 空）：{e}", file=sys.stderr)
    return db_rows


async def backfill_to_db(events: list[dict]) -> int:
    try:
        sys.path.insert(0, str(ROOT / "backend"))
        from src.services.governance.audit import _db_write_async  # type: ignore
    except ImportError as e:
        print(f"⚠ 无法 backfill：{e}", file=sys.stderr)
        return 0
    n = 0
    for ev in events:
        try:
            await _db_write_async(ev)
            n += 1
        except Exception:  # noqa: BLE001
            pass
    return n


def notify_feishu_webhook(text: str) -> None:
    url = os.environ.get("ANXIN_OPS_FEISHU_WEBHOOK")
    if not url:
        return
    try:
        import urllib.request

        body = json.dumps({"msg_type": "text", "content": {"text": text}}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).read()  # noqa: S310
    except Exception as e:  # noqa: BLE001
        print(f"⚠ 飞书告警失败：{e}", file=sys.stderr)


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", help="YYYY-MM-DD")
    parser.add_argument("--until", help="YYYY-MM-DD")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--backfill", action="store_true", help="把 JSONL 中缺的事件写回 DB")
    parser.add_argument("--fail-fast", action="store_true", help="任一篡改即退出 1，不再扫描")
    args = parser.parse_args()

    since_d = dt.date.fromisoformat(args.since) if args.since else (dt.date.today() - dt.timedelta(days=7))
    until_d = dt.date.fromisoformat(args.until) if args.until else dt.date.today()

    # 1. 扫 JSONL
    jsonl_events: dict[str, dict] = {}
    invalid_fp: list[dict] = []
    for fn, line_no, ev in iter_jsonl(since_d, until_d):
        eid = ev.get("event_id")
        if not eid:
            continue
        got = _fingerprint(ev)
        if ev.get("fingerprint") != got:
            invalid_fp.append({"file": fn, "line": line_no, "event_id": eid,
                               "expected": got, "got": ev.get("fingerprint")})
            if args.fail_fast:
                break
        jsonl_events[eid] = ev

    # 2. 扫 DB
    since_dt = dt.datetime.combine(since_d, dt.time.min, tzinfo=dt.timezone.utc)
    until_dt = dt.datetime.combine(until_d, dt.time.max, tzinfo=dt.timezone.utc)
    db_events = await collect_db(since_dt, until_dt)

    # 3. 差集
    j_ids = set(jsonl_events)
    d_ids = set(db_events)
    missing_in_db = j_ids - d_ids
    missing_in_jsonl = d_ids - j_ids
    drift_fp: list[str] = []
    for eid in j_ids & d_ids:
        if jsonl_events[eid].get("fingerprint") != db_events[eid].get("fingerprint"):
            drift_fp.append(eid)

    # 4. backfill
    backfilled = 0
    if args.backfill and missing_in_db:
        backfilled = await backfill_to_db([jsonl_events[eid] for eid in missing_in_db])

    report = {
        "since": since_d.isoformat(),
        "until": until_d.isoformat(),
        "jsonl_count": len(j_ids),
        "db_count": len(d_ids),
        "missing_in_db": len(missing_in_db),
        "missing_in_jsonl": len(missing_in_jsonl),
        "fingerprint_drift": len(drift_fp),
        "fingerprint_invalid": len(invalid_fp),
        "backfilled": backfilled,
        "samples": {
            "missing_in_db": list(missing_in_db)[:10],
            "missing_in_jsonl": list(missing_in_jsonl)[:10],
            "fingerprint_drift": drift_fp[:10],
            "fingerprint_invalid": invalid_fp[:10],
        },
    }

    has_incident = invalid_fp or drift_fp or missing_in_jsonl
    if has_incident:
        notify_feishu_webhook(
            f"[审计对账告警] {since_d}~{until_d}\n"
            f"fingerprint_invalid={len(invalid_fp)} "
            f"drift={len(drift_fp)} "
            f"missing_in_jsonl={len(missing_in_jsonl)}\n"
            f"详见 scripts/audit-reconcile.py 报告"
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for k, v in report.items():
            if k == "samples":
                continue
            print(f"  {k}: {v}")
        if has_incident:
            print("\n⚠ 检出 incident（fp_invalid / drift / missing_in_jsonl 任一>0）")

    if has_incident:
        return 1
    if missing_in_db and not args.backfill:
        # 单纯 DB 写丢失 — 给警告但不算 incident
        print("\n⚠ JSONL 中存在但 DB 未记录的事件（可加 --backfill 修复）")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
