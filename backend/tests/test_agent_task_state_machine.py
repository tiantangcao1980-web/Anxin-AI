# -*- coding: utf-8 -*-
"""
状态机单元测试 —— 不依赖数据库，纯内存对象。
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.services.task_orchestrator.events import TaskEvent, TaskEventType
from src.services.task_orchestrator.models import Task, TaskStatus
from src.services.task_orchestrator.state_machine import (
    InvalidTransitionError,
    TaskStateMachine,
)


def _make_task(status: TaskStatus = TaskStatus.QUEUED) -> Task:
    """构造一个未持久化的 Task 实例（仅供状态机测试）。"""
    t = Task()
    t.id = str(uuid4())
    t.user_id = str(uuid4())
    t.agent_persona = "free_legal"
    t.status = status
    t.priority = 100
    t.payload = {}
    t.result = None
    t.error = None
    t.parent_task_id = None
    t.sandbox_id = None
    t.started_at = None
    t.finished_at = None
    return t


# ---------------------------------------------------------------------------
# 合法转移
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (TaskStatus.QUEUED, TaskStatus.PROVISIONING),
        (TaskStatus.QUEUED, TaskStatus.FAILED),
        (TaskStatus.QUEUED, TaskStatus.CANCELLED),
        (TaskStatus.PROVISIONING, TaskStatus.RUNNING),
        (TaskStatus.PROVISIONING, TaskStatus.FAILED),
        (TaskStatus.PROVISIONING, TaskStatus.CANCELLED),
        (TaskStatus.RUNNING, TaskStatus.REPORTING),
        (TaskStatus.RUNNING, TaskStatus.NEEDS_APPROVAL),
        (TaskStatus.RUNNING, TaskStatus.FAILED),
        (TaskStatus.RUNNING, TaskStatus.CANCELLED),
        (TaskStatus.REPORTING, TaskStatus.DONE),
        (TaskStatus.REPORTING, TaskStatus.FAILED),
        (TaskStatus.NEEDS_APPROVAL, TaskStatus.RUNNING),
        (TaskStatus.NEEDS_APPROVAL, TaskStatus.CANCELLED),
    ],
)
def test_legal_transitions(from_state: TaskStatus, to_state: TaskStatus) -> None:
    """每条合法转移都能成功 transition。"""
    sm = TaskStateMachine()
    task = _make_task(from_state)
    sm.transition(task, to_state)
    assert task.status == to_state


# ---------------------------------------------------------------------------
# 非法转移
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "from_state,to_state",
    [
        (TaskStatus.QUEUED, TaskStatus.RUNNING),  # 必须经过 PROVISIONING
        (TaskStatus.QUEUED, TaskStatus.DONE),
        (TaskStatus.RUNNING, TaskStatus.QUEUED),  # 不能回退
        (TaskStatus.DONE, TaskStatus.RUNNING),  # 终态不能再变
        (TaskStatus.DONE, TaskStatus.FAILED),
        (TaskStatus.FAILED, TaskStatus.RUNNING),
        (TaskStatus.CANCELLED, TaskStatus.RUNNING),
        (TaskStatus.CANCELLED, TaskStatus.DONE),
        (TaskStatus.NEEDS_APPROVAL, TaskStatus.DONE),  # 必须先回 RUNNING
    ],
)
def test_illegal_transitions_blocked(
    from_state: TaskStatus, to_state: TaskStatus
) -> None:
    """非法转移必须抛 InvalidTransitionError（继承 ValueError）。"""
    sm = TaskStateMachine()
    task = _make_task(from_state)
    with pytest.raises(ValueError) as exc_info:
        sm.transition(task, to_state)
    assert isinstance(exc_info.value, InvalidTransitionError)
    # 状态不应改变
    assert task.status == from_state


def test_can_transition_classmethod() -> None:
    """can_transition 类方法正确判定。"""
    assert TaskStateMachine.can_transition(TaskStatus.QUEUED, TaskStatus.PROVISIONING)
    assert not TaskStateMachine.can_transition(TaskStatus.QUEUED, TaskStatus.RUNNING)
    assert not TaskStateMachine.can_transition(TaskStatus.DONE, TaskStatus.RUNNING)


# ---------------------------------------------------------------------------
# 时间戳
# ---------------------------------------------------------------------------


def test_started_at_set_on_running() -> None:
    """进入 RUNNING 时 started_at 自动赋值。"""
    sm = TaskStateMachine()
    task = _make_task(TaskStatus.QUEUED)
    sm.transition(task, TaskStatus.PROVISIONING)
    assert task.started_at is None
    sm.transition(task, TaskStatus.RUNNING)
    assert task.started_at is not None
    assert task.started_at.tzinfo is not None


def test_finished_at_set_on_terminal() -> None:
    """进入 DONE / FAILED / CANCELLED 时 finished_at 自动赋值。"""
    for terminal in (TaskStatus.DONE, TaskStatus.FAILED, TaskStatus.CANCELLED):
        sm = TaskStateMachine()
        task = _make_task(TaskStatus.QUEUED)
        sm.transition(task, TaskStatus.PROVISIONING)
        sm.transition(task, TaskStatus.RUNNING)
        if terminal == TaskStatus.DONE:
            sm.transition(task, TaskStatus.REPORTING)
        sm.transition(task, terminal)
        assert task.finished_at is not None, f"{terminal} 应设 finished_at"


def test_started_at_not_overwritten_when_re_entering_running() -> None:
    """NEEDS_APPROVAL → RUNNING 时不应覆盖 started_at。"""
    sm = TaskStateMachine()
    task = _make_task(TaskStatus.QUEUED)
    sm.transition(task, TaskStatus.PROVISIONING)
    sm.transition(task, TaskStatus.RUNNING)
    first_started = task.started_at
    sm.transition(task, TaskStatus.NEEDS_APPROVAL)
    sm.transition(task, TaskStatus.RUNNING)
    assert task.started_at == first_started


# ---------------------------------------------------------------------------
# 事件 emit
# ---------------------------------------------------------------------------


def test_emitter_called_on_transition() -> None:
    """每次合法 transition 都触发 emitter。"""
    captured: list[TaskEvent] = []

    def collect(ev: TaskEvent) -> None:
        captured.append(ev)

    sm = TaskStateMachine(emitter=collect)
    task = _make_task(TaskStatus.QUEUED)
    sm.transition(task, TaskStatus.PROVISIONING)
    sm.transition(task, TaskStatus.RUNNING)

    assert len(captured) == 2
    assert captured[0].event_type == TaskEventType.PROVISIONING
    assert captured[1].event_type == TaskEventType.STARTED
    # payload 含 from / to
    assert captured[1].payload["from"] == TaskStatus.PROVISIONING.value
    assert captured[1].payload["to"] == TaskStatus.RUNNING.value


def test_context_written_to_task() -> None:
    """transition 时通过 context 写入 result / error。"""
    sm = TaskStateMachine()
    task = _make_task(TaskStatus.QUEUED)
    sm.transition(task, TaskStatus.PROVISIONING)
    sm.transition(task, TaskStatus.RUNNING)
    sm.transition(task, TaskStatus.REPORTING)
    sm.transition(task, TaskStatus.DONE, result={"answer": "42"})
    assert task.result == {"answer": "42"}

    task2 = _make_task(TaskStatus.QUEUED)
    sm.transition(task2, TaskStatus.FAILED, error={"code": "X", "message": "boom"})
    assert task2.error == {"code": "X", "message": "boom"}
