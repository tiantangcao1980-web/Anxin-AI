# -*- coding: utf-8 -*-
"""
Trace → 回归用例转换器（T2）

输入：T1 落盘的 trace summary（dict，已 PII scrub + cluster_id）
输出：
  1. eval case（写入 backend/evals/agents/<agent>/auto/*.jsonl）—— 待人工 review 后入主集
  2. pytest case（写入 backend/tests/auto/test_<cluster_id>.py）—— 复现失败模式

护栏：
  - 自动产物只能进 auto/ 子目录，不直接污染主测试集
  - 每条记录附 origin trace_id + cluster_id + author=auto-converter
  - 涉 PII 字段必须已是 [MASK_*] 形式才能入用例（重新 scrub 一遍兜底）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
EVALS_AUTO_ROOT = REPO_ROOT / "backend" / "evals" / "agents"
TESTS_AUTO_ROOT = REPO_ROOT / "backend" / "tests" / "auto"

# 简化路由 → agent_id 映射（与 AGENTS.md §3.2 保持一致）
ROUTE_TO_AGENT = {
    "chat": "legal-advisor",
    "general": "legal-advisor",
    "contract": "contract-reviewer",
    "due_diligence": "due-diligence",
    "research": "legal-researcher",
    "risk": "risk-assessor",
}


@dataclass
class ConvertResult:
    case_path: Optional[Path]
    pytest_path: Optional[Path]
    skipped_reason: Optional[str]


# ---- PII 兜底（即使 T1 已 scrub，也再扫一遍）----

_PII_PATTERNS = [
    (re.compile(r"\b\d{17}[\dXx]\b"), "[MASK_ID]"),
    (re.compile(r"\b1[3-9]\d{9}\b"), "[MASK_PHONE]"),
    (re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[MASK_EMAIL]"),
    (re.compile(r"\b(?:\d[ -]?){12,18}\d\b"), "[MASK_CARD]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[MASK_KEY]"),
]


def _double_scrub(text: str) -> str:
    out = text
    for pat, rep in _PII_PATTERNS:
        out = pat.sub(rep, out)
    return out


def _has_unmasked_pii(text: str) -> bool:
    return any(pat.search(text) for pat, _ in _PII_PATTERNS)


# ---- 路由 → Agent ----

def _detect_agent(trace: dict) -> Optional[str]:
    route = (trace.get("route") or "").lower()
    if route in ROUTE_TO_AGENT:
        return ROUTE_TO_AGENT[route]
    # fallback：从 spans 里找 agent_name
    for span in trace.get("agent_spans", []) or []:
        agent = (span.get("agent") or "").lower().replace("_", "-")
        if agent in {a for a in ROUTE_TO_AGENT.values()}:
            return agent
    return None


# ---- Trace → Case ----

def trace_to_case(trace: dict) -> dict:
    """从 trace 提取 case 框架（input + 期望失败模式）"""
    cluster_id = None
    error_signature = None
    for span in trace.get("agent_spans", []) or []:
        if span.get("status") == "error":
            cluster_id = span.get("cluster_id")
            error_signature = span.get("operation") or span.get("error_msg")
            break

    case_id = (
        cluster_id
        or hashlib.sha1(json.dumps(trace, sort_keys=True).encode()).hexdigest()[:12]
    )
    return {
        "id": f"auto-{case_id}",
        "input": trace.get("user_query") or trace.get("input") or "（trace 未保留 input）",
        "expected": {
            "summary": "复现失败模式 - 必须不再触发同一 cluster",
            "schema": {"required": []},  # 默认不强校验结构
            "must_not_appear": [],
        },
        "origin": {
            "trace_id": trace.get("trace_id"),
            "cluster_id": cluster_id,
            "error_signature": error_signature,
            "elapsed_ms": trace.get("elapsed_ms"),
        },
        "author": "auto-converter",
        "reviewer": "pending",
    }


# ---- Trace → Pytest ----

PYTEST_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
T2 自动生成 - 回归用例
源 trace: {trace_id}
失败聚类: {cluster_id}
错误签名: {error_signature}

⚠️ 本文件由 backend/scripts/trace_to_test/converter.py 生成，不要手改。
人工 review 后可移到 backend/tests/test_*.py 主集。
"""

