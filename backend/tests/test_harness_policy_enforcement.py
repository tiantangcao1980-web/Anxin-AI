# -*- coding: utf-8 -*-
"""
Harness Policy Enforcement 测试（H1 P0 followup）

验证：
1. ALLOW → allowed=True
2. DENY + warn-only(默认) → allowed=True + decision=deny + enforced=false
3. DENY + enforce(HARNESS_POLICY_ENFORCE=true) → allowed=False + enforced=true
4. REQUIRE_APPROVAL → 当前 warn-only 视同放行 + warn 日志
5. policy 异常 → allowed=True（不拖垮主路径）+ decision=policy_error
6. 异常路径必须 ERROR 级别日志（不能吞 debug）
"""

import logging

import pytest

from src.harness import policy_enforcement
from src.harness.policy_engine import (
    PolicyCheckResult,
    PolicyDecision,
    policy_engine,
)


@pytest.fixture
def warn_only_env(monkeypatch):
    monkeypatch.delenv("HARNESS_POLICY_ENFORCE", raising=False)


@pytest.fixture
def enforce_env(monkeypatch):
    monkeypatch.setenv("HARNESS_POLICY_ENFORCE", "true")


@pytest.fixture
def policy_stub(monkeypatch):
    """提供一个可控的 policy_engine.check_tool_access。"""
    calls = {}

    def fake(agent_name, tool_name):
        return calls["return_value"]

    monkeypatch.setattr(policy_engine, "check_tool_access", fake)
    return calls


def _result(decision: PolicyDecision, reason: str = "test") -> PolicyCheckResult:
    return PolicyCheckResult(decision=decision, reason=reason)


# ===== ALLOW =====

class TestAllow:
    @pytest.mark.asyncio
    async def test_allow_returns_true(self, warn_only_env, policy_stub):
        policy_stub["return_value"] = _result(PolicyDecision.ALLOW)
        allowed, info = await policy_enforcement.check_tool_call("legal_advisor", "search")
        assert allowed is True
        assert info["decision"] == "allow"
        assert info["enforce_mode"] is False


# ===== DENY 在 warn-only 默认下不阻断 =====

class TestDenyWarnOnly:
    @pytest.mark.asyncio
    async def test_deny_warn_only_does_not_block(self, warn_only_env, policy_stub, caplog):
        policy_stub["return_value"] = _result(PolicyDecision.DENY, "out of whitelist")
        with caplog.at_level(logging.WARNING):
            allowed, info = await policy_enforcement.check_tool_call("legal_advisor", "send_email")
        assert allowed is True, "warn-only 模式 DENY 不能真阻断"
        assert info["decision"] == "deny"
        assert info["enforced"] is False

    @pytest.mark.asyncio
    async def test_deny_warn_only_logs_warning(self, warn_only_env, policy_stub, monkeypatch):
        policy_stub["return_value"] = _result(PolicyDecision.DENY)
        captured = []
        monkeypatch.setattr(
            "src.harness.policy_enforcement.logger.warning",
            lambda msg, *a, **kw: captured.append(msg),
        )
        await policy_enforcement.check_tool_call("legal_advisor", "wire_money")
        assert any("DENY" in m and "warn-only" in m for m in captured)


# ===== DENY 在 enforce 模式下真阻断 =====

class TestDenyEnforce:
    @pytest.mark.asyncio
    async def test_deny_enforce_blocks(self, enforce_env, policy_stub):
        policy_stub["return_value"] = _result(PolicyDecision.DENY, "blocked")
        allowed, info = await policy_enforcement.check_tool_call("legal_advisor", "wire_money")
        assert allowed is False, "enforce 模式 DENY 必须阻断"
        assert info["enforced"] is True
        assert info["enforce_mode"] is True


# ===== REQUIRE_APPROVAL =====

