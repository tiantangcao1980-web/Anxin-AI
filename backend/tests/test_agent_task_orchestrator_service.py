"""
TaskOrchestratorService 集成测试

涉及真实 SQLAlchemy AsyncSession（SQLite in-memory），
但 Redis / Celery 都被替换成 no-op，避免外部依赖。
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# 触发 ORM 注册到 Base.metadata（务必在 conftest setup_test_db 之前 import）
from src.services.task_orchestrator.models import Task, TaskStatus  # noqa: F401
from src.services.task_orchestrator.service import TaskOrchestratorService
from src.services.task_orchestrator.state_machine import (
    InvalidTransitionError,
    TaskStateMachine,
)

# ---------------------------------------------------------------------------
# 全局 mock：屏蔽 Redis Streams + Celery，让所有测试都本地跑通
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stub_redis_publish(monkeypatch):
    """publish_event / replay_events / consume_events 全部 no-op。"""
    from src.services.task_orchestrator import events as events_mod
    from src.services.task_orchestrator import service as service_mod

    async def _noop_publish(event, *args, **kwargs):
        return ""

    async def _noop_replay(*args, **kwargs):
        return []

    monkeypatch.setattr(events_mod, "publish_event", _noop_publish)
    monkeypatch.setattr(service_mod, "publish_event", _noop_publish)
    monkeypatch.setattr(events_mod, "replay_events", _noop_replay)


@pytest.fixture(autouse=True)
def _disable_celery_enqueue(monkeypatch):
    """避免 Celery / Redis 真实连接：service 默认 enqueue 走 worker.run_agent_task.delay。

    我们 patch 整个 enqueue 方法，让它直接返回。
    """

    async def _noop_enqueue(self, task):
        return None

    monkeypatch.setattr(TaskOrchestratorService, "enqueue", _noop_enqueue)


# ---------------------------------------------------------------------------
# helper
# ---------------------------------------------------------------------------


def _make_service(db_session: AsyncSession) -> TaskOrchestratorService:
    """构造 service：使用不带 emitter 的状态机，避免触发 asyncio.create_task。"""
    return TaskOrchestratorService(
        session=db_session,
        state_machine=TaskStateMachine(emitter=None),
    )


# ---------------------------------------------------------------------------
# create / list / get
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_task_persists(db_session: AsyncSession, test_user) -> None:
    """create_task 应落库并初始状态 QUEUED。"""
    service = _make_service(db_session)
    task = await service.create_task(
        user_id=str(test_user.id),
        agent_persona="free_legal",
        payload={"q": "你好"},
        priority=50,
    )
    assert task.id is not None
    assert task.status == TaskStatus.QUEUED
    assert task.priority == 50
    assert task.payload == {"q": "你好"}
    # round-trip 查询
    fetched = await service.get_task(task.id)
    assert fetched is not None
    assert fetched.id == task.id


@pytest.mark.asyncio
async def test_list_tasks_filtered_by_status(db_session: AsyncSession, test_user) -> None:
    service = _make_service(db_session)
    t1 = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    t2 = await service.create_task(user_id=str(test_user.id), agent_persona="pro_legal")
    # 把 t2 推到 RUNNING
    await service.start(t2.id)

    queued = await service.list_tasks_for_user(str(test_user.id), status=TaskStatus.QUEUED)
    running = await service.list_tasks_for_user(str(test_user.id), status=TaskStatus.RUNNING)
    assert any(t.id == t1.id for t in queued)
    assert any(t.id == t2.id for t in running)


# ---------------------------------------------------------------------------
# 完整生命周期
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_full_lifecycle(db_session: AsyncSession, test_user) -> None:
    """queued → running → reporting → done 全流程。"""
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.start(task.id)
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.RUNNING
    assert refetch.started_at is not None

    await service.progress(task.id, {"progress": 0.5, "message": "halfway"})
    # progress 不改 status
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.RUNNING

    await service.complete(task.id, {"answer": "42"})
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.DONE
    assert refetch.result == {"answer": "42"}
    assert refetch.finished_at is not None


# ---------------------------------------------------------------------------
# 审批
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_request_approval_pauses(db_session: AsyncSession, test_user) -> None:
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.start(task.id)
    await service.request_approval(task.id, reason="风险阈值超限")
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.NEEDS_APPROVAL


@pytest.mark.asyncio
async def test_approve_resumes_running(db_session: AsyncSession, test_user) -> None:
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.start(task.id)
    await service.request_approval(task.id, reason="check")
    await service.approve(task.id, approver_id=str(test_user.id))
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.RUNNING


@pytest.mark.asyncio
async def test_reject_cancels(db_session: AsyncSession, test_user) -> None:
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.start(task.id)
    await service.request_approval(task.id, reason="check")
    await service.reject(task.id, approver_id=str(test_user.id), reason="不通过")
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.CANCELLED
    assert refetch.error is not None
    assert refetch.error.get("code") == "APPROVAL_REJECTED"


# ---------------------------------------------------------------------------
# 取消
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_from_queued(db_session: AsyncSession, test_user) -> None:
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.cancel(task.id)
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_from_running(db_session: AsyncSession, test_user) -> None:
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.start(task.id)
    await service.cancel(task.id)
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_from_terminal_blocked(db_session: AsyncSession, test_user) -> None:
    """完成后再取消应抛 InvalidTransitionError。"""
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.start(task.id)
    await service.complete(task.id, {"ok": True})
    with pytest.raises(InvalidTransitionError):
        await service.cancel(task.id)


@pytest.mark.asyncio
async def test_fail_writes_error(db_session: AsyncSession, test_user) -> None:
    service = _make_service(db_session)
    task = await service.create_task(user_id=str(test_user.id), agent_persona="free_legal")
    await service.start(task.id)
    await service.fail(task.id, {"code": "TIMEOUT", "message": "超时"})
    refetch = await service.get_task(task.id)
    assert refetch.status == TaskStatus.FAILED
    assert refetch.error == {"code": "TIMEOUT", "message": "超时"}
