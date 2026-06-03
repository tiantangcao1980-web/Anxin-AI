# -*- coding: utf-8 -*-
"""
自愈闭环测试（O2）

验证：
- severity 评分对各档信号合理
- 业务禁列（auth/payment/...）永远 critical + 不允许 auto-heal
- dispatcher 的"何时派 agent / 何时派人"决策正确
- agent 路径白名单：CODEOWNERS / .github / 商业化代码不可改
"""

import pytest

from scripts.self_heal.dispatcher import (
    AGENT_FORBIDDEN_PATHS,
    Assignee,
    decide,
    is_path_safe_for_agent,
)
from scripts.self_heal.severity import (
    ClusterSignal,
    Severity,
    is_auto_heal_allowed,
    score_cluster,
    to_severity,
)


def make_sig(**kw) -> ClusterSignal:
    defaults = {
        "cluster_id": "abc123",
        "occurrence_per_hour": 10.0,
        "affected_users": 5,
        "routes": ["chat"],
        "error_class": "llm",
        "business_critical": False,
    }
    defaults.update(kw)
    return ClusterSignal(**defaults)


# ===== severity =====

class TestSeverity:
    def test_baseline_signal_is_at_least_medium(self):
        """评分体系下，进入聚类即基础贡献 → 最低 MEDIUM（避免漏触发）"""
        sig = make_sig(occurrence_per_hour=1, affected_users=1, routes=["other"], error_class="logic")
        score, _ = score_cluster(sig)
        sev = to_severity(score, sig)
        assert sev in (Severity.LOW, Severity.MEDIUM)
        assert sev != Severity.HIGH

    def test_high_with_many_users(self):
        sig = make_sig(occurrence_per_hour=80, affected_users=40, routes=["chat"], error_class="db")
        score, _ = score_cluster(sig)
        sev = to_severity(score, sig)
        assert sev in (Severity.HIGH, Severity.CRITICAL)

    def test_business_critical_overrides_to_critical(self):
        sig = make_sig(occurrence_per_hour=1, affected_users=1, business_critical=True)
        score, _ = score_cluster(sig)
        assert to_severity(score, sig) == Severity.CRITICAL

    def test_payment_route_locks_critical(self):
        sig = make_sig(routes=["payment"])
        score, _ = score_cluster(sig)
        assert to_severity(score, sig) == Severity.CRITICAL
        assert not is_auto_heal_allowed(sig)

    def test_alembic_route_locks_critical(self):
        sig = make_sig(routes=["alembic_migration"])
        assert not is_auto_heal_allowed(sig)


# ===== dispatcher =====

class TestDispatcher:
    def test_low_signal_assigns_agent_with_max_3_iter(self):
        d = decide(make_sig(occurrence_per_hour=2, affected_users=2, routes=["other"], error_class="logic"))
        assert d.assignee == Assignee.AGENT
        assert d.max_iterations == 3
        assert d.requires_human_review is True

    def test_high_signal_assigns_agent_with_human_review(self):
        d = decide(make_sig(occurrence_per_hour=80, affected_users=40, error_class="db"))
        assert d.assignee in (Assignee.AGENT, Assignee.HUMAN_ONCALL)
        if d.severity == Severity.HIGH:
            assert d.assignee == Assignee.AGENT
            assert d.max_iterations == 2
        if d.severity == Severity.CRITICAL:
            assert d.assignee == Assignee.HUMAN_ONCALL

    def test_payment_route_assigns_human_only(self):
        d = decide(make_sig(routes=["payment"]))
        assert d.assignee == Assignee.HUMAN_ONCALL
        assert d.max_iterations == 0
        assert d.severity == Severity.CRITICAL

    def test_business_critical_flag_routes_to_human(self):
        d = decide(make_sig(business_critical=True))
        assert d.assignee == Assignee.HUMAN_ONCALL


# ===== agent path safety =====

class TestPathSafety:
    @pytest.mark.parametrize("path", [
        "CODEOWNERS",
        ".github/workflows/ci.yml",
        ".github/workflows/ai-review.yml",
        "AGENTS.md",
        "DESIGN.md",
        "backend/src/services/subscription_service.py",
        "backend/src/services/payment_service.py",
        "backend/src/api/routes/auth.py",
        "backend/alembic/versions/abc_migrate.py",
    ])
    def test_forbidden_paths_blocked(self, path):
        assert is_path_safe_for_agent(path, AGENT_FORBIDDEN_PATHS) is False

    @pytest.mark.parametrize("path", [
        "backend/src/services/chat_service.py",
        "backend/src/agents/legal_advisor.py",
        "frontend/src/pages/Chat.tsx",
        "skills/agents/legal-advisor/SKILL.md",
    ])
    def test_allowed_paths_pass(self, path):
        assert is_path_safe_for_agent(path, AGENT_FORBIDDEN_PATHS) is True
