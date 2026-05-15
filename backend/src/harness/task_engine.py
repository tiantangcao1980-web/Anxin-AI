"""
任务状态机 + 优先级队列

为每个 Agent 任务定义显式状态流转，支持：
1. 状态机：pending → running → validating → completed / failed / retry
2. 优先级队列：高风险法律任务优先执行
3. 中间产物持久化：跨步骤保留 artifact
4. 超时恢复 + 优雅降级
5. 任务合同：目标/成功标准/工具白名单/输出模板
"""

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from loguru import logger


class TaskState(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    AWAITING_APPROVAL = "awaiting_approval"


class TaskPriority(int, Enum):
    """任务优先级（数值越小越优先）"""

    CRITICAL = 0  # 紧急法律事务（诉讼截止日期等）
    HIGH = 1  # 合同审阅、正式法律意见
    NORMAL = 2  # 一般法律咨询
    LOW = 3  # 知识检索、信息查询
    BACKGROUND = 4  # 后台分析、统计报表


# 路由→优先级映射
ROUTE_PRIORITY_MAP = {
    "contract_review": TaskPriority.HIGH,
    "document_drafting": TaskPriority.HIGH,
    "due_diligence": TaskPriority.HIGH,
    "specific_agent": TaskPriority.NORMAL,
    "rag": TaskPriority.LOW,
    "general": TaskPriority.NORMAL,
}

# 合法的状态转换
VALID_TRANSITIONS = {
    TaskState.PENDING: {TaskState.RUNNING, TaskState.CANCELLED},
    TaskState.RUNNING: {
        TaskState.VALIDATING,
        TaskState.COMPLETED,
        TaskState.FAILED,
        TaskState.TIMEOUT,
        TaskState.CANCELLED,
    },
    TaskState.VALIDATING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.RETRY},
    TaskState.RETRY: {TaskState.RUNNING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.FAILED: {TaskState.RETRY, TaskState.CANCELLED},
    TaskState.TIMEOUT: {TaskState.RETRY, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.COMPLETED: set(),  # 终态
    TaskState.CANCELLED: set(),  # 终态
    TaskState.AWAITING_APPROVAL: {TaskState.RUNNING, TaskState.CANCELLED},
}


@dataclass
class TaskContract:
    """
    任务合同 — 先有合同，再让 Agent 开工

    定义任务的目标、边界、成功标准和约束。
    """

    goal: str  # 任务目标
    success_criteria: list[str] = field(default_factory=list)  # 成功标准
    forbidden_actions: list[str] = field(default_factory=list)  # 禁止事项
    required_tools: list[str] = field(default_factory=list)  # 必须使用的工具
    output_format: str | None = None  # 期望输出格式
    max_retries: int = 1  # 最大重试次数
    timeout_seconds: int = 120  # 超时时间
    requires_approval: bool = False  # 是否需要人工审批


@dataclass
class TaskRecord:
    """任务记录"""

    task_id: str
    description: str
    state: TaskState = TaskState.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    contract: TaskContract | None = None
    agent_name: str | None = None
    route: str | None = None
    user_id: str | None = None
    conversation_id: str | None = None
    trace_id: str | None = None

    # 时间线
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    # 中间产物
    artifacts: dict[str, Any] = field(default_factory=dict)

    # 执行信息
    retry_count: int = 0
    error_history: list[str] = field(default_factory=list)
    state_history: list[dict[str, Any]] = field(default_factory=list)

    # 结果
    result: Any | None = None
    validation_result: dict[str, Any] | None = None

    @property
    def elapsed_seconds(self) -> float:
        end = self.completed_at or time.time()
        start = self.started_at or self.created_at
        return round(end - start, 2)

    @property
    def is_terminal(self) -> bool:
        return self.state in (TaskState.COMPLETED, TaskState.CANCELLED)


class TaskEngine:
    """
    任务引擎

    管理任务的完整生命周期，包括状态流转、优先级调度和中间产物持久化。
    """

    def __init__(self, max_tasks: int = 5000):
        self._tasks: dict[str, TaskRecord] = {}
        self._max_tasks = max_tasks
        # 统计
        self._state_counts: dict[str, int] = defaultdict(int)
        self._completed_count: int = 0
        self._failed_count: int = 0

    def create_task(
        self,
        description: str,
        route: str | None = None,
        agent_name: str | None = None,
        user_id: str | None = None,
        conversation_id: str | None = None,
        trace_id: str | None = None,
        contract: TaskContract | None = None,
        priority: TaskPriority | None = None,
    ) -> TaskRecord:
        """创建新任务"""
        task_id = uuid.uuid4().hex[:12]

        # 自动推断优先级
        if priority is None:
            priority = ROUTE_PRIORITY_MAP.get(route or "", TaskPriority.NORMAL)

        task = TaskRecord(
            task_id=task_id,
            description=description[:200],
            priority=priority,
            route=route,
            agent_name=agent_name,
            user_id=user_id,
            conversation_id=conversation_id,
            trace_id=trace_id,
            contract=contract,
        )

        self._tasks[task_id] = task
        self._state_counts["pending"] += 1

        # 清理过期任务
        if len(self._tasks) > self._max_tasks:
            self._cleanup_old_tasks()

        logger.debug(f"[TaskEngine] 创建任务 {task_id} | route={route} | priority={priority.name}")
        return task

    def transition(
        self,
        task_id: str,
        new_state: TaskState,
        error_msg: str | None = None,
        result: Any | None = None,
        validation_result: dict[str, Any] | None = None,
    ) -> bool:
        """
        执行状态转换

        Returns:
            True 如果转换成功，False 如果转换非法
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.warning(f"[TaskEngine] 任务 {task_id} 不存在")
            return False

        old_state = task.state
        valid_next = VALID_TRANSITIONS.get(old_state, set())

        if new_state not in valid_next:
            logger.warning(
                f"[TaskEngine] 非法状态转换: {task_id} "
                f"{old_state.value} → {new_state.value} "
                f"(允许: {[s.value for s in valid_next]})"
            )
            return False

        # 执行转换
        task.state = new_state
        task.state_history.append(
            {
                "from": old_state.value,
                "to": new_state.value,
                "at": time.time(),
                "error": error_msg,
            }
        )

        # 更新计数
        self._state_counts[old_state.value] = max(0, self._state_counts.get(old_state.value, 0) - 1)
        self._state_counts[new_state.value] = self._state_counts.get(new_state.value, 0) + 1

        # 状态特定逻辑
        if new_state == TaskState.RUNNING:
            task.started_at = time.time()
        elif new_state == TaskState.COMPLETED:
            task.completed_at = time.time()
            task.result = result
            self._completed_count += 1
        elif new_state == TaskState.FAILED:
            task.completed_at = time.time()
            if error_msg:
                task.error_history.append(error_msg)
            self._failed_count += 1
        elif new_state == TaskState.RETRY:
            task.retry_count += 1
            if error_msg:
                task.error_history.append(error_msg)
        elif new_state == TaskState.VALIDATING:
            task.validation_result = validation_result

        return True

    def can_retry(self, task_id: str) -> bool:
        """检查任务是否可以重试"""
        task = self._tasks.get(task_id)
        if not task or not task.contract:
            return task.retry_count < 1 if task else False
        return task.retry_count < task.contract.max_retries

    def save_artifact(self, task_id: str, key: str, value: Any) -> None:
        """保存中间产物"""
        task = self._tasks.get(task_id)
        if task:
            task.artifacts[key] = value

    def get_artifact(self, task_id: str, key: str) -> Any | None:
        """获取中间产物"""
        task = self._tasks.get(task_id)
        return task.artifacts.get(key) if task else None

    def get_task(self, task_id: str) -> TaskRecord | None:
        """获取任务"""
        return self._tasks.get(task_id)

    def get_pending_by_priority(self) -> list[TaskRecord]:
        """按优先级获取待执行任务"""
        pending = [t for t in self._tasks.values() if t.state == TaskState.PENDING]
        return sorted(pending, key=lambda t: (t.priority.value, t.created_at))

    def get_stats(self) -> dict[str, Any]:
        """获取引擎统计"""
        active = [t for t in self._tasks.values() if not t.is_terminal]
        return {
            "total_tasks": len(self._tasks),
            "active_tasks": len(active),
            "completed": self._completed_count,
            "failed": self._failed_count,
            "success_rate": round(
                self._completed_count / max(1, self._completed_count + self._failed_count), 3
            ),
            "by_state": dict(self._state_counts),
            "by_priority": dict(
                sorted(defaultdict(int, {t.priority.name: 1 for t in active}).items())
            ),
            "avg_elapsed_seconds": round(
                sum(t.elapsed_seconds for t in self._tasks.values() if t.completed_at)
                / max(1, sum(1 for t in self._tasks.values() if t.completed_at)),
                2,
            ),
        }

    def get_user_tasks(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        """获取用户的任务列表"""
        tasks = [t for t in self._tasks.values() if t.user_id == user_id]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [
            {
                "task_id": t.task_id,
                "description": t.description,
                "state": t.state.value,
                "priority": t.priority.name,
                "agent": t.agent_name,
                "elapsed_seconds": t.elapsed_seconds,
                "retry_count": t.retry_count,
                "created_at": t.created_at,
            }
            for t in tasks[:limit]
        ]

    def _cleanup_old_tasks(self) -> None:
        """清理终态的旧任务"""
        terminal = [(tid, t) for tid, t in self._tasks.items() if t.is_terminal]
        terminal.sort(key=lambda x: x[1].created_at)
        # 删除最旧的一半终态任务
        to_remove = len(terminal) // 2
        for tid, _ in terminal[:to_remove]:
            del self._tasks[tid]
        if to_remove > 0:
            logger.info(f"[TaskEngine] 清理 {to_remove} 个旧任务")


# 全局单例
task_engine = TaskEngine()
