# -*- coding: utf-8 -*-
"""财税顾问 persona 5 大能力 + 元数据单元测试（P9-E）。

覆盖：
    1. SYSTEM_PROMPT / capabilities / backed_by_agents 元数据一致性
    2. calculate_tax — 5 税种基础路径 + 非法税种
    3. export_tax_rebate — 正常 / 空 / 缺失报关单
    4. cross_border_vat_guidance — 德国 EU + UK + 美国 + 未知
    5. analyze_financial_report — 文本分支 + Excel 路径分支
    6. tax_planning — 高新 / 出口 / 海外子公司分支 + target_year 校验
"""

from __future__ import annotations

from datetime import date

import pytest

# SQLite ↔ JSONB 兼容（与 ecommerce 测试同款，避免 Postgres-only 类型）
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.agents.personas.finance_models import (  # noqa: E402
    BusinessProfile,
    ExportTransaction,
    FinancialAnalysis,
    RebateReport,
    TaxCalculationRequest,
    TaxCalculationResult,
    TaxPlan,
    VATAdvice,
)
from src.agents.personas.tax_finance_advisor import (  # noqa: E402
    CIT_HIGH_TECH_RATE_PCT,
    CIT_STANDARD_RATE_PCT,
    TaxFinanceAdvisorPersona,
)


# ---------------------------------------------------------------------------
# 元数据一致性
# ---------------------------------------------------------------------------
def test_persona_metadata():
    p = TaxFinanceAdvisorPersona()
    assert p.persona_id == "tax_finance_advisor"
    assert p.display_name == "财税顾问"
    assert p.emoji == "💰"
    assert "xlsx" in p.backed_by_skills
    assert "docx" in p.backed_by_skills
    assert "pdf" in p.backed_by_skills
    assert set(p.backed_by_agents) == {"tax_compliance", "legal_calculator"}
    assert set(p.supported_apps) == {"jindie", "yongyou", "xero", "quickbooks"}
    assert len(p.capabilities) == 5
    for cap in (
        "tax_calculation",
        "export_tax_rebate",
        "cross_border_vat",
        "financial_report_analysis",
        "tax_planning",
    ):
        assert cap in p.capabilities
    # SYSTEM_PROMPT 关键约束
    assert "法条优先" in p.SYSTEM_PROMPT
    assert "VAT" in p.SYSTEM_PROMPT


def test_persona_auto_registered():
    """P8-A: persona class 必须自动注册到 PersonaRegistry。"""
    from src.agents.personas.registry import PersonaRegistry

    reg = PersonaRegistry.instance()
    # 兼容前置测试 reset_instance() 留下的空单例：autoload 幂等，会触发 bootstrap
    reg.autoload()
    assert reg.has("tax_finance_advisor")


# ---------------------------------------------------------------------------
# 1. calculate_tax
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_calculate_vat_basic():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="vat",
        revenue=10_000_000,
        expenses=6_000_000,
        period="monthly",
    )
    r = await p.calculate_tax(req)
    assert isinstance(r, TaxCalculationResult)
    assert r.tax_type == "vat"
    # 销项 1.3M - 进项 0.78M = 0.52M
    assert r.tax_payable == pytest.approx(520_000.0, abs=1.0)
    assert r.legal_basis  # 必须有法条
    assert r.payment_deadline is not None


@pytest.mark.asyncio
async def test_calculate_corporate_income_high_tech():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=50_000_000,
        expenses=40_000_000,
        special_treatment=["high_tech"],
    )
    r = await p.calculate_tax(req)
    assert r.tax_rate_pct == CIT_HIGH_TECH_RATE_PCT
    # 应纳税所得额 1000 万 × 15% = 150 万
    assert r.tax_payable == pytest.approx(1_500_000.0, abs=1.0)


@pytest.mark.asyncio
async def test_calculate_corporate_income_small_micro_auto_detect():
    """收入 - 费用 ≤ 300 万自动触发小型微利。"""
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=5_000_000,
        expenses=3_000_000,  # taxable=200 万 < 300 万 → 小微
    )
    r = await p.calculate_tax(req)
    assert r.tax_rate_pct == 5.0  # CIT_SMALL_MICRO_EFFECTIVE_RATE_PCT


@pytest.mark.asyncio
async def test_calculate_corporate_income_standard_rate():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(
        tax_type="corporate_income",
        revenue=100_000_000,
        expenses=70_000_000,  # taxable=3000 万 → 不触发小微
    )
    r = await p.calculate_tax(req)
    assert r.tax_rate_pct == CIT_STANDARD_RATE_PCT


