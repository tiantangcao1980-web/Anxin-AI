# -*- coding: utf-8 -*-
"""
scheduled_tasks 路由 API 测试（D-1）

覆盖：
    - GET    /api/v1/scheduled-tasks            list（含创建后回读、字段契约）
    - POST   /api/v1/scheduled-tasks            create（next_run_at / persona 兜底）
    - PUT    /api/v1/scheduled-tasks/{id}/toggle  toggle
    - 鉴权：未登录 401
    - org 隔离：A org 看不到 / 不能 toggle B org 的任务
    - service 内置 cron 计算单测
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.scheduled_task import ScheduledTask
from src.models.user import Organization
from src.services.scheduled_task_service import compute_next_run, humanize_cron

BASE = "/api/v1/scheduled-tasks"


# ---------------------------------------------------------------------------
# Fixtures：第二个 org + 该 org 的任务（用于隔离测试）
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def other_org(db_session: AsyncSession) -> Organization:
    org = Organization(id=str(uuid4()), name="另一家公司")
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def other_org_task(
    db_session: AsyncSession, other_org: Organization
) -> ScheduledTask:
    task = ScheduledTask(
        id=str(uuid4()),
        org_id=other_org.id,
        name="他 org 的任务",
        kind="contract_expiry_alert",
        cron="0 9 * * *",
        cron_human="每天 09:00",
        status="active",
        agent_persona="legal",
        next_run_at=datetime(2026, 6, 5, 1, 0, tzinfo=UTC),
    )
    db_session.add(task)
    await db_session.flush()
    return task


# ---------------------------------------------------------------------------
# 鉴权
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_requires_auth(client: AsyncClient) -> None:
    resp = await client.get(BASE)
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# create + list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_then_list(auth_client: AsyncClient) -> None:
    create = await auth_client.post(
        BASE,
        json={
            "name": "采购合同到期提醒",
            "kind": "contract_expiry_alert",
            "cron": "0 9 * * *",
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    # 契约字段齐全
    for key in (
        "id",
        "name",
        "kind",
        "cron",
        "cron_human",
        "status",
        "last_run_at",
        "next_run_at",
        "last_run_ok",
        "agent_persona",
    ):
        assert key in body
    # persona 由 kind 兜底
    assert body["agent_persona"] == "legal"
    # cron_human 由后端生成
    assert body["cron_human"] == "每天 09:00"
    # next_run_at 非空，last_run_* 占位 None（执行=P-later）
    assert body["next_run_at"] is not None
    assert body["last_run_at"] is None
    assert body["last_run_ok"] is None
    assert body["status"] == "active"

    listed = await auth_client.get(BASE)
    assert listed.status_code == 200
    items = listed.json()
    assert isinstance(items, list)
    assert any(it["id"] == body["id"] for it in items)


# ---------------------------------------------------------------------------
# toggle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_toggle_status(auth_client: AsyncClient) -> None:
    created = (
        await auth_client.post(
            BASE,
            json={
                "name": "周报",
                "kind": "sentiment_weekly",
                "cron": "0 9 * * 1",
                "agent_persona": "intelligence",
            },
        )
    ).json()
    task_id = created["id"]

    paused = await auth_client.put(f"{BASE}/{task_id}/toggle", json={"status": "paused"})
    assert paused.status_code == 200
    assert paused.json()["status"] == "paused"

    reactivated = await auth_client.put(
        f"{BASE}/{task_id}/toggle", json={"status": "active"}
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"
    assert reactivated.json()["next_run_at"] is not None


@pytest.mark.asyncio
async def test_toggle_unknown_404(auth_client: AsyncClient) -> None:
    resp = await auth_client.put(
        f"{BASE}/{uuid4()}/toggle", json={"status": "paused"}
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# org 隔离
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_excludes_other_org(
    auth_client: AsyncClient, other_org_task: ScheduledTask
) -> None:
    listed = await auth_client.get(BASE)
    assert listed.status_code == 200
    ids = [it["id"] for it in listed.json()]
    assert other_org_task.id not in ids


@pytest.mark.asyncio
async def test_cannot_toggle_other_org_task(
    auth_client: AsyncClient, other_org_task: ScheduledTask
) -> None:
    resp = await auth_client.put(
        f"{BASE}/{other_org_task.id}/toggle", json={"status": "paused"}
    )
    # 跨 org → 视作不存在
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_task(auth_client: AsyncClient) -> None:
    created = (
        await auth_client.post(
            BASE,
            json={"name": "临时", "kind": "case_status_daily", "cron": "0 8 * * *"},
        )
    ).json()
    deleted = await auth_client.delete(f"{BASE}/{created['id']}")
    assert deleted.status_code == 204
    # 删后 list 不含
    listed = await auth_client.get(BASE)
    assert created["id"] not in [it["id"] for it in listed.json()]


# ---------------------------------------------------------------------------
# service 单测：内置 cron 计算（croniter 不可用时的兜底）
# ---------------------------------------------------------------------------


def test_compute_next_run_daily() -> None:
    after = datetime(2026, 6, 4, 10, 0, tzinfo=UTC)
    nxt = compute_next_run("0 9 * * *", after=after)
    # 当天 09:00 已过 → 次日 09:00
    assert nxt == datetime(2026, 6, 5, 9, 0, tzinfo=UTC)


def test_compute_next_run_weekly_monday() -> None:
    # 2026-06-04 是周四 → 下一个周一是 2026-06-08
    after = datetime(2026, 6, 4, 10, 0, tzinfo=UTC)
    nxt = compute_next_run("0 9 * * 1", after=after)
    assert nxt == datetime(2026, 6, 8, 9, 0, tzinfo=UTC)


def test_humanize_cron_variants() -> None:
    assert humanize_cron("0 9 * * *") == "每天 09:00"
    assert humanize_cron("0 9 * * 1") == "每周一 09:00"
    assert humanize_cron("0 18 * * 1-5") == "工作日 18:00"
    assert humanize_cron("0 10 1 * *") == "每月 1 日 10:00"
    assert humanize_cron("0 10 1 1 *") == "每年 1 月 1 日 10:00"
