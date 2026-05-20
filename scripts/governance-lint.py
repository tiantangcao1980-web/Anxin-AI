#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安心智能助手 · 治理校验

校验：
  1. policy/*.yaml 加载通过（schema_version + 关键 section + 引用一致性）
  2. 所有 plugins/*/skills/*/SKILL.md frontmatter 含治理必填字段
  3. 所有 managed-agent-cookbooks/*/agent.yaml 含 governance section
  4. SKILL.md required-scopes ⊆ access-matrix 已声明的 scope 模式
  5. SKILL.md tool-allowlist ⊆ tool-allowlist.yaml § tool_categories
  6. 所有 SKILL.md 的 jurisdiction 必须在 jurisdiction-rules.yaml § jurisdictions 中
  7. lifecycle-stage 必须是 5 状态之一

用法：
  python3 scripts/governance-lint.py
  python3 scripts/governance-lint.py --json   # 给 CI / 前端
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

ERRORS: list[dict] = []
WARNINGS: list[dict] = []


def err(target: str, code: str, msg: str) -> None:
    ERRORS.append({"target": target, "code": code, "msg": msg})


def warn(target: str, code: str, msg: str) -> None:
    WARNINGS.append({"target": target, "code": code, "msg": msg})


FRONT = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict | None:
    m = FRONT.match(text)
    if not m:
        return None
    return yaml.safe_load(m.group(1)) or {}


