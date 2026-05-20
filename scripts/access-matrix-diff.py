#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安心智能助手 · Access Matrix 变更 diff

PR review 时用：把当前分支的 policy/access-matrix.yaml 与 base 分支对比，
列出每个 role 的 scope 新增 / 移除 / 决策变更（ALLOW → DENY 之类）。

用法：
  python3 scripts/access-matrix-diff.py                  # 与 main 比较
  python3 scripts/access-matrix-diff.py --base origin/main
  python3 scripts/access-matrix-diff.py --base HEAD~5 --json

输出：
  role: legal_member
    + scope=skill.new-thing decision=ALLOW
    - scope=connector.linkedin.send decision=REQUIRE_CONFIRM
    ~ scope=data.contract.write decision=ALLOW → REQUIRE_CONFIRM
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
TARGET = "policy/access-matrix.yaml"


def _load_current() -> dict:
    return yaml.safe_load((ROOT / TARGET).read_text(encoding="utf-8"))


def _load_at_ref(ref: str) -> dict:
    try:
        text = subprocess.check_output(
            ["git", "show", f"{ref}:{TARGET}"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        print(f"无法在 {ref} 读取 {TARGET}", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(text)


def _index(role_cfg: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for kind in ("grants", "denies"):
        for entry in role_cfg.get(kind) or []:
            scope = entry.get("scope")
            if not scope:
                continue
            decision = entry.get("decision") or "DENY"
            out[scope] = {"kind": kind, "decision": decision,
                          "conditions": entry.get("conditions"),
                          "when": entry.get("when")}
    return out


def diff_role(old: dict | None, new: dict | None) -> list[dict]:
    old_idx = _index(old or {})
    new_idx = _index(new or {})
    out: list[dict] = []
    for s in sorted(set(old_idx) | set(new_idx)):
        a, b = old_idx.get(s), new_idx.get(s)
        if a and not b:
            out.append({"change": "removed", "scope": s, "from": a})
        elif b and not a:
            out.append({"change": "added", "scope": s, "to": b})
        elif a != b:
            out.append({"change": "modified", "scope": s, "from": a, "to": b})
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="main")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cur = _load_current()
    base = _load_at_ref(args.base)

    cur_roles = cur.get("roles", {}) or {}
    base_roles = base.get("roles", {}) or {}
    all_roles = sorted(set(cur_roles) | set(base_roles))

    report: dict[str, list[dict]] = {}
    for role in all_roles:
        d = diff_role(base_roles.get(role), cur_roles.get(role))
        if d:
            report[role] = d

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if not report:
        print("✅ access-matrix 无变更")
        return 0
    for role, changes in report.items():
        print(f"\nrole: {role}")
        for c in changes:
            scope = c["scope"]
            if c["change"] == "added":
                print(f"  + scope={scope}  decision={c['to']['decision']}")
            elif c["change"] == "removed":
                print(f"  - scope={scope}  decision={c['from']['decision']}")
            else:
                f, t = c["from"], c["to"]
                print(f"  ~ scope={scope}  decision={f['decision']} → {t['decision']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
