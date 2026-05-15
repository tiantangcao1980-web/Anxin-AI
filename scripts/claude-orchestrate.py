#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安心智能助手 · Managed Agent 参考事件循环

把 `managed-agent-cookbooks/<name>/agent.yaml` 当成 Anthropic Managed Agents API
风格的事件循环本地执行。仅作为参考实现 — 生产环境推荐部署到 Anthropic API 或
backend/src/tasks/managed_agents/ 下的 Celery worker。

设计与参考：
  - Anthropic claude-for-legal/scripts/orchestrate.py
  - Anthropic claude-for-financial-services/scripts/orchestrate.py

用法：
  python3 scripts/claude-orchestrate.py regulation-monitor
  python3 scripts/claude-orchestrate.py contract-renewal-watcher --dry-run

环境变量：
  ANTHROPIC_API_KEY    必填
  ANXIN_FEISHU_TOKEN   推送渠道，可选
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("缺少 PyYAML：pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
COOKBOOK_DIR = ROOT / "managed-agent-cookbooks"


def load_cookbook(name: str) -> dict:
    path = COOKBOOK_DIR / name / "agent.yaml"
    if not path.exists():
        sys.exit(f"找不到 cookbook：{path}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def log(stage: str, payload: dict) -> None:
    line = {"ts": dt.datetime.utcnow().isoformat() + "Z", "stage": stage, **payload}
    print(json.dumps(line, ensure_ascii=False))


def call_claude(prompt: str, model: str, tools: list[str], dry_run: bool) -> dict:
    """占位：实际生产中应替换为 anthropic.Anthropic().messages.create(...)。"""
    if dry_run:
        return {"role": "assistant", "content": f"[dry-run] {prompt[:120]}…"}
    try:
        import anthropic  # type: ignore
    except ImportError:
        sys.exit("生产模式需要 anthropic SDK：pip install anthropic")
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.model_dump()


def event_loop(cookbook: dict, *, dry_run: bool, max_iters: int = 5) -> int:
    model = cookbook.get("model", "claude-opus-4-7")
    tools = cookbook.get("tools", [])
    sources = cookbook.get("dataSources", [])
    guardrails = cookbook.get("guardrails", [])
    human_gate = cookbook.get("humanGate", "")

    log("start", {"agent": cookbook["name"], "dry_run": dry_run, "model": model})

    # Step 1 — Fetch & summarize sources
    fetch_prompt = (
        f"你是 Anxin AI 的 managed agent `{cookbook['name']}`。\n"
        f"任务：{cookbook['description']}\n"
        f"数据源：{json.dumps(sources, ensure_ascii=False)}\n"
        f"约束：{json.dumps(guardrails, ensure_ascii=False)}\n"
        f"产出：一份结构化的草稿（draft），不要直接外发。"
    )
    summary = call_claude(fetch_prompt, model, tools, dry_run)
    log("fetched", {"chars": len(json.dumps(summary, ensure_ascii=False))})

    # Step 2 — Human gate check
    log("human_gate", {"rule": human_gate, "must_confirm": True})

    # Step 3 — Output staging (不直接外发)
    out_dir = ROOT / ".claude" / "managed-agent-runs" / cookbook["name"]
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    (out_dir / f"draft-{stamp}.json").write_text(
        json.dumps({"cookbook": cookbook["name"], "draft": summary, "ts": stamp},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log("staged", {"path": f".claude/managed-agent-runs/{cookbook['name']}/draft-{stamp}.json"})

    log("done", {"agent": cookbook["name"], "human_action_required": True})
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("cookbook", help="cookbook 名（managed-agent-cookbooks 下的目录名）")
    parser.add_argument("--dry-run", action="store_true", help="不真正调用 Claude API")
    parser.add_argument("--max-iters", type=int, default=5)
    args = parser.parse_args()

    if not args.dry_run and not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("非 dry-run 模式必须设置 ANTHROPIC_API_KEY")

    cb = load_cookbook(args.cookbook)
    return event_loop(cb, dry_run=args.dry_run, max_iters=args.max_iters)


if __name__ == "__main__":
    sys.exit(main())
