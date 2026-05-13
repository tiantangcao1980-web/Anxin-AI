# -*- coding: utf-8 -*-
"""
自愈闭环 - 派发决策（O2）

输入：cluster signal + severity
输出：Decision（assignee + 流程）

约束：
- critical / 业务敏感 → 仅人
- low/medium/high 且非禁列 → agent + iter limit
- 禁止 agent 改 CODEOWNERS / .github/workflows / AGENTS.md / 商业化代码
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scripts.self_heal.severity import (
    ClusterSignal,
    Severity,
    is_auto_heal_allowed,
    to_severity,
)


class Assignee(str, Enum):
    AGENT = "agent"
    HUMAN_ONCALL = "human_oncall"
    HUMAN_REVIEWER = "human_reviewer"
    REJECT = "reject"


# Agent 不允许改的路径
AGENT_FORBIDDEN_PATHS = [
    "CODEOWNERS",
    ".github/workflows/",
    "AGENTS.md",
    "DESIGN.md",
    "CLAUDE.md",
    "backend/src/services/subscription_service.py",
    "backend/src/services/billing_service.py",
    "backend/src/services/payment_service.py",
    "backend/src/services/refund_service.py",
    "backend/src/services/esign_service.py",
    "backend/src/api/routes/auth.py",
    "backend/src/api/routes/billing.py",
    "backend/src/api/routes/payments.py",
    "backend/alembic/",
]


@dataclass
class Decision:
    assignee: Assignee
    severity: Severity
    score: float
    reason: str
    max_iterations: int  # agent 修复循环上限
    requires_human_review: bool
    forbidden_paths: list[str]


def decide(sig: ClusterSignal) -> Decision:
    score, _ = (lambda s: (s, None))(0)  # placeholder, real call below
    from scripts.self_heal.severity import score_cluster as _score
    score, _ = _score(sig)
    sev = to_severity(score, sig)

    if sev == Severity.CRITICAL or not is_auto_heal_allowed(sig):
        return Decision(
            assignee=Assignee.HUMAN_ONCALL,
            severity=sev,
            score=score,
            reason="critical 严重度或命中业务禁列（auth/payment/...）",
            max_iterations=0,
            requires_human_review=True,
            forbidden_paths=AGENT_FORBIDDEN_PATHS,
        )

    if sev == Severity.HIGH:
        return Decision(
            assignee=Assignee.AGENT,
            severity=sev,
            score=score,
            reason="high 严重度：agent 修复 + 强制 human review",
            max_iterations=2,
            requires_human_review=True,
            forbidden_paths=AGENT_FORBIDDEN_PATHS,
        )

    # low / medium → agent 自愈，仍需人 dismiss draft
    return Decision(
        assignee=Assignee.AGENT,
        severity=sev,
        score=score,
        reason="低/中严重度：agent 自愈循环",
        max_iterations=3,
        requires_human_review=True,  # 永不 auto-merge
        forbidden_paths=AGENT_FORBIDDEN_PATHS,
    )


def is_path_safe_for_agent(path: str, forbidden: list[str]) -> bool:
    return not any(path == f or path.startswith(f) for f in forbidden)
