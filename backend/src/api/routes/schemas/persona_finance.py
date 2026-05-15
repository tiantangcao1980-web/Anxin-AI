"""财税顾问 persona 路由 Pydantic schemas（P9-E）。

与 ``src/agents/personas/finance_models.py`` 中的 dataclass 一一对应；
设计取舍同 P7-E ``schemas/persona_ecommerce.py``。
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# 通用 Citation 镜像（与 schemas/persona_market.CitationOut 字段一致，但本
# 文件保持独立避免循环 import）
# ---------------------------------------------------------------------------
class CitationOut(BaseModel):
    source: str
    url: str
    title: str = ""
    excerpt: str = ""
    confidence: float = 0.5


# ---------------------------------------------------------------------------
# 1. 税务计算
# ---------------------------------------------------------------------------
_VALID_TAX_TYPES = {
    "vat",
    "corporate_income",
    "individual_income",
    "stamp",
    "consumption",
}


class TaxCalculationIn(BaseModel):
    tax_type: str = Field(
        ..., description="vat / corporate_income / individual_income / stamp / consumption"
    )
    revenue: float | None = None
    expenses: float | None = None
    items: list[dict] = Field(default_factory=list)
    period: str = Field("monthly", description="monthly / quarterly / annual")
    region: str = "CN"
    industry: str | None = None
    special_treatment: list[str] = Field(default_factory=list)

    @field_validator("tax_type")
    @classmethod
    def _check_tax_type(cls, v: str) -> str:
        if v.lower() not in _VALID_TAX_TYPES:
            raise ValueError(f"tax_type 必须是: {', '.join(sorted(_VALID_TAX_TYPES))}")
        return v.lower()

    @field_validator("period")
    @classmethod
    def _check_period(cls, v: str) -> str:
        if v not in {"monthly", "quarterly", "annual"}:
            raise ValueError("period 必须是 monthly / quarterly / annual")
        return v


class TaxCalculationOut(BaseModel):
    tax_type: str
    taxable_amount: float
    tax_rate_pct: float
    tax_payable: float
    deductions: list[dict] = Field(default_factory=list)
    breakdown: dict[str, float] = Field(default_factory=dict)
    legal_basis: list[CitationOut] = Field(default_factory=list)
    payment_deadline: str | None = None
    notes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. 出口退税
# ---------------------------------------------------------------------------
class ExportTransactionIn(BaseModel):
    invoice_no: str = Field(..., min_length=1)
    product_code: str
    hs_code: str
    quantity: int = Field(..., gt=0)
    unit_price_usd: float = Field(..., ge=0)
    fob_total_usd: float = Field(..., ge=0)
    customs_declaration_no: str
    export_date: str = Field(..., description="YYYY-MM-DD")


class ExportRebateIn(BaseModel):
    exports: list[ExportTransactionIn] = Field(..., min_length=1)


class RebateReportOut(BaseModel):
    transactions: list[dict] = Field(default_factory=list)
    eligible_rebate_amount_cny: float
    rebate_rate_pct: float
    expected_filing_date: str
    required_documents: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 3. 跨境 VAT
# ---------------------------------------------------------------------------
class CrossBorderVATIn(BaseModel):
    country: str = Field(..., min_length=1, max_length=50)
    scenario: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., ge=0)
    currency: str = Field("EUR", min_length=3, max_length=10)


class VATAdviceOut(BaseModel):
    country: str
    scenario: str
    transaction_amount: float
    currency: str
    vat_rate_pct: float
    vat_payable: float
    threshold_eur: float
    needs_oss_registration: bool
    needs_local_vat_reg: bool
    filing_frequency: str
    deadline_pattern: str
    recommended_steps: list[str] = Field(default_factory=list)
    disclaimer: str


# ---------------------------------------------------------------------------
# 4. 财报分析
# ---------------------------------------------------------------------------
class AnalyzeReportIn(BaseModel):
    report_text: str | None = Field(None, description="文本财报内容")
    excel_path: str | None = Field(None, description="Excel 财报文件路径")


class FinancialAnalysisOut(BaseModel):
    period: str
    summary: str
    key_metrics: dict[str, float] = Field(default_factory=dict)
    yoy_changes: dict[str, float] = Field(default_factory=dict)
    health_indicators: list[dict] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)
    overall_health_score: float = 0.0


# ---------------------------------------------------------------------------
# 5. 税务筹划
# ---------------------------------------------------------------------------
class BusinessProfileIn(BaseModel):
    industry: str = Field(..., min_length=1)
    annual_revenue: float = Field(..., ge=0)
    employees: int = Field(..., ge=0)
    is_high_tech: bool = False
    is_small_micro: bool = False
    has_export: bool = False
    has_overseas_subsidiary: bool = False


class TaxPlanIn(BaseModel):
    business_profile: BusinessProfileIn
    target_year: int = Field(..., ge=2020, le=2100)


class TaxPlanItemOut(BaseModel):
    strategy: str
    description: str
    estimated_savings: float
    risk_level: str
    legal_basis: list[CitationOut] = Field(default_factory=list)
    implementation_steps: list[str] = Field(default_factory=list)


class TaxPlanOut(BaseModel):
    profile: BusinessProfileIn
    target_year: int
    current_estimated_tax: float
    optimized_estimated_tax: float
    savings: float
    items: list[TaxPlanItemOut] = Field(default_factory=list)
    disclaimer: str


# ---------------------------------------------------------------------------
# 6. 税率查询
# ---------------------------------------------------------------------------
class TaxRatesOut(BaseModel):
    country: str
    tax_type: str
    year: int
    rates: list[dict] = Field(default_factory=list)
    source: str | None = None


# ---------------------------------------------------------------------------
# 7. 报税日历
# ---------------------------------------------------------------------------
class FilingCalendarOut(BaseModel):
    region: str
    year: int
    months: list[dict] = Field(default_factory=list)


__all__ = [
    "CitationOut",
    "TaxCalculationIn",
    "TaxCalculationOut",
    "ExportTransactionIn",
    "ExportRebateIn",
    "RebateReportOut",
    "CrossBorderVATIn",
    "VATAdviceOut",
    "AnalyzeReportIn",
    "FinancialAnalysisOut",
    "BusinessProfileIn",
    "TaxPlanIn",
    "TaxPlanItemOut",
    "TaxPlanOut",
    "TaxRatesOut",
    "FilingCalendarOut",
]
