# -*- coding: utf-8 -*-
"""
cost_tracker 持久化层单测 — A4 (2026-05-14)

覆盖:
1. test_snapshot_creates_row              — 内存有累计但 DB 空 → 创建一行 archived=False
2. test_snapshot_upserts_existing_row     — DB 已有活跃行 → 更新而非新建
3. test_archive_and_reset_zeroes_memory   — 调 archive 后内存清零, DB 行 archived=True
4. test_archive_creates_new_period_row    — 传入 new_period → 新建 archived=False 行
5. test_restore_loads_active_rows         — 内存清空后 restore 应能从 DB 拉回累计
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import delete as sa_delete
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.harness.cost_tracker import CostTracker
from src.models.user_token_usage import UserTokenUsage


@pytest_asyncio.fixture(autouse=True)
async def _clean(db_session: AsyncSession):
    await db_session.execute(sa_delete(UserTokenUsage))
    await db_session.commit()
    yield
    await db_session.execute(sa_delete(UserTokenUsage))
    await db_session.commit()


@pytest.fixture
def tracker() -> CostTracker:
    return CostTracker()


# ====================================================================
# 1. snapshot creates row
# ====================================================================

@pytest.mark.asyncio
async def test_snapshot_creates_row(tracker: CostTracker, db_session: AsyncSession):
    tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=100, completion_tokens=50, user_id="u1",
    )
    today = date.today()
    processed = await tracker.snapshot_to_db(
        db_session, period_start=today, period_end=today + timedelta(days=29),
    )
    await db_session.commit()
    assert processed == 1
    row = (await db_session.execute(select(UserTokenUsage))).scalar_one()
    assert row.user_id == "u1"
    assert row.tokens_used == 150
    assert row.archived is False
    assert row.cost_usd > Decimal("0")


# ====================================================================
# 2. snapshot upserts
# ====================================================================

@pytest.mark.asyncio
async def test_snapshot_upserts_existing_row(tracker: CostTracker, db_session: AsyncSession):
    today = date.today()
    tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=100, completion_tokens=50, user_id="u1",
    )
    await tracker.snapshot_to_db(
        db_session, period_start=today, period_end=today + timedelta(days=29),
    )
    await db_session.commit()

    # 再追加用量, 再 snapshot
    tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=200, completion_tokens=100, user_id="u1",
    )
    await tracker.snapshot_to_db(
        db_session, period_start=today, period_end=today + timedelta(days=29),
    )
    await db_session.commit()

    rows = (await db_session.execute(select(UserTokenUsage))).scalars().all()
    assert len(rows) == 1
    assert rows[0].tokens_used == 450  # 100+50+200+100


# ====================================================================
# 3. archive 后内存清零, DB archived=True
# ====================================================================

@pytest.mark.asyncio
async def test_archive_and_reset_zeroes_memory(tracker: CostTracker, db_session: AsyncSession):
    today = date.today()
    tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=100, completion_tokens=50, user_id="u1",
    )
    await tracker.snapshot_to_db(
        db_session, period_start=today, period_end=today + timedelta(days=29),
    )
    await db_session.commit()

    outcome = await tracker.archive_and_reset_user(db_session, "u1")
    await db_session.commit()

    assert outcome["archived_tokens"] == 150
    assert tracker.get_user_tokens("u1") == 0
    row = (await db_session.execute(select(UserTokenUsage))).scalar_one()
    assert row.archived is True


# ====================================================================
# 4. archive + 新建周期
# ====================================================================

@pytest.mark.asyncio
async def test_archive_creates_new_period_row(tracker: CostTracker, db_session: AsyncSession):
    today = date.today()
    tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=100, completion_tokens=50, user_id="u1",
    )
    await tracker.snapshot_to_db(
        db_session, period_start=today, period_end=today + timedelta(days=29),
    )
    await db_session.commit()

    new_start = today + timedelta(days=30)
    new_end = today + timedelta(days=59)
    outcome = await tracker.archive_and_reset_user(
        db_session, "u1", new_period_start=new_start, new_period_end=new_end,
    )
    await db_session.commit()

    assert outcome["new_period_started"] is True
    rows = (await db_session.execute(
        select(UserTokenUsage).where(UserTokenUsage.user_id == "u1").order_by(UserTokenUsage.archived)
    )).scalars().all()
    assert len(rows) == 2
    active = [r for r in rows if not r.archived][0]
    archived = [r for r in rows if r.archived][0]
    assert active.tokens_used == 0
    assert active.period_start == new_start
    assert archived.tokens_used == 150


# ====================================================================
# 5. restore from db
# ====================================================================

@pytest.mark.asyncio
async def test_restore_loads_active_rows(db_session: AsyncSession):
    # 先用 tracker A snapshot
    t1 = CostTracker()
    t1.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=300, completion_tokens=200, user_id="u1",
    )
    today = date.today()
    await t1.snapshot_to_db(
        db_session, period_start=today, period_end=today + timedelta(days=29),
    )
    await db_session.commit()

    # 模拟重启: 新 tracker, 内存空
    t2 = CostTracker()
    assert t2.get_user_tokens("u1") == 0
    n = await t2.restore_from_db(db_session)
    assert n == 1
    assert t2.get_user_tokens("u1") == 500


# ========== I4 (2026-05-14): Redis 后端 fallback ==========


def test_redis_disabled_by_default(monkeypatch):
    """I4: 未设 COST_TRACKER_REDIS_URL 时, 不调 Redis, 不报错。"""
    monkeypatch.delenv("COST_TRACKER_REDIS_URL", raising=False)
    tracker = CostTracker()
    # record 应不抛
    tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=100, completion_tokens=50, user_id="u_i4",
    )
    # _get_redis_client 应返回 None
    assert tracker._get_redis_client() is None
    # 主路径内存累计仍正常
    assert tracker.get_user_tokens("u_i4") == 150


def test_redis_bad_url_falls_back_to_memory(monkeypatch):
    """I4: 设了非法 Redis URL → 初始化失败, 静默 fallback。"""
    monkeypatch.setenv("COST_TRACKER_REDIS_URL", "redis://invalid-host-doesnt-exist:9999/0")
    tracker = CostTracker()
    # 不应抛
    tracker.record(
        model="gpt-4o", provider="openai",
        prompt_tokens=100, completion_tokens=50, user_id="u_i4b",
    )
    # client 应为 None (ping 失败)
    assert tracker._get_redis_client() is None
    # 内存累计仍正常
    assert tracker.get_user_tokens("u_i4b") == 150
