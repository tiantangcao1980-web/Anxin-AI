# -*- coding: utf-8 -*-
"""
Authz —— Policy Decision Point (PDP)

输入：subject + action + resource + context
输出：Decision + reasons[]

详细文档：docs/governance/AUTHZ-MODEL.md
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger

from src.services.governance.policy_loader import PolicyBundle, get_policy


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_STEP_UP = "REQUIRE_STEP_UP"
    REQUIRE_CONFIRM = "REQUIRE_CONFIRM"


# 严重性：DENY > REQUIRE_STEP_UP > REQUIRE_CONFIRM > ALLOW
_SEVERITY = {
    Decision.DENY: 4,
    Decision.REQUIRE_STEP_UP: 3,
    Decision.REQUIRE_CONFIRM: 2,
    Decision.ALLOW: 1,
}


def _stricter(a: Decision, b: Decision) -> Decision:
    return a if _SEVERITY[a] >= _SEVERITY[b] else b


@dataclass(frozen=True)
class DecisionResult:
    decision: Decision
    reasons: list[dict] = field(default_factory=list)
    policy_snapshot_id: str = ""

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "reasons": self.reasons,
            "policy_snapshot_id": self.policy_snapshot_id,
        }


# Clearance 排序：L1 < L2 < L3 < L4 < L5
_CLEARANCE_ORDER = {"L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}


def _scope_match(rule_scope: str, action: str) -> bool:
    """支持 wildcard。规则：`skill.*.write` 能匹配 `skill.contract.write`。"""
    return fnmatch.fnmatchcase(action, rule_scope)


def _split_top_level(expr: str, sep: str) -> list[str]:
    """按 sep 切分，但忽略引号内出现的 sep（极简，单引号 / 双引号都识别）。"""
    parts: list[str] = []
    buf: list[str] = []
    i = 0
    sep_len = len(sep)
    in_quote: str | None = None
    while i < len(expr):
        ch = expr[i]
        if in_quote:
            buf.append(ch)
            if ch == in_quote:
                in_quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_quote = ch
            buf.append(ch)
            i += 1
            continue
        if expr[i:i+sep_len] == sep:
            parts.append("".join(buf).strip())
            buf = []
            i += sep_len
            continue
        buf.append(ch)
        i += 1
    tail = "".join(buf).strip()
    if tail or parts:
        parts.append(tail)
    return parts


def _eval_condition(expr: str, *, subject: dict, resource: dict, context: dict) -> bool:
    """极简条件表达式求值。安全起见只支持白名单运算符。

    支持顶层 ``and`` / ``or`` 复合（左到右短路；不支持括号嵌套）。
    """
    if not expr or not expr.strip():
        return True

    # 处理 or（更弱）
    parts_or = _split_top_level(expr, " or ")
    if len(parts_or) > 1:
        return any(_eval_condition(p, subject=subject, resource=resource, context=context) for p in parts_or)
    # 处理 and
    parts_and = _split_top_level(expr, " and ")
    if len(parts_and) > 1:
        return all(_eval_condition(p, subject=subject, resource=resource, context=context) for p in parts_and)

    safe = {
        "subject": subject,
        "resource": resource,
        "context": context,
        "L1": "L1", "L2": "L2", "L3": "L3", "L4": "L4", "L5": "L5",
    }

    def _get(path: str) -> Any:
        obj: Any = safe
        for part in path.split("."):
            if isinstance(obj, dict):
                obj = obj.get(part)
            else:
                obj = getattr(obj, part, None)
        return obj

    pattern = re.compile(
        r"^\s*([\w.]+)\s*(==|!=|>=|<=|>|<|in)\s*(.+?)\s*$"
    )
    m = pattern.match(expr)
    if not m:
        logger.warning("无法解析 condition 表达式：{}", expr)
        return True

    lhs_path, op, rhs_raw = m.group(1), m.group(2), m.group(3).strip()
    lhs = _get(lhs_path)

    # 解析右值
    if rhs_raw.startswith("'") and rhs_raw.endswith("'"):
        rhs: Any = rhs_raw[1:-1]
    elif rhs_raw.startswith('"') and rhs_raw.endswith('"'):
        rhs = rhs_raw[1:-1]
    elif rhs_raw.startswith("[") and rhs_raw.endswith("]"):
        # list literal: ['a', 'b']
        rhs = [
            x.strip().strip("'").strip('"')
            for x in rhs_raw[1:-1].split(",")
            if x.strip()
        ]
    elif rhs_raw in ("true", "True"):
        rhs = True
    elif rhs_raw in ("false", "False"):
        rhs = False
    else:
        try:
            rhs = int(rhs_raw)
        except ValueError:
            try:
                rhs = float(rhs_raw)
            except ValueError:
                # 当 path 引用
                rhs = _get(rhs_raw)

    # 比较
    if op == "==":
        return lhs == rhs
    if op == "!=":
        return lhs != rhs
    if op == "in":
        return lhs in (rhs or [])
    # 数值 / clearance
    if isinstance(lhs, str) and lhs in _CLEARANCE_ORDER:
        lhs_v = _CLEARANCE_ORDER[lhs]
    else:
        lhs_v = lhs
    if isinstance(rhs, str) and rhs in _CLEARANCE_ORDER:
        rhs_v = _CLEARANCE_ORDER[rhs]
    else:
        rhs_v = rhs
    try:
        if op == ">=":
            return lhs_v >= rhs_v
        if op == "<=":
            return lhs_v <= rhs_v
        if op == ">":
            return lhs_v > rhs_v
        if op == "<":
            return lhs_v < rhs_v
    except TypeError:
        return False
    return False


def _flatten_roles(matrix: dict, role: str) -> tuple[list[dict], list[dict]]:
    """处理 inherits，返回 (grants, denies) 合并列表。"""
    if role not in matrix.get("roles", {}):
        return [], []
    role_cfg = matrix["roles"][role]
    grants = list(role_cfg.get("grants", []))
    denies = list(role_cfg.get("denies", []))
    for parent in role_cfg.get("inherits", []) or []:
        p_grants, p_denies = _flatten_roles(matrix, parent)
        grants.extend(p_grants)
        denies.extend(p_denies)
    return grants, denies


def decide(
    *,
    subject: dict,
    action: str,
    resource: dict,
    context: dict | None = None,
    policy: PolicyBundle | None = None,
) -> DecisionResult:
    """核心 PDP 函数。

    subject 必含: role, clearance (L1..L5), tenant_id, primary_jurisdiction
    resource 必含: type, id, classification (L1..L5), jurisdiction
    context 可选: amount_cny, mfa_recent, business_hours, jurisdiction_chain, trust_level
    """
    policy = policy or get_policy()
    context = context or {}
    matrix = policy.access_matrix
    reasons: list[dict] = []

    role = subject.get("role", "guest")

    # ── 1. 显式 deny 优先 ─────────────────────────────────────────
    _, denies = _flatten_roles(matrix, role)
    for d in denies:
        scope = d.get("scope", "")
        if _scope_match(scope, action):
            cond = d.get("when") or ""
            if not cond or _eval_condition(cond, subject=subject, resource=resource, context=context):
                reasons.append({"rule": "role-deny", "value": f"role={role} denied scope={scope}"})
                return DecisionResult(Decision.DENY, reasons, policy.snapshot_id)

    # ── 2. role grants ────────────────────────────────────────────
    grants, _ = _flatten_roles(matrix, role)
    role_decision: Decision | None = None
    for g in grants:
        scope = g.get("scope", "")
        if not _scope_match(scope, action):
            continue
        # 条件
        cond_ok = True
        for c in g.get("conditions", []) or []:
            if not _eval_condition(c, subject=subject, resource=resource, context=context):
                cond_ok = False
                reasons.append({"rule": "role-grant-cond-fail", "value": f"scope={scope} cond={c}"})
                break
        if not cond_ok:
            continue
        d = Decision(g.get("decision", "ALLOW"))
        reasons.append({"rule": "role-grant", "value": f"role={role} scope={scope} -> {d.value}"})
        if role_decision is None:
            role_decision = d
        else:
            role_decision = _stricter(role_decision, d)

    if role_decision is None:
        # 没有匹配的 grant — default deny
        default = Decision(matrix.get("default_decision", "DENY"))
        reasons.append({"rule": "default-deny", "value": f"no matching grant for role={role}"})
        result_decision = default
    else:
        result_decision = role_decision

    # ── 3. 全局 gates（再加严，永不放宽）──────────────────────────
    for gate in matrix.get("global_gates", []) or []:
        m = gate.get("match", "")
        if not _scope_match(m, action):
            continue
        when = gate.get("when") or ""
        if when and not _eval_condition(when, subject=subject, resource=resource, context=context):
            continue
        enforce = Decision(gate.get("enforce", "DENY"))
        reasons.append({"rule": "global-gate", "value": f"match={m} when={when or '*'} enforce={enforce.value}"})
        result_decision = _stricter(result_decision, enforce)

    # ── 4. Clearance 校验（subject.clearance ≥ resource.classification）─
    if resource.get("classification") in _CLEARANCE_ORDER:
        s_lvl = _CLEARANCE_ORDER.get(subject.get("clearance", "L1"), 1)
        r_lvl = _CLEARANCE_ORDER[resource["classification"]]
        if s_lvl < r_lvl:
            reasons.append({
                "rule": "classification-gate",
                "value": f"clearance={subject.get('clearance')} < classification={resource['classification']} → DENY",
            })
            result_decision = _stricter(result_decision, Decision.DENY)

    # ── 5. 跨境 ───────────────────────────────────────────────────
    r_juris = resource.get("jurisdiction")
    s_juris = subject.get("primary_jurisdiction", policy.jurisdiction_rules.get("default_jurisdiction", "CN"))
    if r_juris and r_juris != s_juris:
        for rule in policy.jurisdiction_rules.get("cross_border", []) or []:
            src, dst = rule.get("source"), rule.get("dest")
            if src in (s_juris, "*") and dst in (r_juris, "*"):
                cross_decision = Decision(rule.get("rule", "REQUIRE_CONFIRM"))
                reasons.append({
                    "rule": "jurisdiction-gate",
                    "value": f"{s_juris}→{r_juris} requires={rule.get('requires', [])} -> {cross_decision.value}",
                })
                result_decision = _stricter(result_decision, cross_decision)
                break

    return DecisionResult(
        decision=result_decision,
        reasons=reasons,
        policy_snapshot_id=policy.snapshot_id,
    )


__all__ = ["Decision", "DecisionResult", "decide"]
