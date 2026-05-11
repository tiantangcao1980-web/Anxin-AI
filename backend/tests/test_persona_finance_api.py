# -*- coding: utf-8 -*-
"""财税顾问 7 个 API endpoint 集成测试（P9-E）。

覆盖：
    POST /api/v1/personas/finance/calculate-tax
    POST /api/v1/personas/finance/export-rebate
    POST /api/v1/personas/finance/cross-border-vat
    POST /api/v1/personas/finance/analyze-report
    POST /api/v1/personas/finance/tax-plan
    GET  /api/v1/personas/finance/tax-rates
    GET  /api/v1/personas/finance/calendar

鉴权：所有 endpoint 都要求登录用户。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):
    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


import pytest
from httpx import AsyncClient


PREFIX = "/api/v1/personas/finance"


# ---------------------------------------------------------------------------
# 1. calculate-tax
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_calculate_tax_vat(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/calculate-tax",
        json={
            "tax_type": "vat",
            "revenue": 10_000_000,
            "expenses": 6_000_000,
            "period": "monthly",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tax_type"] == "vat"
    assert body["tax_payable"] == pytest.approx(520_000.0, abs=1.0)
    assert body["legal_basis"]


@pytest.mark.asyncio
async def test_calculate_tax_invalid_type_returns_422(
    auth_client: AsyncClient,
) -> None:
    r = await auth_client.post(
        f"{PREFIX}/calculate-tax",
        json={"tax_type": "fake_tax", "revenue": 100, "period": "monthly"},
    )
    # pydantic 校验拦截
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_calculate_tax_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        f"{PREFIX}/calculate-tax",
        json={"tax_type": "vat", "revenue": 100},
    )
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 2. export-rebate
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_export_rebate_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/export-rebate",
        json={
            "exports": [
                {
                    "invoice_no": "EXP001",
                    "product_code": "P001",
                    "hs_code": "8471300000",
                    "quantity": 100,
                    "unit_price_usd": 50.0,
                    "fob_total_usd": 5000.0,
                    "customs_declaration_no": "CD2025001",
                    "export_date": "2025-06-01",
                }
            ]
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["eligible_rebate_amount_cny"] > 0
    assert "出口货物报关单" in body["required_documents"]


@pytest.mark.asyncio
async def test_export_rebate_bad_date_returns_400(
    auth_client: AsyncClient,
) -> None:
    r = await auth_client.post(
        f"{PREFIX}/export-rebate",
        json={
            "exports": [
                {
                    "invoice_no": "X",
                    "product_code": "X",
                    "hs_code": "8471",
                    "quantity": 1,
                    "unit_price_usd": 100,
                    "fob_total_usd": 100,
                    "customs_declaration_no": "X",
                    "export_date": "2025/06/01",  # 错误格式
                }
            ]
        },
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 3. cross-border-vat
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cross_border_vat_germany_b2c(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/cross-border-vat",
        json={
            "country": "德国",
            "scenario": "独立站 B2C",
            "amount": 20000,
            "currency": "EUR",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["vat_rate_pct"] == 19.0
    assert body["needs_oss_registration"] is True
    assert "不构成专业" in body["disclaimer"]


@pytest.mark.asyncio
async def test_cross_border_vat_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        f"{PREFIX}/cross-border-vat",
        json={"country": "德国", "scenario": "B2C", "amount": 100, "currency": "EUR"},
    )
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 4. analyze-report
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analyze_report_text(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/analyze-report",
        json={
            "report_text": "公司应收账款暴增，经营性现金流为负，研发投入显著",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "summary" in body
    assert isinstance(body["red_flags"], list)
    assert 0 <= body["overall_health_score"] <= 100


@pytest.mark.asyncio
async def test_analyze_report_missing_input_returns_400(
    auth_client: AsyncClient,
) -> None:
    r = await auth_client.post(
        f"{PREFIX}/analyze-report",
        json={},
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 5. tax-plan
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tax_plan_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/tax-plan",
        json={
            "business_profile": {
                "industry": "制造业",
                "annual_revenue": 100_000_000,
                "employees": 200,
                "is_high_tech": False,
                "is_small_micro": False,
                "has_export": True,
                "has_overseas_subsidiary": False,
            },
            "target_year": 2026,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_year"] == 2026
    assert body["savings"] >= 0
    assert "持牌税务师" in body["disclaimer"]
    # 应至少包含研发加计扣除 + 出口退税方案
    strategies = [i["strategy"] for i in body["items"]]
    assert any("研发" in s for s in strategies)
    assert any("出口" in s for s in strategies)


@pytest.mark.asyncio
async def test_tax_plan_past_year_returns_400(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/tax-plan",
        json={
            "business_profile": {
                "industry": "制造业",
                "annual_revenue": 1000,
                "employees": 1,
            },
            "target_year": 2000,
        },
    )
    # year < 2020 触发 pydantic 校验 422，否则 persona ValueError → 400
    assert r.status_code in {400, 422}


# ---------------------------------------------------------------------------
# 6. tax-rates
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tax_rates_china_vat(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/tax-rates",
        params={"country": "CN", "tax_type": "vat", "year": 2026},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    rates = body["rates"]
    assert any(rate["rate_pct"] == 13.0 for rate in rates)
    assert any(rate["rate_pct"] == 9.0 for rate in rates)
    assert any(rate["rate_pct"] == 6.0 for rate in rates)


@pytest.mark.asyncio
async def test_tax_rates_germany(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/tax-rates",
        params={"country": "DE", "tax_type": "vat", "year": 2026},
    )
    assert r.status_code == 200
    rates = r.json()["rates"]
    assert any(rate["rate_pct"] == 19.0 for rate in rates)


# ---------------------------------------------------------------------------
# 7. calendar
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_filing_calendar_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.get(
        f"{PREFIX}/calendar", params={"region": "CN", "year": 2026}
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["year"] == 2026
    assert len(body["months"]) == 12
    # 5 月有汇算清缴
    may = next(m for m in body["months"] if m["month"] == 5)
    assert any("汇算清缴" in d["type"] for d in may["deadlines"])


@pytest.mark.asyncio
async def test_calendar_requires_auth(client: AsyncClient) -> None:
    r = await client.get(
        f"{PREFIX}/calendar", params={"region": "CN", "year": 2026}
    )
    assert r.status_code in {401, 403}
