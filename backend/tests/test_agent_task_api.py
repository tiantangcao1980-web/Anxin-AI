# -*- coding: utf-8 -*-
"""
agent_tasks 路由 API 测试

使用 conftest 中的 ``auth_client`` (带 Bearer token) 走 ASGITransport，
Redis / Celery 都被 monkeypatch 掉以避免真实外部依赖。
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient

# 触发 ORM 表注册
from src.services.task_orchestrator.models import Task, TaskStatus  # noqa: F401
from src.services.task_orchestrator.service import TaskOrchestratorService


# ---------------------------------------------------------------------------
# 全局 mock
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _stub_redis_and_celery(monkeypatch):
    from src.services.task_orchestrator import events as events_mod
    from src.services.task_orchestrator import service as service_mod

    async def _noop_publish(event, *args, **kwargs):
        return ""

    async def _noop_replay(*args, **kwargs):
        return []

    monkeypatch.setattr(events_mod, "publish_event", _noop_publish)
    monkeypatch.setattr(service_mod, "publish_event", _noop_publish)
    monkeypatch.setattr(events_mod, "replay_events", _noop_replay)

    async def _noop_enqueue(self, task):
        return None

    monkeypatch.setattr(TaskOrchestratorService, "enqueue", _noop_enqueue)


# ---------------------------------------------------------------------------
# helper：直接经 service 推进任务到指定状态（绕过 worker）
# ---------------------------------------------------------------------------


async def _create_task_via_api(client: AsyncClient, persona: str = "free_legal") -> dict:
    resp = await client.post(
        "/api/v1/agent-tasks",
        json={"agent_persona": persona, "payload": {"q": "hi"}},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# 用例
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_task_endpoint(auth_client: AsyncClient) -> None:
    body = await _create_task_via_api(auth_client)
    assert body["status"] == TaskStatus.QUEUED.value
    assert body["agent_persona"] == "free_legal"
    assert "id" in body


@pytest.mark.asyncio
async def test_get_task_detail_endpoint(auth_client: AsyncClient) -> None:
    created = await _create_task_via_api(auth_client)
    resp = await auth_client.get(f"/api/v1/agent-tasks/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


@pytest.mark.asyncio
async def test_list_tasks_for_user(auth_client: AsyncClient) -> None:
    await _create_task_via_api(auth_client, persona="free_legal")
    await _create_task_via_api(auth_client, persona="pro_legal")
    resp = await auth_client.get("/api/v1/agent-tasks?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["limit"] == 10
    assert data["offset"] == 0
    assert len(data["items"]) >= 2


@pytest.mark.asyncio
async def test_list_tasks_status_filter(auth_client: AsyncClient) -> None:
    await _create_task_via_api(auth_client)
    resp = await auth_client.get(
        f"/api/v1/agent-tasks?status={TaskStatus.QUEUED.value}"
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["status"] == TaskStatus.QUEUED.value for item in items)


@pytest.mark.asyncio
async def test_cancel_endpoint(auth_client: AsyncClient) -> None:
    created = await _create_task_via_api(auth_client)
    resp = await auth_client.post(f"/api/v1/agent-tasks/{created['id']}/cancel")
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == TaskStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_cancel_already_terminal_returns_409(
    auth_client: AsyncClient,
) -> None:
    created = await _create_task_via_api(auth_client)
    # 第一次取消成功
    r1 = await auth_client.post(f"/api/v1/agent-tasks/{created['id']}/cancel")
    assert r1.status_code == 200
    # 第二次应 409 InvalidTransition
    r2 = await auth_client.post(f"/api/v1/agent-tasks/{created['id']}/cancel")
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_approval_flow(
    auth_client: AsyncClient, db_session, test_user
) -> None:
    """模拟 worker 把任务推到 NEEDS_APPROVAL，然后通过 API approve。"""
    # 1. API 创建任务
    created = await _create_task_via_api(auth_client)
    task_id = created["id"]

    # 2. 后台用 service 把它推到 NEEDS_APPROVAL（绕过 worker）
    service = TaskOrchestratorService(db_session)
    await service.start(task_id)
    await service.request_approval(task_id, reason="测试审批")
    await db_session.commit()

    # 3. API approve
    r = await auth_client.post(f"/api/v1/agent-tasks/{task_id}/approve", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == TaskStatus.RUNNING.value


@pytest.mark.asyncio
async def test_approval_reject_flow(
    auth_client: AsyncClient, db_session, test_user
) -> None:
    created = await _create_task_via_api(auth_client)
    task_id = created["id"]

    service = TaskOrchestratorService(db_session)
    await service.start(task_id)
    await service.request_approval(task_id, reason="测试")
    await db_session.commit()

    r = await auth_client.post(
        f"/api/v1/agent-tasks/{task_id}/reject",
        json={"reason": "驳回测试"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == TaskStatus.CANCELLED.value


@pytest.mark.asyncio
async def test_get_result_endpoint(
    auth_client: AsyncClient, db_session, test_user
) -> None:
    created = await _create_task_via_api(auth_client)
    task_id = created["id"]

    # 推到 DONE
    service = TaskOrchestratorService(db_session)
    await service.start(task_id)
    await service.complete(task_id, {"answer": "42"})
    await db_session.commit()

    r = await auth_client.get(f"/api/v1/agent-tasks/{task_id}/result")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == TaskStatus.DONE.value
    assert body["result"] == {"answer": "42"}


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/v1/agent-tasks",
        json={"agent_persona": "free_legal"},
    )
    assert r.status_code == 401
