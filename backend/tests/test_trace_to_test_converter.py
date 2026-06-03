# -*- coding: utf-8 -*-
"""
Trace → Test 转换器测试（T2）

覆盖：
- 正常 trace 能产出 case + pytest 文件
- 含 cluster_id 才生成 pytest，否则只生成 case
- 包含未脱敏 PII 的 trace 必须被拒绝
- 同 cluster_id 不重复生成 pytest
- 不识别的 route 返回 skipped_reason
"""

import json
import shutil

import pytest

from scripts.trace_to_test.converter import (
    EVALS_AUTO_ROOT,
    TESTS_AUTO_ROOT,
    convert,
    trace_to_case,
)

SAMPLE_TRACE_FAILED = {
    "trace_id": "abc123def456",
    "user_id": "u-1",
    "conversation_id": "c-1",
    "route": "chat",
    "elapsed_ms": 1234,
    "agent_spans": [
        {
            "operation": "agent.legal_advisor.chat",
            "agent": "legal_advisor",
            "status": "error",
            "error_type": "RateLimit",
            "error_msg": "rate limit",
            "cluster_id": "deadbeef00000001",
        }
    ],
}


@pytest.fixture(autouse=True)
def cleanup_auto_dirs():
    yield
    auto_evals = EVALS_AUTO_ROOT / "legal-advisor" / "auto"
    if auto_evals.exists():
        shutil.rmtree(auto_evals)
    for p in TESTS_AUTO_ROOT.glob("test_cluster_*.py"):
        p.unlink()


def test_trace_to_case_includes_origin():
    case = trace_to_case(SAMPLE_TRACE_FAILED)
    assert case["id"].startswith("auto-")
    assert case["origin"]["trace_id"] == "abc123def456"
    assert case["origin"]["cluster_id"] == "deadbeef00000001"
    assert case["author"] == "auto-converter"
    assert case["reviewer"] == "pending"


def test_convert_writes_case_and_pytest():
    r = convert(SAMPLE_TRACE_FAILED)
    assert r.skipped_reason is None
    assert r.case_path is not None and r.case_path.exists()
    assert r.pytest_path is not None and r.pytest_path.exists()
    text = r.pytest_path.read_text(encoding="utf-8")
    assert "deadbeef00000001" in text
    assert "@pytest.mark.auto_generated" in text


def test_convert_skips_pii_trace():
    leaky = {
        "trace_id": "leak1",
        "route": "chat",
        "user_query": "我的身份证 110101199001011234，帮我处理",
        "agent_spans": [],
    }
    r = convert(leaky)
    # 双重 scrub 应自动洗掉，但若仍残留就必须 skip
    if r.skipped_reason:
        assert "PII" in r.skipped_reason
    else:
        # case 文件中不应再含原身份证号
        case_text = r.case_path.read_text(encoding="utf-8")
        assert "110101199001011234" not in case_text
        assert "[MASK_ID]" in case_text


def test_convert_skips_unknown_route():
    r = convert({"trace_id": "x", "route": "totally-unknown-route", "agent_spans": []})
    assert r.skipped_reason and "无法识别" in r.skipped_reason


def test_convert_dedupes_pytest_for_same_cluster():
    r1 = convert(SAMPLE_TRACE_FAILED)
    # 修改 trace_id 但保持 cluster_id 不变
    trace2 = json.loads(json.dumps(SAMPLE_TRACE_FAILED))
    trace2["trace_id"] = "xyz999"
    r2 = convert(trace2)
    assert r1.pytest_path == r2.pytest_path
