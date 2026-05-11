# -*- coding: utf-8 -*-
"""LeadHunterAgent 5 capability mock 测试 (P7-C)。

覆盖：
    1. discover_leads     — criteria 过滤 + 排序 + limit 截断
    2. draft_email        — 多语言模板加载 + 占位符替换 + AB 主题
    3. linkedin_outreach  — 校验 / OAuth / 长度 / mock client 路径
    4. generate_quote     — 占位字节流 + docx_skill mock
    5. sync_to_crm        — 不支持 CRM / 缺 token / mock client upsert
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.agents.personas.lead_hunter import LeadHunterAgent
from src.agents.personas.sales_models import (
    Contact,
    Lead,
    LeadDiscoveryCriteria,
    QuoteItem,
    QuoteTerms,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def agent() -> LeadHunterAgent:
    return LeadHunterAgent()


@pytest.fixture
def candidates() -> list[dict]:
    return [
        {
            "id": "lead-001",
            "company_name": "广州绿能配件有限公司",
            "industry": "新能源汽车配件",
            "country": "中国",
            "employees_estimate": 250,
            "contacts": [
                {"name": "张总", "title": "采购总监", "email": "z@green.cn"},
            ],
            "tags": ["funded"],
            "source": "linkedin",
            "signals": {"recent_funding_news": 0.9},
        },
        {
            "id": "lead-002",
            "company_name": "Acme Bicycle",
            "industry": "自行车制造",  # 不匹配 ICP
            "country": "美国",
            "employees_estimate": 1000,
            "contacts": [
                {"name": "John", "title": "Engineer", "email": "j@acme.com"},
            ],
            "tags": [],
            "source": "manual",
        },
        {
            "id": "lead-003",
            "company_name": "深圳新动力电池",
            "industry": "新能源汽车配件",
            "country": "中国",
            "employees_estimate": 80,
            "contacts": [
                {"name": "Lily", "title": "VP Sales", "linkedin_url": "x"},
            ],
            "tags": ["uses-bosch"],
            "source": "qichacha",
        },
        {
            "id": "lead-004",
            "company_name": "Competitor Inc",
            "industry": "新能源汽车配件",
            "country": "中国",
            "employees_estimate": 600,
            "contacts": [],
            "tags": ["competitor"],
            "source": "manual",
        },
    ]


# ---------------------------------------------------------------------------
# 1. discover_leads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_leads_filters_and_scores(agent, candidates):
    crit = LeadDiscoveryCriteria(
        industry="新能源汽车配件",
        company_size="50-500",
        exclude_competitors=True,
        limit=10,
    )
    leads = await agent.discover_leads(crit, candidates=candidates)
    ids = [lead.id for lead in leads]

    # 1) 行业不匹配的 lead-002 被剔除
    assert "lead-002" not in ids
    # 2) competitor 标签被剔除
    assert "lead-004" not in ids
    # 3) 公司规模 600 超过 500 上限 → lead-001 (250) 与 lead-003 (80) 通过
    assert "lead-001" in ids and "lead-003" in ids
    # 4) 评分排序：lead-001 有 funded + DM ⇒ 应排第一
    assert leads[0].id == "lead-001"
    assert all(lead.score > 0 for lead in leads)


@pytest.mark.asyncio
async def test_discover_leads_respects_limit(agent, candidates):
    crit = LeadDiscoveryCriteria(industry="新能源汽车配件", limit=1)
    leads = await agent.discover_leads(crit, candidates=candidates)
    assert len(leads) == 1


# ---------------------------------------------------------------------------
# 2. draft_email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_email_zh_cold_intro_renders_company_name(agent):
    lead = Lead(
        id="x",
        company_name="深圳新动力电池",
        industry="新能源汽车配件",
        country="中国",
        contacts=[Contact(name="李总监", title="采购总监")],
    )
    draft = await agent.draft_email(
        lead,
        intent="cold_intro",
        language="zh",
        sender={"name": "Anxin", "company": "安心智能"},
        hooks={"hook_recent_news": "完成 A 轮融资"},
    )
    assert draft.language == "zh"
    assert draft.template_id == "cold_intro_zh"
    assert "深圳新动力电池" in draft.subject or "深圳新动力电池" in draft.body
    assert "完成 A 轮融资" in draft.body
    assert len(draft.subject_variants) >= 1  # 至少 2 个总变体（首个用作 subject）
    assert 0 < draft.estimated_response_rate <= 0.5


@pytest.mark.asyncio
async def test_draft_email_falls_back_when_template_missing(agent):
    lead = Lead(id="x", company_name="C", industry="i", country="US")
    # ja + cold_intro 不存在，应回退到 cold_intro_zh
    draft = await agent.draft_email(lead, intent="cold_intro", language="ja")
    assert draft.template_id == "cold_intro_zh"


# ---------------------------------------------------------------------------
# 3. linkedin_outreach
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linkedin_outreach_rejects_invalid_url(agent):
    res = await agent.linkedin_outreach(
        "https://twitter.com/x", "hi", oauth_token="t"
    )
    assert res["ok"] is False
    assert res["error"] == "invalid_profile_url"


@pytest.mark.asyncio
async def test_linkedin_outreach_requires_oauth(agent):
    res = await agent.linkedin_outreach(
        "https://www.linkedin.com/in/abc/", "hi", oauth_token=""
    )
    assert res["ok"] is False
    assert res["error"] == "oauth_required"


@pytest.mark.asyncio
async def test_linkedin_outreach_rejects_long_message(agent):
    res = await agent.linkedin_outreach(
        "https://www.linkedin.com/in/abc/", "x" * 301, oauth_token="t"
    )
    assert res["ok"] is False
    assert res["error"] == "message_too_long"


@pytest.mark.asyncio
async def test_linkedin_outreach_uses_injected_client(agent):
    mock = AsyncMock()
    mock.send_connection_request = AsyncMock(return_value={"invitation_id": "abc"})
    res = await agent.linkedin_outreach(
        "https://www.linkedin.com/in/abc/",
        "hello",
        oauth_token="t",
        client=mock,
    )
    assert res["ok"] is True
    assert res["status"] == "sent"
    assert res["invitation_id"] == "abc"
    mock.send_connection_request.assert_awaited_once()


# ---------------------------------------------------------------------------
# 4. generate_quote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_quote_placeholder_bytes(agent):
    lead = Lead(id="x", company_name="ACME", industry="i", country="US")
    items = [QuoteItem(sku="A1", name="Widget", description=None,
                       quantity=10, unit_price=20.0, currency="USD")]
    blob = await agent.generate_quote(lead, items, terms={})
    assert isinstance(blob, bytes) and len(blob) > 0
    assert b"ACME" in blob
    assert b"USD" in blob


@pytest.mark.asyncio
async def test_generate_quote_uses_docx_skill_when_provided(agent):
    lead = Lead(id="x", company_name="ACME", industry="i", country="US")
    items = [QuoteItem(sku="A1", name="W", description=None,
                       quantity=1, unit_price=99.99, currency="USD")]
    skill = AsyncMock()
    skill.render_quote = AsyncMock(return_value=b"FAKE_DOCX_BYTES")
    blob = await agent.generate_quote(lead, items, QuoteTerms(), docx_skill=skill)
    assert blob == b"FAKE_DOCX_BYTES"
    skill.render_quote.assert_awaited_once()


# ---------------------------------------------------------------------------
# 5. sync_to_crm
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_to_crm_unsupported_crm(agent):
    res = await agent.sync_to_crm([Lead(id="x", company_name="C",
                                         industry="i", country="US")],
                                  crm="weirdcrm", oauth_token="t")
    assert res["failed"] == 1
    assert res["errors"][0]["reason"] == "unsupported_crm"


@pytest.mark.asyncio
async def test_sync_to_crm_requires_token(agent):
    res = await agent.sync_to_crm([Lead(id="x", company_name="C",
                                         industry="i", country="US")],
                                  crm="hubspot", oauth_token="")
    assert res["failed"] == 1
    assert res["errors"][0]["reason"] == "oauth_required"


@pytest.mark.asyncio
async def test_sync_to_crm_with_client_aggregates_results(agent):
    leads = [
        Lead(id="a", company_name="A", industry="i", country="US"),
        Lead(id="b", company_name="B", industry="i", country="US"),
        Lead(id="c", company_name="C", industry="i", country="US"),
    ]
    client = AsyncMock()
    client.upsert_lead = AsyncMock(side_effect=[
        {"action": "created"},
        {"action": "updated"},
        Exception("boom"),
    ])
    res = await agent.sync_to_crm(leads, crm="salesforce",
                                  oauth_token="t", client=client)
    assert res["created"] == 1
    assert res["updated"] == 1
    assert res["failed"] == 1
    assert res["errors"][0]["lead_id"] == "c"
    assert res["crm"] == "salesforce"
