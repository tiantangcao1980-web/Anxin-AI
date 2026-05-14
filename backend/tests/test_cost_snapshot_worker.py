# -*- coding: utf-8 -*-
"""
cost_snapshot worker 单测 — E2 (2026-05-14)

覆盖:
1. test_snapshot_empty_tracker_no_error  — 内存空时不报错
2. test_snapshot_flushes_user_data       — 累计→DB upsert
3. test_snapshot_repeated_idempotent     — 重复执行更新同一行
"""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.harness.cost_tracker import cost_tracker
from src.models.user_token_usage import UserTokenUsage


@pytest_asyncio.fixture(autouse=True)
async def _clean(db_session: AsyncSession):
    await db_session.execute(sa_delete(UserTokenUsage))
    await db_session.commit()
    # 同时清零 cost_tracker 内存, 避免测试间污染
    cost_tracker._by_user_tokens.clear()
    cost_tracker._by_user.clear()
    yield
    await db_session.execute(sa_delete(UserTokenUsage))
    await db_session.commit()
    cost_tracker._by_user_tokens.clear()
    cost_tracker._by_user.clear()


@pytest.mark.asyncio
async def test_snapshot_empty_tracker_no_error(db_session: AsyncSession):
    """内存空时, snapshot_to_db 不应崩, 返回 0。"""
    today = date.today()
    n = await cost_tracker.snapshot_to_db(
        db_session, period_start=today, period_end=today,
    )
    await db_session.commit()
    assert n == 0
    rows = (await db_session.execute(select(UserTokenUsage))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_snapshot_flushes_user_data(db_session: AsyncSession):
    """累计的用户数据应被写入 DB (单一活跃行)。"""
    cost_tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=300, completion_tokens=200, user_id="snapshot_u1",
    )
    today = date.today()
    await cost_tracker.snapshot_to_db(
        db_session, period_start=today, period_end=today,
    )
    await db_session.commit()
    row = (await db_session.execute(select(UserTokenUsage))).scalar_one()
    assert row.user_id == "snapshot_u1"
    assert row.tokens_used == 500
    assert row.archived is False


@pytest.mark.asyncio
async def test_snapshot_repeated_idempotent(db_session: AsyncSession):
    """连续两次 snapshot 应 upsert 而不是新建行。"""
    cost_tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=100, completion_tokens=50, user_id="snapshot_u2",
    )
    today = date.today()
    await cost_tracker.snapshot_to_db(db_session, period_start=today, period_end=today)
    await db_session.commit()

    # 再追加, 再 snapshot
    cost_tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=200, completion_tokens=100, user_id="snapshot_u2",
    )
    await cost_tracker.snapshot_to_db(db_session, period_start=today, period_end=today)
    await db_session.commit()

    rows = (await db_session.execute(select(UserTokenUsage))).scalars().all()
    assert len(rows) == 1
    assert rows[0].tokens_used == 450  # 100+50+200+100
