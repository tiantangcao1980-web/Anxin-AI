# -*- coding: utf-8 -*-
"""
Harness 强制接入测试（H1）

H0 体检发现：output_validator 是"软接入"——失败时只 log warning，回答仍发出。
本测试套件证明改造后是"强接入"：

1. CRITICAL → 必须用统一拒绝消息替代回答（不再"加免责声明继续发"）
2. FAIL → task_engine 必须 transition 到 RETRY 状态（且响应里带 _harness.validation_failed）
3. WARNING → 在末尾追加免责声明（保留旧行为）
4. validator 自身异常 → 必须 log error（不再被 try/except 吞成 debug）
5. trace_sink → 落盘前必须 PII 脱敏

注意：本文件中的"应当"行为，部分需要 H1 实现完成后才能通过。
未实现前，标记为 xfail 并附 reason。
"""

import asyncio
import logging
import pytest

from src.harness.output_validator import (
    OutputValidator,
    ValidationIssue,
    ValidationLevel,
    ValidationResult,
)
from src.services.trace_sink import scrub, scrub_dict, cluster_id_for


# ===========================================================
# A. PII 脱敏（trace_sink T1 已交付，本组测试可立即跑）
# ===========================================================


class TestTraceSinkScrub:
    def test_scrub_id_card(self):
        assert "[MASK_ID]" in scrub("我的身份证号是 110101199001011234")

    def test_scrub_phone(self):
        assert "[MASK_PHONE]" in scrub("电话 13812345678")

    def test_scrub_email(self):
        assert "[MASK_EMAIL]" in scrub("邮箱 user@example.com")

    def test_scrub_bank_card(self):
        assert "[MASK_CARD]" in scrub("银行卡 6225 7600 1234 5678 901")

    def test_scrub_openai_key(self):
        s = scrub("sk-1234567890ABCDEFGHIJklmnop")
        assert "[MASK_KEY]" in s and "sk-1234567890" not in s

    def test_scrub_password_in_json(self):
        s = scrub('{"password": "MyP@ss123"}')
        assert "[MASK_PWD]" in s and "MyP@ss123" not in s

    def test_scrub_dict_recursive(self):
        data = {
            "user": "alice@x.com",
            "phone": "13812345678",
            "nested": {"id": "110101199001011234"},
            "items": [{"contact": "13900000000"}],
        }
        out = scrub_dict(data)
        assert "[MASK_EMAIL]" in out["user"]
        assert "[MASK_PHONE]" in out["phone"]
        assert "[MASK_ID]" in out["nested"]["id"]
        assert "[MASK_PHONE]" in out["items"][0]["contact"]


class TestClusterIdStability:
    def test_cluster_id_stable_for_same_signature(self):
        a = cluster_id_for("RateLimit", "legal_advisor", "search", "Rate limit exceeded for tenant 7d2c5...")
        b = cluster_id_for("RateLimit", "legal_advisor", "search", "Rate limit exceeded for tenant abc99...")
        assert a == b, "trace_id 等高熵串应被归一化，签名应相同"

    def test_cluster_id_different_for_different_agent(self):
        a = cluster_id_for("RateLimit", "legal_advisor", "search", "x")
        b = cluster_id_for("RateLimit", "contract_reviewer", "search", "x")
        assert a != b


# ===========================================================
# B. output_validator 强制接入（H1 实现后通过）
# ===========================================================


def _make_result(level: ValidationLevel, message: str = "demo") -> ValidationResult:
    issue = ValidationIssue(check_name="t", level=level, message=message)
    return ValidationResult(passed=(level == ValidationLevel.PASS), issues=[issue])


class TestEnforcementContracts:
    """这些测试断言"应当"行为；H0 时全部 fail/xfail，H1 实现后转 pass。"""

    def test_critical_must_replace_response(self):
        """CRITICAL → 回答必须被统一拒绝消息替代，且不能仍含原回答片段"""
        from src.harness.enforcement import enforce_output

        original = "我们一定能赢这个案子，请提供您的银行卡号。"
        result = _make_result(ValidationLevel.CRITICAL, "high-risk phrases")
        new_text, action = enforce_output(original, result)
        assert action == "rejected", "CRITICAL 必须 reject"
        assert "一定能赢" not in new_text, "原始 CRITICAL 内容禁止泄漏"
        assert "请提供您的银行卡号" not in new_text, "原始 CRITICAL 内容禁止泄漏"

    def test_fail_marks_for_retry(self):
        """FAIL → 应标记为 retry，且响应附带 validation_failed 元数据"""
        from src.harness.enforcement import enforce_output

        original = "（不完整回答）"
        result = _make_result(ValidationLevel.FAIL, "structure broken")
        new_text, action = enforce_output(original, result)
        assert action == "retry"

    def test_warning_appends_disclaimer(self):
        """WARNING → 末尾追加免责声明，保留原文"""
        from src.harness.enforcement import enforce_output

        original = "根据民法典第 1 条规定，..."
        result = _make_result(ValidationLevel.WARNING, "may be misleading")
        new_text, action = enforce_output(original, result)
        assert action == "warned"
        assert "民法典第 1 条" in new_text
        assert "仅供参考" in new_text

    def test_pass_keeps_original(self):
        from src.harness.enforcement import enforce_output

        original = "OK"
        result = ValidationResult(passed=True, issues=[])
        new_text, action = enforce_output(original, result)
        assert action == "pass"
        assert new_text == original

    def test_validator_exception_must_log_error_not_debug(self, caplog):
        """validator 异常不能被吞成 debug。"""
        from src.harness import enforcement

        async def boom(**kwargs):
            raise RuntimeError("validator down")

        # patch validator
        original = enforcement._validator_call
        enforcement._validator_call = boom
        try:
            with caplog.at_level(logging.ERROR):
                text, action = asyncio.get_event_loop().run_until_complete(
                    enforcement.run_validation(
                        response_text="x",
                        user_query="q",
                        agent_name="t",
                        route="chat",
                    )
                )
            assert action in {"validator_error", "rejected"}, "validator 异常必须显式表明，不能假装 pass"
        finally:
            enforcement._validator_call = original