@pytest.mark.asyncio
async def test_calculate_individual_income_threshold():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(tax_type="individual_income", revenue=100_000)
    r = await p.calculate_tax(req)
    # 应纳税 = 100000 - 60000 = 40000 → 落在 36000-144000 档（10%）
    # 40000 × 10% - 2520 = 1480
    assert r.tax_payable == pytest.approx(1_480.0, abs=1.0)


@pytest.mark.asyncio
async def test_calculate_stamp_tax():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(tax_type="stamp", revenue=1_000_000)
    r = await p.calculate_tax(req)
    # 100 万 × 万分之三 = 300
    assert r.tax_payable == pytest.approx(300.0, abs=0.01)


@pytest.mark.asyncio
async def test_calculate_consumption_tax():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(tax_type="consumption", revenue=2_000_000)
    r = await p.calculate_tax(req)
    assert r.tax_payable > 0
    assert r.tax_type == "consumption"


@pytest.mark.asyncio
async def test_calculate_tax_invalid_type():
    p = TaxFinanceAdvisorPersona()
    req = TaxCalculationRequest(tax_type="unknown_tax", revenue=100)
    with pytest.raises(ValueError, match="不支持"):
        await p.calculate_tax(req)


# ---------------------------------------------------------------------------
# 2. export_tax_rebate
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_export_rebate_basic():
    p = TaxFinanceAdvisorPersona()
    exports = [
        ExportTransaction(
            invoice_no="EXP001",
            product_code="P001",
            hs_code="8471300000",  # 84 章机电
            quantity=100,
            unit_price_usd=50.0,
            fob_total_usd=5000.0,
            customs_declaration_no="CD2025001",
            export_date=date(2025, 6, 1),
        )
    ]
    r = await p.export_tax_rebate(exports)
    assert isinstance(r, RebateReport)
    # 5000 USD × 7.10 × 13% = 4615 CNY
    assert r.eligible_rebate_amount_cny == pytest.approx(4615.0, rel=0.01)
    assert r.rebate_rate_pct == pytest.approx(13.0, abs=0.01)
    assert "出口货物报关单" in r.required_documents
    assert r.expected_filing_date == date(2025, 7, 15)


@pytest.mark.asyncio
async def test_export_rebate_empty_raises():
    p = TaxFinanceAdvisorPersona()
    with pytest.raises(ValueError, match="不能为空"):
        await p.export_tax_rebate([])


@pytest.mark.asyncio
async def test_export_rebate_missing_customs_flagged():
    p = TaxFinanceAdvisorPersona()
    tx = ExportTransaction(
        invoice_no="EXP002",
        product_code="P002",
        hs_code="8471300000",
        quantity=10,
        unit_price_usd=100,
        fob_total_usd=1000,
        customs_declaration_no="",  # 缺
        export_date=date(2025, 5, 1),
    )
    r = await p.export_tax_rebate([tx])
    assert any("报关单" in flag for flag in r.risks)


# ---------------------------------------------------------------------------
# 3. cross_border_vat_guidance
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cross_border_vat_germany_b2c_oss():
    p = TaxFinanceAdvisorPersona()
    advice = await p.cross_border_vat_guidance(
        country="德国",
        scenario="独立站 B2C",
        amount=20_000.0,  # > €10000 阈值
        currency="EUR",
    )
    assert isinstance(advice, VATAdvice)
    assert advice.vat_rate_pct == 19.0
    assert advice.vat_payable == pytest.approx(20_000 * 0.19, abs=0.01)
    assert advice.needs_oss_registration is True  # EU + B2C + 超阈值
    assert advice.disclaimer
    assert "不构成专业" in advice.disclaimer


@pytest.mark.asyncio
async def test_cross_border_vat_uk_not_eu_oss():
    p = TaxFinanceAdvisorPersona()
    advice = await p.cross_border_vat_guidance(
        country="UK", scenario="独立站", amount=50_000, currency="GBP"
    )
    assert advice.vat_rate_pct == 20.0
    assert advice.needs_oss_registration is False  # UK 已脱欧


@pytest.mark.asyncio
async def test_cross_border_vat_us_sales_tax_path():
    p = TaxFinanceAdvisorPersona()
    advice = await p.cross_border_vat_guidance(
        country="美国", scenario="海外仓直发", amount=100_000, currency="USD"
    )
    assert advice.vat_rate_pct == 0.0  # 美国无联邦 VAT
    assert any("nexus" in s.lower() for s in advice.recommended_steps)


