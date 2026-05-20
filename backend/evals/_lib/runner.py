#!/usr/bin/env python3
"""
Agent Eval Runner（E1）

用法:
    python -m evals._lib.runner --agent legal-advisor
    python -m evals._lib.runner --all
    python -m evals._lib.runner --all --compare-baseline --threshold 0.05

设计:
- 默认不真的调用 LLM（CI 友好）。--with-agent 才真跑 agent。
- 默认 mode=structural-only：只跑 4 维打分中不依赖 LLM 的 3 维（structural/citation/safety），similarity 占位。
- compare-baseline：分数低于 baseline*(1-threshold) 退出码 1，PR Gate 阻塞。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

from evals._lib.scorer import score_case, CaseScore


EVALS_ROOT = Path(__file__).resolve().parent.parent
AGENTS_DIR = EVALS_ROOT / "agents"


def list_agents() -> list[str]:
    return sorted(p.name for p in AGENTS_DIR.iterdir() if p.is_dir())


def load_cases(agent_id: str) -> list[dict]:
    path = AGENTS_DIR / agent_id / "cases.jsonl"
    if not path.exists():
        return []
    cases = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            cases.append(json.loads(line))
    return cases


def load_baseline(agent_id: str) -> dict:
    path = AGENTS_DIR / agent_id / "baseline.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def stub_actual(case: dict) -> dict:
    """E1 阶段 stub：用 case.expected.stub_actual 模拟 agent 输出，便于 CI 跑通。
    真接入 agent → 替换为 await agent.chat(case['input'])
    """
    return case.get("stub_actual") or {}


def run_agent(agent_id: str) -> tuple[float, list[CaseScore]]:
    cases = load_cases(agent_id)
    if not cases:
        return 0.0, []
    scores = [score_case(c, stub_actual(c)) for c in cases]
    return median(s.total for s in scores), scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", help="指定 agent id")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--compare-baseline", action="store_true")
    parser.add_argument("--threshold", type=float, default=0.05)
    parser.add_argument("--save-baseline", action="store_true",
                        help="把当前结果写为新的 baseline.json")
    args = parser.parse_args()

    targets = list_agents() if args.all else ([args.agent] if args.agent else [])
    if not targets:
        parser.error("--agent 或 --all 至少给一个")

    overall_pass = True
    summary: dict[str, dict] = {}
    for agent_id in targets:
        med_score, scores = run_agent(agent_id)
        summary[agent_id] = {
            "median": round(med_score, 3),
            "case_count": len(scores),
            "case_scores": [s.to_dict() for s in scores],
        }
        baseline = load_baseline(agent_id)
        baseline_med = baseline.get("median", 0.0)

        marker = "✅"
        if args.compare_baseline and baseline_med:
            min_acceptable = baseline_med * (1 - args.threshold)
            if med_score < min_acceptable:
                marker = "❌"
                overall_pass = False
        elif args.compare_baseline:
            marker = "⚠️ no-baseline"

        print(f"{marker} {agent_id}: median={med_score:.3f} (baseline={baseline_med:.3f})")
        for s in scores:
            print(f"    - {s.case_id}: total={s.total:.3f} | "
                  f"structural={s.structural:.2f} citation={s.citation:.2f} "
                  f"safety={s.safety:.2f} similarity={s.similarity:.2f}")
            for note in s.notes:
                print(f"        · {note}")

        if args.save_baseline:
            (AGENTS_DIR / agent_id / "baseline.json").write_text(
                json.dumps({"median": round(med_score, 3), "case_count": len(scores)},
                           ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"    💾 已写入 baseline.json")

    if args.compare_baseline and not overall_pass:
        print("\n❌ 分数低于 baseline，阻塞 merge")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
