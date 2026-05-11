# -*- coding: utf-8 -*-
"""税务计算边界场景单元测试（P9-E）。

聚焦数值边界与档位切换：
    - 增值税：进项 > 销项（留抵）/ items 明细驱动
    - 企业所得税：300 万阈值切换、亏损归零、高新 + 小微互斥优先级
    - 出口退税：HS 编码档位（机电 / 默认）/ 多笔加权 / 零金额
"""

from __future__ import annotations

from datetime import date

import pytest

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.agents.personas.finance_models import (  # noqa: E402
    ExportTransaction,
    TaxCalculationRequest,
)
from src.agents.personas.tax_finance_advisor import (  # noqa: E402
    CIT_HIGH_TECH_RATE_PCT,
    CIT_SMALL_MICRO_EFFECTIVE_RATE_PCT,
    CIT_STANDARD_RATE_PCT,
    EXPORT_REBATE_RATES_PCT,
    TaxFinanceAdvisorPersona,
)


# ---------------------------------------------------------------------------
# 增值税边界
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_vat_input_exceeds_output_zero_payable():
    """进项税额 > 销项时应缴 = 0（留抵）。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="vat",
        revenue=1_000_000,
        expenses=2_000_000,  # 进项 > 销项
    )
    r = await p.calculate_tax(req)
    assert r.tax_payable == 0.0
    assert r.breakdown["input_tax"] > r.breakdown["output_tax"]


@pytest.mark.asyncio
async def test_vat_items_driven():
    """items 明细驱动（不同税率混合）。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="vat",
        items=[
            {"name": "销售货物", "amount": 1_000_000, "rate_pct": 13.0, "type": "output"},
            {"name": "现代服务", "amount": 500_000, "rate_pct": 6.0, "type": "output"},
            {"name": "采购原材料", "amount": 600_000, "rate_pct": 13.0, "type": "input"},
        ],
        period="monthly",
    )
    r = await p.calculate_tax(req)
    # 销项: 1M*13% + 0.5M*6% = 130000 + 30000 = 160000
    # 进项: 0.6M*13% = 78000
    # 应交: 82000
    assert r.tax_payable == pytest.approx(82_000.0, abs=1.0)


@pytest.mark.asyncio
async def test_vat_zero_revenue_zero_payable():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(tax_type="vat", revenue=0.0, expenses=0.0)
    r = await p.calculate_tax(req)
    assert r.tax_payable == 0.0


# ---------------------------------------------------------------------------
# 企业所得税边界
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cit_loss_makes_taxable_income_zero():
    """收入 < 费用 时应纳税所得额归零，税额 = 0。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=10_000_000,
        expenses=15_000_000,  # 亏损
    )
    r = await p.calculate_tax(req)
    assert r.taxable_amount == 0.0
    assert r.tax_payable == 0.0


@pytest.mark.asyncio
async def test_cit_threshold_300w_just_below():
    """taxable=299 万 < 300 万 → 触发小微 5%。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=4_990_000,
        expenses=2_000_000,  # taxable = 299 万
    )
    r = await p.calculate_tax(req)
    assert r.tax_rate_pct == CIT_SMALL_MICRO_EFFECTIVE_RATE_PCT


@pytest.mark.asyncio
async def test_cit_threshold_300w_above():
    """taxable=301 万 > 300 万 → 标准 25%。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=10_010_000,
        expenses=7_000_000,  # taxable = 301 万
    )
    r = await p.calculate_tax(req)
    assert r.tax_rate_pct == CIT_STANDARD_RATE_PCT


@pytest.mark.asyncio
async def test_cit_high_tech_takes_priority_over_default():
    """显式 high_tech 触发 15%。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=100_000_000,
        expenses=70_000_000,
        special_treatment=["high_tech"],
    )
    r = await p.calculate_tax(req)
    assert r.tax_rate_pct == CIT_HIGH_TECH_RATE_PCT


@pytest.mark.asyncio
async def test_cit_small_micro_overrides_high_tech_when_threshold_hit():
    """small_micro 显式声明且 taxable ≤ 300 万 → 优先小微 5%（小微更优惠）。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=4_000_000,
        expenses=2_000_000,  # taxable=200 万
        special_treatment=["small_micro", "high_tech"],
    )
    r = await p.calculate_tax(req)
    # 小微优先（实现里 small_micro 分支先判定）
    assert r.tax_rate_pct == CIT_SMALL_MICRO_EFFECTIVE_RATE_PCT


# ---------------------------------------------------------------------------
# 个税边界（档位切换）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_iit_below_5000_threshold_zero():
    """全年 < 60000 → 应纳税所得 0 → 税额 0。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(tax_type="individual_income", revenue=50_000)
    r = await p.calculate_tax(req)
    assert r.tax_payable == 0.0