def load_policies() -> dict:
    pdir = ROOT / "policy"
    files = [
        "access-matrix.yaml", "trust-levels.yaml", "data-classification.yaml",
        "jurisdiction-rules.yaml", "tool-allowlist.yaml", "pii-redaction.yaml",
        "skill-lifecycle.yaml",
    ]
    out: dict[str, dict] = {}
    for fn in files:
        p = pdir / fn
        if not p.exists():
            err(f"policy/{fn}", "POLICY_MISSING", f"缺失 policy/{fn}")
            continue
        try:
            out[fn] = yaml.safe_load(p.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            err(f"policy/{fn}", "POLICY_YAML_ERROR", str(e))
    return out


def check_policy_schema(policies: dict) -> None:
    schema_keys = {
        "access-matrix.yaml": ["schema_version", "default_decision", "roles"],
        "trust-levels.yaml": ["schema_version", "levels", "registries"],
        "data-classification.yaml": ["schema_version", "levels", "clearance_by_role"],
        "jurisdiction-rules.yaml": ["schema_version", "jurisdictions", "cross_border"],
        "tool-allowlist.yaml": ["schema_version", "tool_categories", "persona_defaults"],
        "pii-redaction.yaml": ["schema_version", "types", "policies"],
        "skill-lifecycle.yaml": ["schema_version", "states", "transitions", "thresholds"],
    }
    for fn, keys in schema_keys.items():
        data = policies.get(fn) or {}
        for k in keys:
            if k not in data:
                err(f"policy/{fn}", "POLICY_SCHEMA", f"缺字段：{k}")


def all_scope_patterns(matrix: dict) -> set[str]:
    out = set()
    for role_cfg in matrix.get("roles", {}).values():
        for g in (role_cfg.get("grants") or []) + (role_cfg.get("denies") or []):
            s = g.get("scope")
            if s:
                out.add(s)
    return out


def lint_skill(skill_md: Path, policies: dict) -> None:
    rel = skill_md.relative_to(ROOT).as_posix()
    fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    if fm is None:
        err(rel, "FRONTMATTER_MISSING", "缺少 frontmatter")
        return

    required = [
        "name", "description", "version", "user-invocable",
        "access-level", "data-classification", "jurisdiction",
        "required-scopes", "tool-allowlist", "lifecycle-stage", "audit-level",
    ]
    for k in required:
        if k not in fm:
            err(rel, "FRONTMATTER_MISSING_FIELD", f"缺字段：{k}")

    # data-classification ∈ L1..L5
    if "data-classification" in fm and fm["data-classification"] not in ("L1","L2","L3","L4","L5"):
        err(rel, "INVALID_CLASSIFICATION", f"无效 data-classification: {fm['data-classification']}")

    # jurisdiction ∈ policy.jurisdictions
    if "jurisdiction" in fm:
        valid = set((policies.get("jurisdiction-rules.yaml") or {}).get("jurisdictions", {}).keys()) | {"global"}
        if fm["jurisdiction"] not in valid:
            err(rel, "INVALID_JURISDICTION", f"未知 jurisdiction: {fm['jurisdiction']}")

    # lifecycle-stage ∈ 5 状态
    valid_stages = set((policies.get("skill-lifecycle.yaml") or {}).get("states", []))
    if "lifecycle-stage" in fm and fm["lifecycle-stage"] not in valid_stages:
        err(rel, "INVALID_LIFECYCLE", f"无效 lifecycle-stage: {fm['lifecycle-stage']}")

    # required-scopes 是否在 access-matrix patterns 中能匹配
    patterns = all_scope_patterns(policies.get("access-matrix.yaml") or {})
    for sc in fm.get("required-scopes") or []:
        import fnmatch
        matched = any(fnmatch.fnmatchcase(sc, p) for p in patterns)
        if not matched:
            warn(rel, "SCOPE_NOT_IN_ACCESS_MATRIX",
                 f"scope '{sc}' 未被 access-matrix 任何 pattern 匹配；调用必然 DENY")

    # tool-allowlist ⊆ tool_categories
    tool_cats = set((policies.get("tool-allowlist.yaml") or {}).get("tool_categories", {}).keys())
    for t in fm.get("tool-allowlist") or []:
        if t not in tool_cats:
            err(rel, "INVALID_TOOL_CATEGORY", f"tool '{t}' 不在 policy/tool-allowlist.yaml § tool_categories")


def lint_cookbook(cb_dir: Path, policies: dict) -> None:
    rel = cb_dir.relative_to(ROOT).as_posix()
    ay = cb_dir / "agent.yaml"
    if not ay.exists():
        err(rel, "AGENT_YAML_MISSING", "缺 agent.yaml")
        return
    try:
        data = yaml.safe_load(ay.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        err(rel, "AGENT_YAML_INVALID", str(e))
        return

    if "governance" not in data:
        err(rel, "COOKBOOK_MISSING_GOVERNANCE", "agent.yaml 缺 governance section")
        return
    gov = data["governance"]
    for k in ("authz", "dataClassification", "jurisdiction", "pii", "audit"):
        if k not in gov:
            err(rel, "COOKBOOK_GOVERNANCE_FIELD", f"governance.{k} 缺失")

    # dataClassification 合法
    if gov.get("dataClassification") not in ("L1","L2","L3","L4","L5"):
        err(rel, "INVALID_CLASSIFICATION",
            f"无效 dataClassification: {gov.get('dataClassification')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="JSON 输出（CI 友好）")
    args = parser.parse_args()

    policies = load_policies()
    check_policy_schema(policies)

    for skill_md in sorted((ROOT / "plugins").glob("*/skills/*/SKILL.md")):
        lint_skill(skill_md, policies)

    for cb in sorted((ROOT / "managed-agent-cookbooks").glob("*/")):
        if not cb.is_dir():
            continue
        lint_cookbook(cb, policies)

    if args.json:
        print(json.dumps({"errors": ERRORS, "warnings": WARNINGS}, ensure_ascii=False, indent=2))
    else:
        if WARNINGS:
            print("\n=== 警告 ===")
            for w in WARNINGS:
                print(f"  ⚠ [{w['code']}] {w['target']}: {w['msg']}")
        if ERRORS:
            print("\n=== 错误 ===")
            for e in ERRORS:
                print(f"  ✗ [{e['code']}] {e['target']}: {e['msg']}")
            print(f"\n治理校验失败：{len(ERRORS)} errors / {len(WARNINGS)} warnings")
            return 1
        print(f"\n✅ 治理校验通过（{len(WARNINGS)} warnings）")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
