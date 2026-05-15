# -*- coding: utf-8 -*-
"""
SkillLifecycle —— 状态机 + 状态迁移守门

约定见 docs/governance/SKILL-LIFECYCLE.md，规则源 policy/skill-lifecycle.yaml。
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from loguru import logger

from src.services.governance.audit import write_event
from src.services.governance.policy_loader import get_policy


class LifecycleStage(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"
    REVOKED = "REVOKED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class TransitionResult:
    allowed: bool
    reasons: list[str]
    required_gates: list[str]


GateRunner = Callable[[dict], bool]


def _matching_transitions(policy: dict, src: str, dst: str) -> list[dict]:
    out = []
    for t in policy.get("transitions", []) or []:
        if t.get("from") == src and t.get("to") == dst:
            out.append(t)
    return out


def can_transition(
    *,
    skill_id: str,
    from_stage: LifecycleStage,
    to_stage: LifecycleStage,
    actor: dict,
    gate_runners: dict[str, GateRunner] | None = None,
    context: dict | None = None,
) -> TransitionResult:
    policy = get_policy().skill_lifecycle
    candidates = _matching_transitions(policy, from_stage.value, to_stage.value)
    if not candidates:
        return TransitionResult(
            False,
            [f"未注册的迁移 {from_stage.value} → {to_stage.value}"],
            [],
        )

    # 取第一条匹配的
    spec = candidates[0]
    required_actor = spec.get("actor")
    gates: list[str] = spec.get("gates") or []
    reasons: list[str] = []
    allowed = True

    # actor 校验
    actor_role = actor.get("role")
    if required_actor and required_actor not in (
        actor_role,
        f"{actor_role}_role",
        actor.get("type"),
    ):
        reasons.append(f"actor={actor_role}/{actor.get('type')} 不符合 required={required_actor}")
        allowed = False

    # gates 校验
    context = context or {}
    for g in gates:
        runner = (gate_runners or {}).get(g)
        if runner is None:
            reasons.append(f"gate={g} 未提供 runner → 视为未通过")
            allowed = False
            continue
        ok = bool(runner(context))
        reasons.append(f"gate={g} → {'pass' if ok else 'fail'}")
        if not ok:
            allowed = False

    return TransitionResult(allowed=allowed, reasons=reasons, required_gates=gates)


def transition(
    *,
    skill_id: str,
    from_stage: LifecycleStage,
    to_stage: LifecycleStage,
    actor: dict,
    gate_runners: dict[str, GateRunner] | None = None,
    context: dict | None = None,
) -> TransitionResult:
    """执行迁移（含审计）。"""
    res = can_transition(
        skill_id=skill_id,
        from_stage=from_stage,
        to_stage=to_stage,
        actor=actor,
        gate_runners=gate_runners,
        context=context,
    )
    write_event({
        "event_type": "lifecycle.change",
        "actor": actor,
        "resource": {"type": "skill", "id": skill_id},
        "from_stage": from_stage.value,
        "to_stage": to_stage.value,
        "decision": "ALLOW" if res.allowed else "DENY",
        "outcome": "success" if res.allowed else "rejected",
        "reasons": res.reasons,
    })
    if not res.allowed:
        logger.warning("Skill 迁移被拒：{} {}→{} reasons={}",
                       skill_id, from_stage.value, to_stage.value, res.reasons)
    return res


__all__ = ["LifecycleStage", "TransitionResult", "can_transition", "transition"]