class TestRequireApproval:
    @pytest.mark.asyncio
    async def test_approval_warn_only_passes(self, warn_only_env, policy_stub):
        """A6: warn-only 模式 + 未注入 db → 不创建工单, 仍放行 + warn"""
        policy_stub["return_value"] = _result(PolicyDecision.REQUIRE_APPROVAL, "needs review")
        allowed, info = await policy_enforcement.check_tool_call("contract_reviewer", "esign")
        assert allowed is True
        assert info["decision"] == "require_approval"
        assert info["enforced"] is False
        # 没传 db, 不应有 approval_id
        assert "approval_id" not in info

    @pytest.mark.asyncio
    async def test_approval_enforce_without_db_still_passes(self, enforce_env, policy_stub):
        """A6: enforce 模式但未注入 db → 工单无法创建, 退化为 warn-only 放行 (保持向下兼容)"""
        policy_stub["return_value"] = _result(PolicyDecision.REQUIRE_APPROVAL)
        allowed, info = await policy_enforcement.check_tool_call("contract_reviewer", "esign")
        assert allowed is True
        assert "approval_id" not in info


# ===== policy 异常 =====

class TestPolicyException:
    @pytest.mark.asyncio
    async def test_exception_does_not_block_main_path(self, warn_only_env, monkeypatch):
        def boom(agent_name, tool_name):
            raise RuntimeError("policy down")
        monkeypatch.setattr(policy_engine, "check_tool_access", boom)
        allowed, info = await policy_enforcement.check_tool_call("legal_advisor", "search")
        assert allowed is True, "policy 异常不能让主路径挂"
        assert info["decision"] == "policy_error"

    @pytest.mark.asyncio
    async def test_exception_logs_error_not_debug(self, warn_only_env, monkeypatch):
        def boom(agent_name, tool_name):
            raise RuntimeError("policy down")
        monkeypatch.setattr(policy_engine, "check_tool_access", boom)
        captured_error = []
        captured_debug = []
        monkeypatch.setattr(
            "src.harness.policy_enforcement.logger.error",
            lambda msg, *a, **kw: captured_error.append(msg),
        )
        monkeypatch.setattr(
            "src.harness.policy_enforcement.logger.debug",
            lambda msg, *a, **kw: captured_debug.append(msg),
        )
        await policy_enforcement.check_tool_call("legal_advisor", "search")
        # 关键契约：异常必须 ERROR，不能吞成 debug
        assert any("policy_engine" in m for m in captured_error)
        assert all("policy_engine" not in m for m in captured_debug)


# ===== A7: trace_context 写入 _policy_info =====

class TestTracePolicyInfo:
    @pytest.mark.asyncio
    async def test_deny_writes_to_trace_policy_info(self, enforce_env, policy_stub):
        """A7: DENY 决策写入 current_trace._policy_info, ALLOW 不写。"""
        from src.harness.trace_context import end_trace, start_trace

        trace = start_trace(user_id="u_a7")
        try:
            policy_stub["return_value"] = _result(PolicyDecision.DENY, "blocked_a7")
            await policy_enforcement.check_tool_call("agent_a7", "send_email")

            summary = trace.to_summary()
            policy_info = summary.get("_policy_info", [])
            assert len(policy_info) == 1
            assert policy_info[0]["decision"] == "deny"
            assert policy_info[0]["tool"] == "send_email"
            assert policy_info[0]["enforced"] is True
            assert policy_info[0]["reason"] == "blocked_a7"
            assert "ts" in policy_info[0]
        finally:
            end_trace()

    @pytest.mark.asyncio
    async def test_allow_does_not_pollute_trace_policy_info(self, warn_only_env, policy_stub):
        """A7: ALLOW 不写, 避免高频 ALLOW 撑爆 trace metadata。"""
        from src.harness.trace_context import end_trace, start_trace

        trace = start_trace(user_id="u_a7b")
        try:
            policy_stub["return_value"] = _result(PolicyDecision.ALLOW)
            for _ in range(5):
                await policy_enforcement.check_tool_call("agent_a7b", "search")

            summary = trace.to_summary()
            assert summary.get("_policy_info", []) == []
        finally:
            end_trace()