@pytest.mark.asyncio
async def test_iit_top_bracket_45pct():
    """高收入触发 45% 顶档。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(tax_type="individual_income", revenue=2_000_000)
    r = await p.calculate_tax(req)
    # 应纳税 = 2M - 6万 = 194 万 → 落 45% 档
    # 1940000 × 45% - 181920 = 691080
    assert r.tax_rate_pct == 45.0
    assert r.tax_payable == pytest.approx(691_080.0, abs=1.0)


# ---------------------------------------------------------------------------
# 出口退税边界
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_export_rebate_default_rate_for_unknown_hs():
    """未知 HS 章节落 default 13%。"""
    p = TaxFinanceAdvisorPersona()
    tx = ExportTransaction(
        invoice_no="EXP100",
        product_code="X",
        hs_code="9999999999",  # 99 章不在表
        quantity=1,
        unit_price_usd=1000,
        fob_total_usd=1000,
        customs_declaration_no="CD100",
        export_date=date(2025, 3, 1),
    )
    r = await p.export_tax_rebate([tx])
    assert r.rebate_rate_pct == pytest.approx(EXPORT_REBATE_RATES_PCT["default"], abs=0.01)


@pytest.mark.asyncio
async def test_export_rebate_multi_chapter_weighted_avg():
    """多章节加权平均（机电 13% + 默认 13%）。"""
    p = TaxFinanceAdvisorPersona()
    txs = [
        ExportTransaction(
            invoice_no="EXP1",
            product_code="A",
            hs_code="8471300000",
            quantity=1,
            unit_price_usd=1000,
            fob_total_usd=1000,
            customs_declaration_no="CD1",
            export_date=date(2025, 4, 1),
        ),
        ExportTransaction(
            invoice_no="EXP2",
            product_code="B",
            hs_code="3924100000",
            quantity=1,
            unit_price_usd=2000,
            fob_total_usd=2000,
            customs_declaration_no="CD2",
            export_date=date(2025, 4, 5),
        ),
    ]
    r = await p.export_tax_rebate(txs)
    assert r.rebate_rate_pct == pytest.approx(13.0, abs=0.01)
    # 总 FOB 3000 USD × 7.10 × 13% = 2769
    assert r.eligible_rebate_amount_cny == pytest.approx(2769.0, rel=0.01)


@pytest.mark.asyncio
async def test_export_rebate_zero_fob_flagged_risk():
    """FOB = 0 触发 risk 提示。"""
    p = TaxFinanceAdvisorPersona()
    tx = ExportTransaction(
        invoice_no="EXP0",
        product_code="X",
        hs_code="8471",
        quantity=1,
        unit_price_usd=0,
        fob_total_usd=0,  # 异常
        customs_declaration_no="CD0",
        export_date=date(2025, 1, 1),
    )
    r = await p.export_tax_rebate([tx])
    assert any("FOB" in s or "异常" in s for s in r.risks)


@pytest.mark.asyncio
async def test_export_rebate_filing_date_next_month_15():
    """expected_filing_date = max(export_date) 的次月 15 日。"""
    p = TaxFinanceAdvisorPersona()
    tx = ExportTransaction(
        invoice_no="EXP_DEC",
        product_code="X",
        hs_code="8471",
        quantity=1,
        unit_price_usd=100,
        fob_total_usd=100,
        customs_declaration_no="CD-DEC",
        export_date=date(2025, 12, 20),
    )
    r = await p.export_tax_rebate([tx])
    # 12 月出口 → 次年 1 月 15 日
    assert r.expected_filing_date == date(2026, 1, 15)


# ---------------------------------------------------------------------------
# 跨境 VAT 边界（与上面 persona 测试互补）
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cross_border_vat_b2b_eu_no_oss():
    """欧盟内 B2B 交易不触发 OSS（仅 B2C 触发）。"""
    p = TaxFinanceAdvisorPersona()
    advice = await p.cross_border_vat_guidance(
        country="德国",
        scenario="商对商批发出口",
        amount=50_000,
        currency="EUR",
    )
    assert advice.needs_oss_registration is False


@pytest.mark.asyncio
async def test_cross_border_vat_below_threshold_no_oss():
    """欧盟 B2C 但销售额 < 阈值不触发 OSS。"""
    p = TaxFinanceAdvisorPersona()
    advice = await p.cross_border_vat_guidance(
        country="德国",
        scenario="B2C 独立站",
        amount=5_000,  # < €10000
        currency="EUR",
    )
    assert advice.needs_oss_registration is False
