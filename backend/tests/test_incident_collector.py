# -*- coding: utf-8 -*-
"""
IncidentCollector 单元测试 — Slice 1

覆盖：
1. test_collect_creates_new_incident      — 新建落库
2. test_collect_dedupes_within_5_min      — 5 分钟窗口去重
3. test_collect_scrubs_pii                — 手机号被脱敏，原号不残留
4. test_fingerprint_stable                — 同 source+title 指纹稳定
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.harness.incident_collector import IncidentCollector
from src.models.incident import Incident
from src.schemas.incident import IncidentSeverity, IncidentSource
from src.services.pii_service import PIIService


@pytest_asyncio.fixture
async def collector(db_session: AsyncSession) -> IncidentCollector:
    """每个测试获得独立的 PIIService（内部 redaction_map 是有状态的）。"""
    return IncidentCollector(db=db_session, pii=PIIService())


@pytest_asyncio.fixture(autouse=True)
async def _clean_incidents(db_session: AsyncSession):
    """每个测试前后清空 incidents 表，避免上一个 test commit 的污染。

    conftest 的 db_session fixture 会 rollback，但 collector.collect()
    会 commit，所以需要手动清理。
    """
    from sqlalchemy import delete as sa_delete
    await db_session.execute(sa_delete(Incident))
    await db_session.commit()
    yield
    await db_session.execute(sa_delete(Incident))
    await db_session.commit()


# ====================================================================
# 1. 新建落库
# ====================================================================

@pytest.mark.asyncio
async def test_collect_creates_new_incident(
    collector: IncidentCollector,
    db_session: AsyncSession,
):
    incident = await collector.collect(
        source=IncidentSource.OUTPUT_VALIDATOR,
        title="合同起草输出缺少必要条款",
        payload={"missing_clauses": ["违约责任", "争议解决"]},
        severity=IncidentSeverity.P1,
        agent_name="DocumentDrafter",
        route="/api/v1/agents/document_drafter",
    )

    assert incident.id is not None
    assert incident.source == "output_validator"
    assert incident.severity == "P1"
    assert incident.status == "open"
    assert incident.occurrence_count == 1
    assert incident.fingerprint
    assert len(incident.fingerprint) == 64

    # 数据库可读
    rows = (await db_session.execute(select(Incident))).scalars().all()
    assert len(rows) == 1
    assert rows[0].agent_name == "DocumentDrafter"


# ====================================================================
# 2. 5 分钟窗口去重
# ====================================================================

@pytest.mark.asyncio
async def test_collect_dedupes_within_5_min(
    collector: IncidentCollector,
    db_session: AsyncSession,
):
    payload = {"reason": "format_error"}

    first = await collector.collect(
        source=IncidentSource.AGENT_FORUM,
        title="Agent 内部辩论分歧",
        payload=payload,
    )
    second = await collector.collect(
        source=IncidentSource.AGENT_FORUM,
        title="Agent 内部辩论分歧",
        payload=payload,
    )
    third = await collector.collect(
        source=IncidentSource.AGENT_FORUM,
        title="Agent 内部辩论分歧",
        payload=payload,
    )

    assert first.id == second.id == third.id, "同 fingerprint 应复用记录"
    assert third.occurrence_count == 3

    rows = (await db_session.execute(select(Incident))).scalars().all()
    assert len(rows) == 1, "5 分钟内同类只能有一条"


# ====================================================================
# 3. PII 脱敏
# ====================================================================

@pytest.mark.asyncio
async def test_collect_scrubs_pii(
    collector: IncidentCollector,
    db_session: AsyncSession,
):
    raw_phone = "13812345678"
    raw_id = "110101199001011234"  # 18 位身份证

    incident = await collector.collect(
        source=IncidentSource.LOW_RATING,
        title=f"用户 {raw_phone} 反馈差评",
        payload={
            "user_phone": raw_phone,
            "user_id_card": raw_id,
            "comment": f"我手机 {raw_phone} 没收到验证码",
            "nested": {"contact": raw_phone},
            "tags": ["bad", raw_phone],
        },
    )

    # 序列化整个 payload + title 检查
    full_text = (
        incident.title
        + " "
        + str(incident.payload)
    )
    assert raw_phone not in full_text, (
        f"PII 手机号 {raw_phone} 不应残留：{full_text!r}"
    )
    assert raw_id not in full_text, (
        f"PII 身份证 {raw_id} 不应残留：{full_text!r}"
    )
    # 占位符存在
    assert "[PHONE_" in full_text or "[ID_" in full_text


# ====================================================================
# 4. 指纹稳定性
# ====================================================================

@pytest.mark.asyncio
async def test_fingerprint_stable(
    collector: IncidentCollector,
    db_session: AsyncSession,
):
    """同样的 source+title 两次调用，fingerprint 必须一致。"""
    fp1 = IncidentCollector._make_fingerprint(
        IncidentSource.API_5XX,
        "POST /api/v1/agents/legal_advisor 500",
        {"err": "TimeoutError"},
        fingerprint_keys=None,
    )
    fp2 = IncidentCollector._make_fingerprint(
        IncidentSource.API_5XX,
        "POST /api/v1/agents/legal_advisor 500",
        {"err": "OtherError"},  # payload 变了，但用 None 时只看 title
        fingerprint_keys=None,
    )
    assert fp1 == fp2, "fingerprint_keys=None 时只用 title，应稳定"

    # 用 fingerprint_keys 时跟选定字段相关
    fp3 = IncidentCollector._make_fingerprint(
        IncidentSource.API_5XX,
        "any title",
        {"err": "TimeoutError", "trace": "abc"},
        fingerprint_keys=["err"],
    )
    fp4 = IncidentCollector._make_fingerprint(
        IncidentSource.API_5XX,
        "different title",
        {"err": "TimeoutError", "trace": "xyz"},
        fingerprint_keys=["err"],
    )
    assert fp3 == fp4, "选定 fingerprint_keys 时只看选定字段"
    assert fp3 != fp1, "fingerprint 算法应区分输入"