import pytest


@pytest.mark.auto_generated
@pytest.mark.regression
@pytest.mark.cluster("{cluster_id}")
def test_must_not_re_trigger_cluster_{cluster_safe}():
    """复现 trace 失败模式 - 验证修复不再触发同一 cluster_id"""
    # 占位：真接入需要：
    #   1. 加载 trace 输入（user input + 上下文）
    #   2. 调用 chat_service.chat(...)
    #   3. 断言响应里 _harness.cluster_id != "{cluster_id}"
    pytest.skip("待人工接入真实回放路径（trace 输入 → chat_service.chat → cluster_id 断言）")
'''


def trace_to_pytest(trace: dict, agent_id: str) -> Optional[str]:
    cluster_id = None
    error_signature = None
    for span in trace.get("agent_spans", []) or []:
        if span.get("status") == "error":
            cluster_id = span.get("cluster_id")
            error_signature = span.get("operation") or span.get("error_msg")
            break
    if not cluster_id:
        return None
    cluster_safe = re.sub(r"\W", "_", cluster_id)[:24]
    return PYTEST_TEMPLATE.format(
        trace_id=trace.get("trace_id", "unknown"),
        cluster_id=cluster_id,
        cluster_safe=cluster_safe,
        error_signature=(error_signature or "")[:80],
    )


# ---- 主转换 ----

def convert(trace: dict, *, dry_run: bool = False) -> ConvertResult:
    raw_text = json.dumps(trace, ensure_ascii=False)
    if _has_unmasked_pii(raw_text):
        # 兜底再洗一次；仍洗不掉就拒绝
        clean = _double_scrub(raw_text)
        if _has_unmasked_pii(clean):
            return ConvertResult(None, None, "trace 包含未脱敏 PII，拒绝转测")
        trace = json.loads(clean)

    agent = _detect_agent(trace)
    if not agent:
        return ConvertResult(None, None, f"无法识别 agent (route={trace.get('route')})")

    case = trace_to_case(trace)
    pytest_src = trace_to_pytest(trace, agent)

    if dry_run:
        return ConvertResult(None, None, "dry_run")

    case_path = EVALS_AUTO_ROOT / agent / "auto" / "cases.jsonl"
    case_path.parent.mkdir(parents=True, exist_ok=True)
    with case_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(case, ensure_ascii=False) + "\n")

    pytest_path = None
    if pytest_src:
        TESTS_AUTO_ROOT.mkdir(parents=True, exist_ok=True)
        cluster = case["origin"]["cluster_id"]
        pytest_path = TESTS_AUTO_ROOT / f"test_cluster_{cluster}.py"
        if not pytest_path.exists():  # 同 cluster 不重复生成
            pytest_path.write_text(pytest_src, encoding="utf-8")

    return ConvertResult(case_path, pytest_path, None)


# ---- CLI ----

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("trace_files", nargs="*", help="trace JSON 文件路径列表（每文件一个 trace summary）")
    parser.add_argument("--stdin", action="store_true", help="从 stdin 读 NDJSON")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    traces: list[dict] = []
    for p in args.trace_files:
        traces.append(json.loads(Path(p).read_text(encoding="utf-8")))
    if args.stdin:
        for line in sys.stdin:
            line = line.strip()
            if line:
                traces.append(json.loads(line))

    if not traces:
        parser.error("需要 trace 文件或 --stdin")

    converted = skipped = 0
    for trace in traces:
        r = convert(trace, dry_run=args.dry_run)
        if r.skipped_reason:
            skipped += 1
            print(f"⊘ skip: {r.skipped_reason} (trace={trace.get('trace_id')})")
        else:
            converted += 1
            print(f"✓ case→{r.case_path}  pytest→{r.pytest_path}")
    print(f"\n转换 {converted} / 跳过 {skipped}")


if __name__ == "__main__":
    main()
