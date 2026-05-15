"""财税顾问 persona 路由（P9-E）。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/finance"`` 注册）::

    POST   /api/v1/personas/finance/calculate-tax        税务计算（5 税种）
    POST   /api/v1/personas/finance/export-rebate        出口退税
    POST   /api/v1/personas/finance/cross-border-vat     跨境 VAT 决策建议
    POST   /api/v1/personas/finance/analyze-report       财报分析（文本 / Excel 路径）
    POST   /api/v1/personas/finance/tax-plan             年度税务筹划
    GET    /api/v1/personas/finance/tax-rates            税率查询
    GET    /api/v1/personas/finance/calendar             报税日历

权限：所有路由都需要登录用户（与 P7-E persona_ecommerce 一致）。
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.agents.personas.finance_models import (
    BusinessProfile,
    ExportTransaction,
    TaxCalculationRequest,
)
from src.agents.personas.tax_finance_advisor import (
    EXPORT_REBATE_RATES_PCT,
    TaxFinanceAdvisorPersona,
)
from src.api.routes.schemas.persona_finance import (
    AnalyzeReportIn,
    CitationOut,
    CrossBorderVATIn,
    ExportRebateIn,
    FilingCalendarOut,
    FinancialAnalysisOut,
    RebateReportOut,
    TaxCalculationIn,
    TaxCalculationOut,
    TaxPlanIn,
    TaxPlanItemOut,
    TaxPlanOut,
    TaxRatesOut,
    VATAdviceOut,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Persona 单例（无副作用，可线程安全共享）
# ---------------------------------------------------------------------------
_PERSONA: TaxFinanceAdvisorPersona | None = None


def _get_persona() -> TaxFinanceAdvisorPersona:
    """依赖注入入口；测试可通过 ``app.dependency_overrides`` 替换。"""
    global _PERSONA
    if _PERSONA is None:
        _PERSONA = TaxFinanceAdvisorPersona()
    return _PERSONA


def _to_citation_out(citations) -> list[CitationOut]:
    return [
        CitationOut(
            source=c.source,
            url=c.url,
            title=c.title,
            excerpt=c.excerpt,
            confidence=c.confidence,
        )
        for c in citations
    ]


# ---------------------------------------------------------------------------
# 1. calculate-tax
# ---------------------------------------------------------------------------
@router.post(
    "/calculate-tax",
    response_model=TaxCalculationOut,
    summary="税务计算（增值税 / 企业所得税 / 个税 / 印花税 / 消费税）",
)
async def calculate_tax(
    payload: TaxCalculationIn,
    persona: TaxFinanceAdvisorPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> TaxCalculationOut:
    request = TaxCalculationRequest(
        tax_type=payload.tax_type,
        revenue=payload.revenue,
        expenses=payload.expenses,
        items=payload.items,
        period=payload.period,
        region=payload.region,
        industry=payload.industry,
        special_treatment=payload.special_treatment,
    )
    try:
        result = await persona.calculate_tax(request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return TaxCalculationOut(
        tax_type=result.tax_type,
        taxable_amount=result.taxable_amount,
        tax_rate_pct=result.tax_rate_pct,
        tax_payable=result.tax_payable,
        deductions=result.deductions,
        breakdown=result.breakdown,
        legal_basis=_to_citation_out(result.legal_basis),
        payment_deadline=result.payment_deadline.isoformat() if result.payment_deadline else None,
        notes=result.notes,
    )


# ---------------------------------------------------------------------------
# 2. export-rebate
# ---------------------------------------------------------------------------
@router.post(
    "/export-rebate",
    response_model=RebateReportOut,
    summary="出口退税计算（含申报材料 + 风险提示）",
)
async def export_rebate(
    payload: ExportRebateIn,
    persona: TaxFinanceAdvisorPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> RebateReportOut:
    transactions: list[ExportTransaction] = []
    for tx in payload.exports:
        try:
            export_date = date.fromisoformat(tx.export_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"export_date 格式错误（需 YYYY-MM-DD）: {tx.export_date}",
            ) from exc
        transactions.append(
            ExportTransaction(
                invoice_no=tx.invoice_no,
                product_code=tx.product_code,
                hs_code=tx.hs_code,
                quantity=tx.quantity,
                unit_price_usd=tx.unit_price_usd,
                fob_total_usd=tx.fob_total_usd,
                customs_declaration_no=tx.customs_declaration_no,
                export_date=export_date,
            )
        )

    try:
        report = await persona.export_tax_rebate(transactions)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return RebateReportOut(
        transactions=[
            {
                "invoice_no": tx.invoice_no,
                "product_code": tx.product_code,
                "hs_code": tx.hs_code,
                "quantity": tx.quantity,
                "unit_price_usd": tx.unit_price_usd,
                "fob_total_usd": tx.fob_total_usd,
                "customs_declaration_no": tx.customs_declaration_no,
                "export_date": tx.export_date.isoformat(),
            }
            for tx in report.transactions
        ],
        eligible_rebate_amount_cny=report.eligible_rebate_amount_cny,
        rebate_rate_pct=report.rebate_rate_pct,
        expected_filing_date=report.expected_filing_date.isoformat(),
        required_documents=report.required_documents,
        risks=report.risks,
    )


# ---------------------------------------------------------------------------
# 3. cross-border-vat
# ---------------------------------------------------------------------------
@router.post(
    "/cross-border-vat",
    response_model=VATAdviceOut,
    summary="跨境 VAT 决策建议（应缴预测 + OSS 判断）",
)
async def cross_border_vat(
    payload: CrossBorderVATIn,
    persona: TaxFinanceAdvisorPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> VATAdviceOut:
    try:
        advice = await persona.cross_border_vat_guidance(
            country=payload.country,
            scenario=payload.scenario,
            amount=payload.amount,
            currency=payload.currency,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return VATAdviceOut(
        country=advice.country,
        scenario=advice.scenario,
        transaction_amount=advice.transaction_amount,
        currency=advice.currency,
        vat_rate_pct=advice.vat_rate_pct,
        vat_payable=advice.vat_payable,
        threshold_eur=advice.threshold_eur,
        needs_oss_registration=advice.needs_oss_registration,
        needs_local_vat_reg=advice.needs_local_vat_reg,
        filing_frequency=advice.filing_frequency,
        deadline_pattern=advice.deadline_pattern,
        recommended_steps=advice.recommended_steps,
        disclaimer=advice.disclaimer,
    )


# ---------------------------------------------------------------------------
# 4. analyze-report
# ---------------------------------------------------------------------------
@router.post(
    "/analyze-report",
    response_model=FinancialAnalysisOut,
    summary="财报分析（文本 / Excel 路径）",
)
async def analyze_report(
    payload: AnalyzeReportIn,
    persona: TaxFinanceAdvisorPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> FinancialAnalysisOut:
    text = payload.report_text or payload.excel_path
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="必须提供 report_text 或 excel_path 之一",
        )

    analysis = await persona.analyze_financial_report(text)
    return FinancialAnalysisOut(
        period=analysis.period,
        summary=analysis.summary,
        key_metrics=analysis.key_metrics,
        yoy_changes=analysis.yoy_changes,
        health_indicators=analysis.health_indicators,
        red_flags=analysis.red_flags,
        opportunities=analysis.opportunities,
        overall_health_score=analysis.overall_health_score,
    )


# ---------------------------------------------------------------------------
# 5. tax-plan
# ---------------------------------------------------------------------------
@router.post(
    "/tax-plan",
    response_model=TaxPlanOut,
    summary="年度税务筹划（含 disclaimer）",
)
async def tax_plan(
    payload: TaxPlanIn,
    persona: TaxFinanceAdvisorPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> TaxPlanOut:
    profile = BusinessProfile(
        industry=payload.business_profile.industry,
        annual_revenue=payload.business_profile.annual_revenue,
        employees=payload.business_profile.employees,
        is_high_tech=payload.business_profile.is_high_tech,
        is_small_micro=payload.business_profile.is_small_micro,
        has_export=payload.business_profile.has_export,
        has_overseas_subsidiary=payload.business_profile.has_overseas_subsidiary,
    )
    try:
        plan = await persona.tax_planning(profile, payload.target_year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    items_out = [
        TaxPlanItemOut(
            strategy=i.strategy,
            description=i.description,
            estimated_savings=i.estimated_savings,
            risk_level=i.risk_level,
            legal_basis=_to_citation_out(i.legal_basis),
            implementation_steps=i.implementation_steps,
        )
        for i in plan.items
    ]
    return TaxPlanOut(
        profile=payload.business_profile,
        target_year=plan.target_year,
        current_estimated_tax=plan.current_estimated_tax,
        optimized_estimated_tax=plan.optimized_estimated_tax,
        savings=plan.savings,
        items=items_out,
        disclaimer=plan.disclaimer,
    )


# ---------------------------------------------------------------------------
# 6. tax-rates
# ---------------------------------------------------------------------------
@router.get(
    "/tax-rates",
    response_model=TaxRatesOut,
    summary="税率查询（按国家 / 税种 / 年份）",
)
async def tax_rates(
    country: str = Query(..., min_length=2, max_length=50),
    tax_type: str = Query(..., min_length=1, max_length=50),
    year: int = Query(..., ge=2000, le=2100),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> TaxRatesOut:
    """返回指定国家 / 税种的税率档位列表。

    P9-E mock：返回中国境内增值税 / 所得税 / 退税档位三档；P10+ 接入官方
    税务总局 API。
    """
    country_norm = country.strip().upper()
    tax_type_norm = tax_type.lower().strip()

    if country_norm in {"CN", "CHINA", "中国"}:
        if tax_type_norm == "vat":
            rates = [
                {"category": "销售货物 / 加工修理修配劳务", "rate_pct": 13.0},
                {"category": "运输 / 邮政 / 基础电信 / 建筑 / 不动产", "rate_pct": 9.0},
                {"category": "现代服务 / 生活服务", "rate_pct": 6.0},
                {"category": "小规模纳税人征收率", "rate_pct": 3.0},
            ]
        elif tax_type_norm == "corporate_income":
            rates = [
                {"category": "法定标准税率", "rate_pct": 25.0},
                {"category": "高新技术企业", "rate_pct": 15.0},
                {"category": "小型微利企业（实际综合）", "rate_pct": 5.0},
            ]
        elif tax_type_norm == "export_rebate":
            rates = [
                {"hs_chapter": chapter, "rate_pct": rate}
                for chapter, rate in EXPORT_REBATE_RATES_PCT.items()
                if chapter != "default"
            ]
        else:
            rates = []
    elif country_norm in {"DE", "GERMANY", "德国"}:
        rates = [
            {"category": "Standard VAT", "rate_pct": 19.0},
            {"category": "Reduced", "rate_pct": 7.0},
        ]
    elif country_norm in {"UK", "ENGLAND", "英国"}:
        rates = [
            {"category": "Standard VAT", "rate_pct": 20.0},
            {"category": "Reduced", "rate_pct": 5.0},
        ]
    else:
        rates = []

    return TaxRatesOut(
        country=country,
        tax_type=tax_type_norm,
        year=year,
        rates=rates,
        source="China State Taxation Administration (mock)",
    )


# ---------------------------------------------------------------------------
# 7. calendar
# ---------------------------------------------------------------------------
@router.get(
    "/calendar",
    response_model=FilingCalendarOut,
    summary="报税日历（按月）",
)
async def filing_calendar(
    region: str = Query("CN", min_length=2, max_length=10),
    year: int = Query(..., ge=2000, le=2100),
    persona: TaxFinanceAdvisorPersona = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> FilingCalendarOut:
    months = persona.filing_calendar(region, year)
    return FilingCalendarOut(region=region, year=year, months=months)
