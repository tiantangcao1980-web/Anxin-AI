# -*- coding: utf-8 -*-
"""
Policy Engine 强制接入（H1 P0 followup）

H0 体检发现 policy_engine 18 个策略已注册但**主路径 0 调用** —— 任何 agent
调任何工具都不过权限检查。本模块把 `policy_engine.check_tool_access` 接到
`agents/base.py` 的 tool_call 执行前。

护栏：
  - **默认 warn-only**：DENY 仅 log + 记 audit，不阻断（先观察 1 周避免误伤）
  - 切 enforce 模式靠环境变量 HARNESS_POLICY_ENFORCE=true
  - REQUIRE_APPROVAL 不实现真审批（接 approvals 是后续 PR），warn-only 模式下视作放行
  - 异常视同放行（避免 policy 层故障导致主路径全挂）

返回的 (allowed, decision_dict)：
  allowed: True 时主路径继续；False 时 enforce 模式下应短路
  decision_dict: 写入 trace_context 的 metadata，便于 admin 审计
"""

from __future__ import annotations

import os
from typing import Tuple

from loguru import logger

from src.harness.policy_engine import PolicyDecision, policy_engine


def _is_enforce_mode() -> bool:
    """读环境变量；默认 False（warn-only）。"""
    return os.environ.get("HARNESS_POLICY_ENFORCE", "false").lower() in {"true", "1", "yes"}


# 拒绝时返回给 agent 的 tool_output（agent 会把这段塞回 LLM 上下文）
DENY_TOOL_OUTPUT = (
    "[工具调用被策略拒绝] 该工具不在你的权限白名单内，或风险等级超出限制。"
    "请改用其他工具，或将该操作转人工审批。"
)


def check_tool_call(agent_name: str, tool_name: str) -> Tuple[bool, dict]:
    """检查 agent 是否可调用 tool。

    返回 (allowed, decision_dict)。warn-only 模式下 allowed 始终为 True。
    """
    enforce = _is_enforce_mode()
    decision_dict = {
        "agent": agent_name,
        "tool": tool_name,
        "enforce_mode": enforce,
    }

    try:
        result = policy_engine.check_tool_access(agent_name=agent_name, tool_name=tool_name)
    except Exception as e:  # noqa: BLE001
        # 关键：policy 故障不能让主路径全挂
        logger.error(f"[Harness] policy_engine 调用异常 agent={agent_name} tool={tool_name}: {e}")
        decision_dict.update({"decision": "policy_error", "reason": str(e)})
        return True, decision_dict

    decision_dict.update({
        "decision": result.decision.value,
        "reason": result.reason,
    })

    if result.decision == PolicyDecision.ALLOW:
        return True, decision_dict

    if result.decision == PolicyDecision.REQUIRE_APPROVAL:
        # 后续 PR 接 approvals 工作流；当前 warn-only 模式视同放行 + warn
        logger.warning(
            f"[Harness][policy] REQUIRE_APPROVAL agent={agent_name} tool={tool_name} "
            f"reason={result.reason} (warn-only, 后续接 approvals)"
        )
        decision_dict["enforced"] = False
        return True, decision_dict

    # DENY 分支
    if enforce:
        logger.warning(
            f"[Harness][policy] DENY agent={agent_name} tool={tool_name} "
            f"reason={result.reason} ENFORCED"
        )
        decision_dict["enforced"] = True
        return False, decision_dict

    # warn-only
    logger.warning(
        f"[Harness][policy] DENY agent={agent_name} tool={tool_name} "
        f"reason={result.reason} (warn-only, 实际放行；切换 enforce 设 HARNESS_POLICY_ENFORCE=true)"
    )
    decision_dict["enforced"] = False
    return True, decision_dict
