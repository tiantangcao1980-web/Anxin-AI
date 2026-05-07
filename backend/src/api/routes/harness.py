"""
Harness Engineering 监控面板 API

提供 token 消耗、费用统计、工具调用、权限审计等数据接口。
仅管理员可访问。
"""


from typing import Any

from fastapi import APIRouter, Depends, Query

from src.core.deps import get_admin_user

router = APIRouter(prefix="/harness", tags=["harness"])
ResponsePayload = dict[str, Any]


@router.get("/stats")
async def get_harness_stats(user: Any = Depends(get_admin_user)) -> ResponsePayload:
    """获取 Harness 全局统计概览"""
    result: ResponsePayload = {}

    try:
        from src.harness.cost_tracker import cost_tracker
        result["cost"] = cost_tracker.get_stats()
    except Exception as e:
        result["cost"] = {"error": str(e)}

    try:
        from src.harness.tool_registry import tool_registry
        result["tools"] = tool_registry.get_summary()
    except Exception as e:
        result["tools"] = {"error": str(e)}

    try:
        from src.harness.policy_engine import policy_engine
        result["policy"] = policy_engine.get_stats()
    except Exception as e:
        result["policy"] = {"error": str(e)}

    try:
        from src.harness.task_engine import task_engine
        result["tasks"] = task_engine.get_stats()
    except Exception as e:
        result["tasks"] = {"error": str(e)}

    return {"status": "ok", "data": result}


@router.get("/cost")
async def get_cost_stats(user: Any = Depends(get_admin_user)) -> ResponsePayload:
    """获取费用统计详情"""
    from src.harness.cost_tracker import cost_tracker
    return {"status": "ok", "data": cost_tracker.get_stats()}


@router.get("/cost/conversation/{conversation_id}")
async def get_conversation_cost(
    conversation_id: str,
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """获取单个会话的费用明细"""
    from src.harness.cost_tracker import cost_tracker
    return {"status": "ok", "data": cost_tracker.get_conversation_cost(conversation_id)}


@router.get("/tools")
async def list_tools(
    risk_level: str | None = Query(None, description="过滤风险等级"),
    tag: str | None = Query(None, description="过滤标签"),
    agent: str | None = Query(None, description="过滤可用 Agent"),
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """列出已注册的工具"""
    from src.harness.tool_registry import RiskLevel, tool_registry

    risk = RiskLevel(risk_level) if risk_level else None
    tools = tool_registry.list_tools(risk_level=risk, tag=tag, agent_name=agent)
    return {
        "status": "ok",
        "data": [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "risk_level": t.risk_level.value,
                "requires_approval": t.requires_approval,
                "allowed_agents": list(t.allowed_agents) if t.allowed_agents is not None else None,
                "tags": t.tags,
            }
            for t in tools
        ],
    }


@router.get("/tools/stats")
async def get_tool_stats(
    tool_name: str | None = Query(None),
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """获取工具调用统计"""
    from src.harness.tool_registry import tool_registry
    return {"status": "ok", "data": tool_registry.get_tool_stats(tool_name)}


@router.get("/policy/check")
async def check_policy(
    agent: str = Query(..., description="Agent 名称"),
    tool: str = Query(..., description="工具名称"),
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """检查 Agent 是否有权限调用工具"""
    from src.harness.policy_engine import policy_engine
    result = policy_engine.check_tool_access(agent, tool)
    return {
        "status": "ok",
        "data": {
            "decision": result.decision.value,
            "reason": result.reason,
            "agent": result.agent_name,
            "tool": result.tool_name,
            "required_approver": result.required_approver_role,
        },
    }


@router.get("/policy/agent/{agent_name}/tools")
async def get_agent_tools(
    agent_name: str,
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """获取 Agent 可用的所有工具"""
    from src.harness.policy_engine import policy_engine
    tools = policy_engine.get_agent_available_tools(agent_name)
    return {"status": "ok", "data": {"agent": agent_name, "available_tools": tools}}


@router.get("/policy/audit")
async def get_policy_audit(
    limit: int = Query(50, le=200),
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """获取权限审计日志"""
    from src.harness.policy_engine import policy_engine
    logs = policy_engine._audit_log[-limit:]
    logs.reverse()
    return {"status": "ok", "data": logs}


# ===== 任务引擎 =====

@router.get("/tasks")
async def get_task_stats(user: Any = Depends(get_admin_user)) -> ResponsePayload:
    """获取任务引擎统计"""
    from src.harness.task_engine import task_engine
    return {"status": "ok", "data": task_engine.get_stats()}


@router.get("/tasks/user/{user_id}")
async def get_user_tasks(
    user_id: str,
    limit: int = Query(20, le=100),
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """获取用户任务列表"""
    from src.harness.task_engine import task_engine
    return {"status": "ok", "data": task_engine.get_user_tasks(user_id, limit)}


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """获取任务详情"""
    from src.harness.task_engine import task_engine
    task = task_engine.get_task(task_id)
    if not task:
        return {"status": "error", "message": "任务不存在"}
    return {
        "status": "ok",
        "data": {
            "task_id": task.task_id,
            "description": task.description,
            "state": task.state.value,
            "priority": task.priority.name,
            "agent": task.agent_name,
            "route": task.route,
            "elapsed_seconds": task.elapsed_seconds,
            "retry_count": task.retry_count,
            "error_history": task.error_history,
            "state_history": task.state_history,
            "created_at": task.created_at,
        },
    }


# ===== 多端能力协商 =====

@router.get("/capability/negotiate")
async def negotiate_capability(
    platform: str = Query("web", description="平台类型: web/desktop/mobile/mini_program"),
    mode: str = Query("cloud", description="运行模式: cloud/hybrid/top_secret"),
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """协商当前环境的可用能力"""
    from src.harness.capability_negotiator import (
        AppMode,
        PlatformType,
        capability_negotiator,
    )
    try:
        result = capability_negotiator.negotiate(
            platform=PlatformType(platform),
            mode=AppMode(mode),
        )
        return {
            "status": "ok",
            "data": {
                "platform": result.platform.value,
                "mode": result.mode.value,
                "available_features": result.available_features,
                "unavailable_features": result.unavailable_features,
                "available_tasks": result.available_tasks,
                "warnings": result.warnings,
                "recommendations": result.recommendations,
            },
        }
    except ValueError as e:
        return {"status": "error", "message": f"无效参数: {e}"}


@router.get("/capability/degradation")
async def get_degradation_notice(
    from_mode: str = Query(..., description="当前模式"),
    to_mode: str = Query(..., description="目标模式"),
    user: Any = Depends(get_admin_user),
) -> ResponsePayload:
    """获取模式切换降级通知"""
    from src.harness.capability_negotiator import AppMode, capability_negotiator
    try:
        notice = capability_negotiator.get_degradation_notice(
            from_mode=AppMode(from_mode),
            to_mode=AppMode(to_mode),
        )
        return {"status": "ok", "data": notice}
    except ValueError as e:
        return {"status": "error", "message": f"无效参数: {e}"}
