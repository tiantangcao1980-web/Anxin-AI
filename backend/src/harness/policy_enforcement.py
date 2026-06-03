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
from typing import Any

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


async def check_tool_call(
    agent_name: str,
    tool_name: str,
    *,
    enforce: bool | None = None,
    db: Any | None = None,
    org_id: str | None = None,
    requested_by: str | None = None,
    action_payload: dict[str, Any] | None = None,
) -> tuple[bool, dict[str, Any]]:
    """检查 agent 是否可调用 tool。

    Args:
        agent_name: agent 名
        tool_name: 工具名
        enforce: 显式覆盖模式 (True=硬阻断, False=warn-only)。None 时读
            HARNESS_POLICY_ENFORCE 环境变量(默认 warn-only)。
            base.py 主路径默认 enforce=True (1 周观察期已过)。
        db: 可选 AsyncSession (A6 2026-05-14). 当 decision=REQUIRE_APPROVAL
            且 db + org_id 都提供时, 自动调 agent_approval_service.request_approval
            创建审批工单, decision_dict 含 approval_id; enforce 模式下仍 deny,
            warn-only 模式下放行但保留审计记录.
        org_id: 见 db.
        requested_by: 审批工单的 requested_by 字段 (通常是 user_id).
        action_payload: 审批工单 payload (默认含 agent_name + tool_name).

    返回 (allowed, decision_dict)。warn-only 模式下 allowed 始终为 True。
    """
    if enforce is None:
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
        _record_to_trace(decision_dict)
        return True, decision_dict

    decision_dict.update({
        "decision": result.decision.value,
        "reason": result.reason,
    })

    if result.decision == PolicyDecision.ALLOW:
        # ALLOW 不写 trace _policy_info (避免噪声)
        return True, decision_dict

    if result.decision == PolicyDecision.REQUIRE_APPROVAL:
        # A6 (2026-05-14): 自动创建审批工单 (db + org_id 都到位时)
        approval_id: str | None = None
        approval_status: str | None = None
        if db is not None and org_id:
            try:
                from src.services.agent_approval_service import AgentApprovalService

                svc = AgentApprovalService(db)
                payload = dict(action_payload or {})
                payload.setdefault("agent_name", agent_name)
                payload.setdefault("tool_name", tool_name)
                payload.setdefault("policy_reason", result.reason)
                decision = await svc.request_approval(
                    org_id=org_id,
                    action_type=f"mcp_tool:{tool_name}",
                    risk_level="high",  # REQUIRE_APPROVAL 默认归类高风险
                    requested_by=requested_by,
                    route_key=None,
                    payload=payload,
                )
                if decision.allowed:
                    approval_id = decision.approval_id
                    approval_status = decision.status
                    decision_dict["approval_id"] = approval_id
                    decision_dict["approval_status"] = approval_status
                    logger.warning(
                        f"[Harness][policy] REQUIRE_APPROVAL agent={agent_name} tool={tool_name} "
                        f"→ 已创建审批工单 {approval_id} (status={approval_status})"
                    )
                else:
                    logger.error(
                        f"[Harness][policy] REQUIRE_APPROVAL agent={agent_name} tool={tool_name} "
                        f"创建审批工单失败: {decision.reason_code} {decision.human_message}"
                    )
                    decision_dict["approval_create_failed"] = decision.reason_code
            except Exception as exc:
                logger.error(
                    f"[Harness][policy] REQUIRE_APPROVAL agent={agent_name} tool={tool_name} "
                    f"审批服务异常 (不阻断, 主路径继续): {exc}"
                )
                decision_dict["approval_error"] = str(exc)
        else:
            logger.warning(
                f"[Harness][policy] REQUIRE_APPROVAL agent={agent_name} tool={tool_name} "
                f"reason={result.reason} (db/org_id 未注入, 跳过工单创建)"
            )

        # enforce 模式 + 已创建 pending 审批 → 阻断 (等人工 approve)
        if enforce and approval_status == "pending":
            decision_dict["enforced"] = True
            _record_to_trace(decision_dict)
            return False, decision_dict
        # warn-only 模式或工单创建失败 → 放行 + 审计
        decision_dict["enforced"] = False
        _record_to_trace(decision_dict)
        return True, decision_dict

    # DENY 分支
    if enforce:
        logger.warning(
            f"[Harness][policy] DENY agent={agent_name} tool={tool_name} "
            f"reason={result.reason} ENFORCED"
        )
        decision_dict["enforced"] = True
        _record_to_trace(decision_dict)
        return False, decision_dict

    # warn-only
    logger.warning(
        f"[Harness][policy] DENY agent={agent_name} tool={tool_name} "
        f"reason={result.reason} (warn-only, 实际放行；切换 enforce 设 HARNESS_POLICY_ENFORCE=true)"
    )
    decision_dict["enforced"] = False
    _record_to_trace(decision_dict)
    return True, decision_dict


def _record_to_trace(decision_dict: dict[str, Any]) -> None:
    """A7: 把非 ALLOW 决策写入当前 trace 的 _policy_info, 供 admin 审计。"""
    try:
        from src.harness.trace_context import current_trace

        trace = current_trace()
        if trace is not None:
            trace.record_policy_decision(decision_dict)
    except Exception as exc:
        # trace 写入失败不影响主路径
        logger.debug(f"[Harness][policy] trace 写入跳过: {exc}")
