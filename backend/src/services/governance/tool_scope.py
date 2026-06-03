# -*- coding: utf-8 -*-
"""
ToolScope —— skill / cookbook 调用 tool 时的白名单二次校验（PEP 第三层）

任意 skill 在沙箱里调用某 tool 时，sandbox provider 必须先调
`enforce_tool_call(skill_id=..., tool=..., target=...)`：
返回 ALLOW / CONFIRM / DENY。

规则源 policy/tool-allowlist.yaml。
"""
from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from enum import Enum

from src.services.governance.policy_loader import get_policy


class ToolDecision(str, Enum):
    ALLOW = "ALLOW"
    CONFIRM = "REQUIRE_CONFIRM"
    DENY = "DENY"


@dataclass(frozen=True)
class ToolEnforcement:
    decision: ToolDecision
    reason: str
    audit_event: str = ""


def _tool_category(policy: dict, tool: str) -> str | None:
    """从 tool_categories 反查 tool 所属类。"""
    for cat, cfg in policy.get("tool_categories", {}).items():
        if tool in (cfg.get("tools") or []):
            return cat
    return None


def _host_match(host: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(host, p) for p in (patterns or []))


def enforce_tool_call(
    *,
    skill_id: str,
    tool: str,
    target_host: str | None = None,
    persona: str | None = None,
    is_cookbook: bool = False,
    cookbook_name: str | None = None,
    trust_level: str = "verified",
) -> ToolEnforcement:
    policy = get_policy().tool_allowlist

    # 1. 找到 effective config（per-skill override > cookbook override > persona default）
    overrides = policy.get("skill_overrides", {}) or {}
    cb_overrides = policy.get("cookbook_overrides", {}) or {}
    persona_defaults = policy.get("persona_defaults", {}) or {}

    eff = None
    if is_cookbook and cookbook_name and cookbook_name in cb_overrides:
        eff = cb_overrides[cookbook_name]
    elif skill_id in overrides:
        eff = overrides[skill_id]
    elif persona and persona in persona_defaults:
        eff = persona_defaults[persona]

    if eff is None:
        return ToolEnforcement(
            ToolDecision.DENY,
            f"no allowlist for skill={skill_id} persona={persona}",
            audit_event="tool.violation.unlisted",
        )

    # 2. 类目分析
    category = _tool_category(policy, tool)
    if category is None:
        return ToolEnforcement(
            ToolDecision.DENY,
            f"tool={tool} 未在 tool_categories 注册",
            audit_event="tool.violation.unlisted",
        )

    # 3. allow / confirm / deny
    if category in (eff.get("deny") or []):
        return ToolEnforcement(
            ToolDecision.DENY,
            f"tool category={category} explicitly denied for {skill_id}",
            audit_event="tool.violation.unlisted",
        )
    if category in (eff.get("confirm") or []):
        return ToolEnforcement(
            ToolDecision.CONFIRM,
            f"tool category={category} requires confirm for {skill_id}",
        )
    if category not in (eff.get("allow") or []):
        return ToolEnforcement(
            ToolDecision.DENY,
            f"tool category={category} not in allow list for {skill_id}",
            audit_event="tool.violation.unlisted",
        )

    # 4. egress 域名白名单
    if category == "network_egress" and target_host:
        egress = eff.get("explicit_egress_allowlist") or []
        if egress and not _host_match(target_host, egress):
            return ToolEnforcement(
                ToolDecision.DENY,
                f"host={target_host} not in egress allowlist for {skill_id}",
                audit_event="tool.violation.egress_host",
            )

    # 5. untrusted skill 外发再次守门
    if category == "external_send" and trust_level == "untrusted":
        return ToolEnforcement(
            ToolDecision.DENY,
            "untrusted skill 不允许 external_send",
            audit_event="tool.violation.untrusted_send",
        )

    return ToolEnforcement(ToolDecision.ALLOW, f"OK category={category}")


__all__ = ["ToolDecision", "ToolEnforcement", "enforce_tool_call"]
