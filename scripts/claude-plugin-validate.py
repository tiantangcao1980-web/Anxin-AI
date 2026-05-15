#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安心智能助手 · Claude 插件校验脚本

校验：
  1. .claude-plugin/marketplace.json 字段完整
  2. 每个 plugin 目录有 plugin.json + README.md + CLAUDE.md
  3. 每个 plugin 至少有 cold-start-interview skill
  4. 每个 SKILL.md frontmatter 有 name / description / user-invocable
  5. 每个 managed-agent-cookbook 有 agent.yaml + README.md
  6. agent.yaml 必含 guardrails / humanGate / dataSources

参考：Anthropic 的 `claude-for-legal/scripts/validate.py` 与
      `claude-for-financial-services/scripts/check.py`。

用法：
  python3 scripts/claude-plugin-validate.py             # 校验全仓
  python3 scripts/claude-plugin-validate.py plugins/legal-advisor
  python3 scripts/claude-plugin-validate.py managed-agent-cookbooks/regulation-monitor
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml  # PyYAML
except ImportError:
    print("[FATAL] 缺少 PyYAML：pip install pyyaml", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(msg: str) -> None:
    ERRORS.append(msg)


def warn(msg: str) -> None:
    WARNINGS.append(msg)


FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def parse_frontmatter(text: str) -> dict | None:
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    try:
        return yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        err(f"frontmatter YAML parse error: {e}")
        return None


def validate_marketplace() -> None:
    f = ROOT / ".claude-plugin" / "marketplace.json"
    if not f.exists():
        err(".claude-plugin/marketplace.json 不存在")
        return
    data = json.loads(f.read_text(encoding="utf-8"))
    for required in ("name", "displayName", "version", "plugins"):
        if required not in data:
            err(f"marketplace.json 缺少字段：{required}")
    for p in data.get("plugins", []):
        path = ROOT / p["path"]
        if not path.exists():
            err(f"marketplace 注册的插件路径不存在：{p['path']}")
    for c in data.get("managedAgentCookbooks", []):
        path = ROOT / c["path"]
        if not path.exists():
            err(f"marketplace 注册的 cookbook 路径不存在：{c['path']}")


def validate_plugin(pdir: Path) -> None:
    name = pdir.name
    pj = pdir / ".claude-plugin" / "plugin.json"
    if not pj.exists():
        err(f"[{name}] 缺少 .claude-plugin/plugin.json")
        return
    try:
        meta = json.loads(pj.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        err(f"[{name}] plugin.json 不是合法 JSON：{e}")
        return
    for field in ("name", "displayName", "version", "skills"):
        if field not in meta:
            err(f"[{name}] plugin.json 缺少字段：{field}")
    for must in ("README.md", "CLAUDE.md"):
        if not (pdir / must).exists():
            err(f"[{name}] 缺少 {must}")
    cold = pdir / "skills" / "cold-start-interview" / "SKILL.md"
    if meta.get("requiresColdStart", True) and not cold.exists():
        err(f"[{name}] 缺少冷启动访谈 skill：skills/cold-start-interview/SKILL.md（如不需要可在 plugin.json 设 requiresColdStart: false）")
    for skill_md in pdir.glob("skills/*/SKILL.md"):
        validate_skill_md(skill_md, plugin=name)


def validate_skill_md(skill_md: Path, plugin: str | None = None) -> None:
    rel = skill_md.relative_to(ROOT)
    text = skill_md.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    if fm is None:
        err(f"{rel} 缺少 YAML frontmatter")
        return
    for field in ("name", "description"):
        if field not in fm:
            err(f"{rel} frontmatter 缺少：{field}")
    if "user-invocable" not in fm:
        warn(f"{rel} frontmatter 缺少 user-invocable（推荐显式声明）")
    if len(text) < 200:
        warn(f"{rel} 内容过短（< 200 字），可能未完成")


def validate_cookbook(cdir: Path) -> None:
    name = cdir.name
    ay = cdir / "agent.yaml"
    if not ay.exists():
        err(f"[cookbook:{name}] 缺少 agent.yaml")
        return
    try:
        data = yaml.safe_load(ay.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        err(f"[cookbook:{name}] agent.yaml YAML 错误：{e}")
        return
    for field in ("name", "trigger", "tools", "guardrails", "humanGate"):
        if field not in data:
            err(f"[cookbook:{name}] agent.yaml 缺少字段：{field}")
    if not (cdir / "README.md").exists():
        err(f"[cookbook:{name}] 缺少 README.md")
    guardrails = data.get("guardrails", [])
    if isinstance(guardrails, list) and len(guardrails) < 2:
        warn(f"[cookbook:{name}] guardrails 少于 2 条，建议至少声明 draft-only + source-attribution")


def discover_targets(args: list[str]) -> Iterable[Path]:
    if not args:
        validate_marketplace()
        for pd in sorted((ROOT / "plugins").glob("*/")):
            yield ("plugin", pd)
        for cd in sorted((ROOT / "managed-agent-cookbooks").glob("*/")):
            yield ("cookbook", cd)
        return
    for a in args:
        p = (ROOT / a).resolve() if not os.path.isabs(a) else Path(a).resolve()
        if not p.exists():
            err(f"路径不存在：{a}")
            continue
        if "managed-agent-cookbooks" in p.parts:
            yield ("cookbook", p)
        elif "plugins" in p.parts:
            yield ("plugin", p)
        else:
            err(f"无法判断 target 类型：{a}")


def main() -> int:
    args = sys.argv[1:]
    for kind, p in discover_targets(args):
        if kind == "plugin":
            validate_plugin(p)
        else:
            validate_cookbook(p)

    if WARNINGS:
        print("\n=== 警告 ===")
        for w in WARNINGS:
            print(f"  ⚠ {w}")
    if ERRORS:
        print("\n=== 错误 ===")
        for e in ERRORS:
            print(f"  ✗ {e}")
        print(f"\n校验失败：{len(ERRORS)} errors / {len(WARNINGS)} warnings")
        return 1
    print(f"\n✅ 校验通过（{len(WARNINGS)} warnings）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
