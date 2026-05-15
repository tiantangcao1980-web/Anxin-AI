"""
异步任务编排服务模块

参考 Codex Cloud / Claude Dispatch 模式：用户在 App 派发任务，
agent 在远端 sandbox 中执行，完成后回报。

主要导出：
- ``Task``：异步任务 ORM 模型（表 ``agent_tasks``）
- ``TaskStatus``：任务状态枚举
- ``TaskStateMachine``：状态机（合法转移 + 转移钩子）
- ``TaskOrchestratorService``：服务门面（创建/入队/进度/完成/失败/审批）
- ``TaskEvent``：状态/进度事件（供 SSE / WebSocket 推送）

实现阶段：P2（详见 ``README.md``）。
"""

from src.services.task_orchestrator.events import TaskEvent, TaskEventType
from src.services.task_orchestrator.models import Task, TaskStatus
from src.services.task_orchestrator.service import TaskOrchestratorService
from src.services.task_orchestrator.state_machine import (
    InvalidTransitionError,
    TaskStateMachine,
)

__all__ = [
    "Task",
    "TaskStatus",
    "TaskStateMachine",
    "InvalidTransitionError",
    "TaskOrchestratorService",
    "TaskEvent",
    "TaskEventType",
]
