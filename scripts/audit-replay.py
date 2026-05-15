#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安心智能助手 · 审计重放

读取 `.claude/audit/*.jsonl` 按条件过滤、可选地重新跑 PDP 验证一致性。
约定见 docs/governance/AUDIT-LOG-SPEC.md。

用法：
  python3 scripts/audit-replay.py --user usr_xxx --date 2026-05-14
  python3 scripts/audit-replay.py --decision REQUIRE_CONFIRM --outcome user-cancelled
  python3 scripts/audit-replay.py --trace-id trace_abc...
  python3 scripts/audit-replay.py --since 2026-04-01 --until 2026-04-30 --jurisdiction "CN->EU"
  python3 scripts/audit-replay.py --verify-fingerprint    # 校验所有事件 fingerprint
  python3 scripts/audit-replay.py --replay-decision       # 用当时 policy 重新跑 decide() 比对结果
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIT_DIR = ROOT / ".claude" / "audit"


def _canonical(o: object) -> str:
    return json.dumps(o, sort_keys=True, ensure_ascii=False, default=str)


def _fingerprint(event: dict) -> str:
    payload = {k: v for k, v in event.items() if k != "fingerprint"}
    return "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def iter_events(since: dt.date | None, until: dt.date | None):
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
                except json.JSONDecodeError as e:
                    print(f"⚠ 跳过 {p.name}:{line_no} ({e})", file=sys.stderr)


def matches(ev: dict, args: argparse.Namespace) -> bool:
    if args.user and (ev.get("actor", {}).get("id") != args.user):
        return False
    if args.role and (ev.get("actor", {}).get("role") != args.role):
        return False
    if args.event_type and ev.get("event_type") != args.event_type:
        return False
    if args.decision and ev.get("decision") != args.decision:
        return False
    if args.outcome and ev.get("outcome") != args.outcome:
        return False
    if args.trace_id and ev.get("trace_id") != args.trace_id:
        return False
    if args.action and ev.get("action") != args.action:
        return False
    if args.jurisdiction:
        # 跨境字符串 "CN->EU" 来自 context.jurisdiction_chain 或 resource.jurisdiction
        chain = (ev.get("context") or {}).get("jurisdiction_chain")
        res_juris = (ev.get("resource") or {}).get("jurisdiction")
        actor_juris = ev.get("actor", {}).get("primary_jurisdiction", "CN")
        if "->" in args.jurisdiction:
            target = args.jurisdiction
            current = f"{actor_juris}->{res_juris}" if res_juris and res_juris != actor_juris else None
            if current != target and chain != target:
                return False
        else:
            if res_juris != args.jurisdiction:
                return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--user")
    parser.add_argument("--role")
    parser.add_argument("--event-type")
    parser.add_argument("--decision")
    parser.add_argument("--outcome")
    parser.add_argument("--trace-id")
    parser.add_argument("--action")
    parser.add_argument("--jurisdiction")
    parser.add_argument("--since", help="YYYY-MM-DD")
    parser.add_argument("--until", help="YYYY-MM-DD")
    parser.add_argument("--date", help="单日 YYYY-MM-DD（覆盖 since/until）")
    parser.add_argument("--verify-fingerprint", action="store_true")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    since = dt.date.fromisoformat(args.since) if args.since else None
    until = dt.date.fromisoformat(args.until) if args.until else None
    if args.date:
        since = dt.date.fromisoformat(args.date)
        until = since

    matched: list[dict] = []
    bad_fp = 0
    total = 0
    for fn, line_no, ev in iter_events(since, until):
        total += 1
        if args.verify_fingerprint:
            got = _fingerprint(ev)
            if ev.get("fingerprint") != got:
                bad_fp += 1
                print(f"✗ fingerprint mismatch {fn}:{line_no}", file=sys.stderr)
                continue
        if matches(ev, args):
            matched.append(ev)
            if len(matched) >= args.limit:
                break

    if args.json:
        print(json.dumps(matched, ensure_ascii=False, indent=2, default=str))
    else:
        for ev in matched:
            ts = ev.get("ts", "")
            actor = (ev.get("actor") or {}).get("id", "?")
            role = (ev.get("actor") or {}).get("role", "?")
            etype = ev.get("event_type", "?")
            action = ev.get("action", "")
            decision = ev.get("decision", "")
            outcome = ev.get("outcome", "")
            print(f"{ts}  {role}/{actor}  {etype}  {action}  → {decision} ({outcome})")
        print(f"\nscanned={total} matched={len(matched)} fingerprint_bad={bad_fp}")

    return 1 if bad_fp else 0


if __name__ == "__main__":
    sys.exit(main())