@pytest.mark.asyncio
async def test_cross_border_vat_unknown_country_safe_default():
    p = TaxFinanceAdvisorPersona()
    advice = await p.cross_border_vat_guidance(
        country="不存在国", scenario="B2B", amount=1000, currency="EUR"
    )
    assert advice.disclaimer  # 兜底仍带 disclaimer


@pytest.mark.asyncio
async def test_cross_border_vat_negative_amount_raises():
    p = TaxFinanceAdvisorPersona()
    with pytest.raises(ValueError):
        await p.cross_border_vat_guidance("德国", "B2C", -100, "EUR")


# ---------------------------------------------------------------------------
# 4. analyze_financial_report
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analyze_report_text_red_flags():
    p = TaxFinanceAdvisorPersona()
    text = "公司收入增长，但应收账款暴增，经营性现金流为负，存货积压"
    r = await p.analyze_financial_report(text)
    assert isinstance(r, FinancialAnalysis)
    assert len(r.red_flags) >= 2
    assert r.overall_health_score < 75  # 至少 2 个 red_flag → 减分


@pytest.mark.asyncio
async def test_analyze_report_text_opportunities():
    p = TaxFinanceAdvisorPersona()
    text = "公司主要从事制造业，研发投入占比 8%，部分产品出口"
    r = await p.analyze_financial_report(text)
    assert any("研发" in o for o in r.opportunities)
    assert any("出口" in o for o in r.opportunities)


@pytest.mark.asyncio
async def test_analyze_report_excel_path_branch():
    p = TaxFinanceAdvisorPersona()
    r = await p.analyze_financial_report("/tmp/q3_2025.xlsx")
    assert "Excel" in r.summary or "财报" in r.summary


# ---------------------------------------------------------------------------
# 5. tax_planning
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tax_planning_high_tech_eligible():
    p = TaxFinanceAdvisorPersona()
    profile = BusinessProfile(
        industry="制造业",
        annual_revenue=100_000_000,
        employees=200,
        is_high_tech=False,
        has_export=True,
    )
    plan = await p.tax_planning(profile, target_year=2026)
    assert isinstance(plan, TaxPlan)
    # 应包含研发加计扣除 + 高新认定 + 出口退税策略
    strategies = [i.strategy for i in plan.items]
    assert any("研发" in s for s in strategies)
    assert any("高新" in s for s in strategies)
    assert any("出口" in s for s in strategies)
    assert plan.savings > 0
    assert plan.disclaimer
    assert "持牌税务师" in plan.disclaimer


@pytest.mark.asyncio
async def test_tax_planning_overseas_subsidiary_high_risk():
    p = TaxFinanceAdvisorPersona()
    profile = BusinessProfile(
        industry="制造业",
        annual_revenue=200_000_000,
        employees=300,
        has_overseas_subsidiary=True,
    )
    plan = await p.tax_planning(profile, target_year=2026)
    # 海外子公司方案必须存在且 risk_level=high
    overseas = [i for i in plan.items if "海外" in i.strategy or "BEPS" in i.description.upper()]
    assert overseas
    assert overseas[0].risk_level == "high"


@pytest.mark.asyncio
async def test_tax_planning_past_year_raises():
    p = TaxFinanceAdvisorPersona()
    profile = BusinessProfile(industry="制造业", annual_revenue=1000, employees=1)
    with pytest.raises(ValueError):
        await p.tax_planning(profile, target_year=2000)


@pytest.mark.asyncio
async def test_tax_planning_legal_basis_present():
    """所有筹划建议必须有法律依据。"""
    p = TaxFinanceAdvisorPersona()
    profile = BusinessProfile(
        industry="制造业",
        annual_revenue=50_000_000,
        employees=100,
        has_export=True,
    )
    plan = await p.tax_planning(profile, target_year=2026)
    for item in plan.items:
        assert item.legal_basis, f"{item.strategy} 缺少法律依据"


# ---------------------------------------------------------------------------
# 6. filing_calendar
# ---------------------------------------------------------------------------
def test_filing_calendar_basic():
    p = TaxFinanceAdvisorPersona()
    cal = p.filing_calendar("CN", 2026)
    assert len(cal) == 12
    # 5 月有汇算清缴
    may = next(m for m in cal if m["month"] == 5)
    assert any("汇算清缴" in d["type"] for d in may["deadlines"])
    # 6 月有个税汇算
    jun = next(m for m in cal if m["month"] == 6)
    assert any("个人所得税" in d["type"] for d in jun["deadlines"])
