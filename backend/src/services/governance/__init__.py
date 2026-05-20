# -*- coding: utf-8 -*-
"""
Governance —— 治理与权限边界服务

doctrine 见 docs/governance/，policy 见 policy/*.yaml。

模块拓扑：

    policy_loader.py  ← 加载 + 校验 6 个 policy/*.yaml；热重载
    authz.py          ← PDP：decide(subject, action, resource, context) -> Decision
    audit.py          ← 审计日志双写：JSONL + DB
    data_classifier.py← 数据分级 + PII 识别 + 脱敏 / 还原
    trust.py          ← Trust level 计算 + revoked.json 维护
    tool_scope.py     ← Skill / Cookbook 调用 tool 时的白名单二次校验
    skill_lifecycle.py← Skill 状态机 + 状态迁移守门

设计原则：
- **Default deny**：未显式 allow 的访问一律拒绝。
- **PDP / PEP 分离**：本模块只做判定；FastAPI dependency / decorator 做执行。
- **可解释性**：每个 decide() 返回 (decision, reasons[])，写审计。
- **可重放**：policy snapshot id 写入审计；6 个月后能用当时 policy 重放。
"""
from __future__ import annotations

from src.services.governance.authz import (
    Decision,
    DecisionResult,
    decide,
)
from src.services.governance.audit import audit_log, write_event
from src.services.governance.data_classifier import (
    Classification,
    PIIFinding,
    classify,
    mask,
    unmask,
)
from src.services.governance.policy_loader import (
    PolicyBundle,
    get_policy,
    reload_policy,
)
from src.services.governance.skill_lifecycle import (
    LifecycleStage,
    can_transition,
    transition,
)
from src.services.governance.tool_scope import enforce_tool_call
from src.services.governance.trust import TrustLevel, evaluate_trust
from src.services.governance import confirm_inbox, shadow_runner
from src.services.governance.external_send_gate import guard_external_send

__all__ = [
    # authz
    "Decision",
    "DecisionResult",
    "decide",
    # audit
    "audit_log",
    "write_event",
    # data_classifier
    "Classification",
    "PIIFinding",
    "classify",
    "mask",
    "unmask",
    # policy
    "PolicyBundle",
    "get_policy",
    "reload_policy",
    # lifecycle
    "LifecycleStage",
    "can_transition",
    "transition",
    # tool scope
    "enforce_tool_call",
    # trust
    "TrustLevel",
    "evaluate_trust",
    # PEP-4 + shadow
    "confirm_inbox",
    "shadow_runner",
    "guard_external_send",
]
