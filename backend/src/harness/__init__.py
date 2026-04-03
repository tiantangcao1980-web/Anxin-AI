# -*- coding: utf-8 -*-
"""
Harness Engineering 核心层

将 LLM 能力封装在确定性工程框架中：
- trace_context: 全链路请求追踪
- cost_tracker: Token 用量与费用统计
- output_validator: 输出质量校验引擎
- tool_registry: 工具注册与治理中心
- policy_engine: Agent 权限与审批引擎
- context_engine: 统一上下文装配
"""

from src.harness.trace_context import TraceContext, current_trace, start_trace
from src.harness.cost_tracker import cost_tracker, CostRecord
from src.harness.output_validator import output_validator
from src.harness.tool_registry import tool_registry
from src.harness.policy_engine import policy_engine
from src.harness.context_engine import context_engine
from src.harness.task_engine import task_engine, TaskState, TaskPriority
from src.harness.capability_negotiator import capability_negotiator

__all__ = [
    "TraceContext",
    "current_trace",
    "start_trace",
    "cost_tracker",
    "CostRecord",
    "output_validator",
    "tool_registry",
    "policy_engine",
    "context_engine",
    "task_engine",
    "TaskState",
    "TaskPriority",
    "capability_negotiator",
]
