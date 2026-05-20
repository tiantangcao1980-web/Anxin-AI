# -*- coding: utf-8 -*-
"""
Triage Service 单元测试 — CREAO Slice 2 (A3, 2026-05-14)

覆盖:
1. test_no_open_incidents_returns_empty       — 空表
2. test_clusters_by_source_agent_route        — 三键聚类
3. test_severity_max_picks_worst              — P1 vs P2 → P1
4. test_transition_state_open_to_triaged      — 状态机推进
5. test_dry_run_does_not_write                — dry_run=True 不改库
6. test_trend_label_surging                   — 1h 高于 24h 平均 1.5x → surging
7. test_trend_label_quiet                     — 24h 内无更新 → quiet
8. test_overview_aggregates                   — get_triage_overview 三维度计数
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.harness.triage_service import (
    get_triage_overview,
    triage_open_incidents,
)
from src.models.incident import Incident


@pytest_asyncio.fixture(autouse=True)
async def _clean_incidents(db_session: AsyncSession):
    await db_session.execute(sa_delete(Incident))
    await db_session.commit()
    yield
    await db_session.execute(sa_delete(Incident))
    await db_session.commit()


def _make_incident(
    *,
    source: str = "output_validator",
    severity: str = "P2",
    agent_name: str | None = None,
    route: str | None = None,
    fingerprint: str = "fp_test",
    occurrence_count: int = 1,
    last_seen_offset: timedelta = timedelta(),
    status: str = "open",
) -> Incident:
    now = datetime.now(timezone.utc)
    return Incident(
        source=source,
        severity=severity,
        fingerprint=fingerprint,
        title=f"{source}/{fingerprint}",
        payload={"k": "v"},
        agent_name=agent_name,
        route=route,
        status=status,
        occurrence_count=occurrence_count,
        first_seen_at=now - timedelta(hours=2) + last_seen_offset,
        last_seen_at=now + last_seen_offset,
    )


# ====================================================================
# 1. 空表
# ====================================================================

@pytest.mark.asyncio
async def test_no_open_incidents_returns_empty(db_session: AsyncSession):
    result = await triage_open_incidents(db_session)
    assert result["scanned"] == 0
    assert result["clusters"] == []
    assert result["transitioned"] == 0


# ====================================================================
# 2. 三键聚类
# ====================================================================

@pytest.mark.asyncio
async def test_clusters_by_source_agent_route(db_session: AsyncSession):
    # 2 个 incident 同 (output_validator, agent_a, /route1) → 1 个 cluster
    # 1 个 incident 不同 route → 独立 cluster
    db_session.add_all([
        _make_incident(agent_name="agent_a", route="/route1", fingerprint="a1"),
        _make_incident(agent_name="agent_a", route="/route1", fingerprint="a2"),
        _make_incident(agent_name="agent_a", route="/route2", fingerprint="a3"),
    ])
    await db_session.commit()

    result = await triage_open_incidents(db_session)
    assert result["scanned"] == 3
    assert len(result["clusters"]) == 2
    # 找到 /route1 cluster, 应有 2 条 incident
    r1 = next(c for c in result["clusters"] if c["route"] == "/route1")
    assert r1["incident_count"] == 2


# ====================================================================
# 3. 严重度取最严
# ====================================================================

@pytest.mark.asyncio
async def test_severity_max_picks_worst(db_session: AsyncSession):
    db_session.add_all([
        _make_incident(severity="P2", agent_name="x", route="/r", fingerprint="p2"),
        _make_incident(severity="P1", agent_name="x", route="/r", fingerprint="p1"),
        _make_incident(severity="P3", agent_name="x", route="/r", fingerprint="p3"),
    ])
    await db_session.commit()

    result = await triage_open_incidents(db_session)
    assert len(result["clusters"]) == 1
    assert result["clusters"][0]["severity_max"] == "P1"


# ====================================================================
# 4. 状态机推进
# ====================================================================

@pytest.mark.asyncio
async def test_transition_state_open_to_triaged(db_session: AsyncSession):
    db_session.add(_make_incident(agent_name="a", route="/r", fingerprint="t1"))
    await db_session.commit()

    result = await triage_open_incidents(db_session)
    assert result["transitioned"] == 1
    # 重新查
    from sqlalchemy import select as sa_select
    row = (await db_session.execute(sa_select(Incident))).scalar_one()
    assert row.status == "triaged"
    assert row.triage_summary is not None
    assert "agent=a" in row.triage_summary or "/r" in row.triage_summary


# ====================================================================
# 5. dry_run 不写库
# ====================================================================

@pytest.mark.asyncio
async def test_dry_run_does_not_write(db_session: AsyncSession):
    db_session.add(_make_incident(agent_name="a", fingerprint="dry1"))
    await db_session.commit()

    result = await triage_open_incidents(db_session, transition_state=False)
    assert result["scanned"] == 1
    assert result["transitioned"] == 0
    # 重新查 status 还是 open
    from sqlalchemy import select as sa_select
    row = (await db_session.execute(sa_select(Incident))).scalar_one()
    assert row.status == "open"
    assert row.triage_summary is None


# ====================================================================
# 6. 趋势: surging
# ====================================================================

@pytest.mark.asyncio
async def test_trend_label_surging(db_session: AsyncSession):
    """1h 内出现 8 次, 24h 内总共 10 次 → 小时均值 ~0.4, 8 / 0.4 = 20 → surging。"""
    # 制造 1 个 incident, occurrence_count=8, last_seen_at=现在 (落在 1h 窗口)
    inc = _make_incident(
        agent_name="surge",
        fingerprint="surge_fp",
        occurrence_count=8,
    )
    # 再加 2 个 incident, 落在 1h 之外, 24h 之内
    inc2 = _make_incident(
        agent_name="surge",
        fingerprint="surge_fp2",
        occurrence_count=2,
        last_seen_offset=-timedelta(hours=10),
    )
    db_session.add_all([inc, inc2])
    await db_session.commit()

    result = await triage_open_incidents(db_session, transition_state=False)
    cluster = result["clusters"][0]
    assert cluster["trend_24h"] == 10
    assert cluster["trend_1h"] == 8
    assert cluster["trend_label"] == "surging"


# ====================================================================
# 7. 趋势: quiet (24h 内无更新)
# ====================================================================

@pytest.mark.asyncio
async def test_trend_label_quiet(db_session: AsyncSession):
    """incident last_seen_at 在 25h 前 → 24h 窗口外, trend_24h=0 → quiet。"""
    inc = _make_incident(
        agent_name="old",
        fingerprint="old_fp",
        occurrence_count=5,
        last_seen_offset=-timedelta(hours=25),
    )
    db_session.add(inc)
    await db_session.commit()

    result = await triage_open_incidents(db_session, transition_state=False)
    cluster = result["clusters"][0]
    assert cluster["trend_24h"] == 0
    assert cluster["trend_label"] == "quiet"


# ====================================================================
# 8. overview 三维度计数
# ====================================================================

# ====================================================================
# 9. G7: Slice 2.5 LLM 根因猜测 (mock)
# ====================================================================

@pytest.mark.asyncio
async def test_llm_summary_skipped_for_p2(db_session: AsyncSession):
    """G7: enable_llm_summary=True 但 cluster 是 P2 → 不调 LLM。"""
    db_session.add(_make_incident(severity="P2", agent_name="x", fingerprint="p2_g7"))
    await db_session.commit()
    result = await triage_open_incidents(
        db_session, transition_state=False, enable_llm_summary=True,
    )
    assert result["llm_calls"] == 0


@pytest.mark.asyncio
async def test_llm_summary_enabled_calls_for_p1(db_session: AsyncSession, monkeypatch):
    """G7: P1 cluster + enable_llm_summary=True → 调用 LLM (mocked)。"""
    db_session.add(_make_incident(severity="P1", agent_name="critical", fingerprint="p1_g7"))
    await db_session.commit()

    # mock _generate_llm_summary 返回固定字符串
    from src.harness import triage_service
    async def fake_summary(cluster, samples):
        return "数据库连接池耗尽"
    monkeypatch.setattr(triage_service, "_generate_llm_summary", fake_summary)

    result = await triage_open_incidents(
        db_session, transition_state=True, enable_llm_summary=True,
    )
    assert result["llm_calls"] == 1
    cluster = result["clusters"][0]
    assert cluster["llm_root_cause_hint"] == "数据库连接池耗尽"
    # incident.triage_summary 也应含根因
    from sqlalchemy import select as sa_select
    inc = (await db_session.execute(sa_select(Incident))).scalar_one()
    assert "根因猜测: 数据库连接池耗尽" in (inc.triage_summary or "")


@pytest.mark.asyncio
async def test_llm_summary_disabled_by_default(db_session: AsyncSession, monkeypatch):
    """G7: 默认 enable_llm_summary=False → 不调 LLM (零 token 消耗)。"""
    db_session.add(_make_incident(severity="P0", agent_name="urgent", fingerprint="p0_g7"))
    await db_session.commit()

    from src.harness import triage_service
    calls = []
    async def fake_summary(cluster, samples):
        calls.append(1)
        return "should not be called"
    monkeypatch.setattr(triage_service, "_generate_llm_summary", fake_summary)

    result = await triage_open_incidents(db_session, transition_state=False)
    assert len(calls) == 0
    assert result["llm_calls"] == 0


@pytest.mark.asyncio
async def test_overview_aggregates(db_session: AsyncSession):
    db_session.add_all([
        _make_incident(source="output_validator", severity="P1", fingerprint="o1"),
        _make_incident(source="output_validator", severity="P2", fingerprint="o2", status="triaged"),
        _make_incident(source="api_5xx", severity="P0", fingerprint="a1"),
    ])
    await db_session.commit()

    overview = await get_triage_overview(db_session)
    assert overview["by_status"]["open"] == 2
    assert overview["by_status"]["triaged"] == 1
    assert overview["by_severity"]["P0"] == 1
    assert overview["by_severity"]["P1"] == 1
    assert overview["by_severity"]["P2"] == 1
    assert overview["by_source"]["output_validator"] == 2
    assert overview["by_source"]["api_5xx"] == 1
