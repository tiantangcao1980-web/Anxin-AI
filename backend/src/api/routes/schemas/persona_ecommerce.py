"""跨境电商助手 persona 路由 Pydantic schemas（P7-E）。

与 ``src/agents/personas/ecommerce_models.py`` 中的 dataclass 一一对应，
但 API 层用 pydantic 是因为：
1. FastAPI 自动 OpenAPI / Swagger UI / 校验。
2. 对外字段（如 ``avg_price_band`` 用 list[float] 而非 tuple）更易 JSON 化。
3. 业务字段可在此叠加校验（``mood`` 限 enum、``country`` 长度限 50 等）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# 1. analyze-niche
# ---------------------------------------------------------------------------
class AnalyzeNicheIn(BaseModel):
    niche: str = Field(..., min_length=1, max_length=200, description="细分品类名")
    target_markets: list[str] = Field(default_factory=list, description="国家代码")


class CompetitorOut(BaseModel):
    asin: str | None = None
    monthly_sales_est: int | None = None
    price_usd: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class CitationOut(BaseModel):
    source: str
    url: str
    snippet: str | None = None


class NicheReportOut(BaseModel):
    niche: str
    market_size_usd: float
    growth_rate_pct: float
    competition_level: str
    avg_price_band: list[float]  # tuple → list 利于 JSON
    profit_margin_estimate_pct: float
    top_competitors: list[dict]
    seasonal_pattern: str
    recommended_action: str
    rationale: str
    citations: list[CitationOut] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. verify-supplier
# ---------------------------------------------------------------------------
class VerifySupplierIn(BaseModel):
    supplier_id_or_url: str = Field(..., min_length=1, max_length=500)
    source: str = "alibaba_1688"


class SupplierVerificationOut(BaseModel):
    supplier_id: str
    name: str
    business_license_verified: bool
    factory_audit_grade: str | None = None
    years_in_business: int | None = None
    moq: int
    capacity_per_month: int | None = None
    customs_records_count: int
    risk_flags: list[str] = Field(default_factory=list)
    recommendation: str


# ---------------------------------------------------------------------------
# 3. negotiate
# ---------------------------------------------------------------------------
class NegotiateIn(BaseModel):
    target_price: float = Field(..., gt=0)
    mood: str = Field(..., description="aggressive | moderate | friendly")
    history: list[dict] = Field(default_factory=list)

    @field_validator("mood")
    @classmethod
    def _check_mood(cls, v: str) -> str:
        if v not in {"aggressive", "moderate", "friendly"}:
            raise ValueError("mood 必须是 aggressive / moderate / friendly")
        return v


class NegotiationMoveOut(BaseModel):
    move_type: str
    proposed_price: float
    proposed_terms: dict
    script_text: str
    rationale: str
    expected_supplier_reaction: str
    bottom_line_distance_pct: float


# ---------------------------------------------------------------------------
# 4. setup-store
# ---------------------------------------------------------------------------
class SetupStoreIn(BaseModel):
    oauth_token: str = Field(..., min_length=1)
    theme: str = Field("dawn", max_length=50)
    products: list[dict] = Field(default_factory=list)


class SetupStoreOut(BaseModel):
    ok: bool
    store_url: str | None = None
    installed_theme: str | None = None
    products_created: int = 0
    next_steps: list[str] = Field(default_factory=list)
    error: str | None = None
    hint: str | None = None


# ---------------------------------------------------------------------------
# 5. list-to-platforms
# ---------------------------------------------------------------------------
class ProductSpecIn(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    title: dict[str, str] = Field(default_factory=dict)
    description: dict[str, str] = Field(default_factory=dict)
    price: float = Field(..., gt=0)
    currency: str = "USD"
    images: list[str] = Field(default_factory=list)
    weight_g: float = 0
    dimensions_cm: list[float] = Field(default_factory=lambda: [0, 0, 0])
    hs_code: str | None = None
    origin_country: str = "CN"


class ListToPlatformsIn(BaseModel):
    product: ProductSpecIn
    platforms: list[str] = Field(..., min_length=1)
    languages: list[str] = Field(..., min_length=1)


class ListToPlatformsOut(BaseModel):
    ok: bool
    sku: str | None = None
    total: int = 0
    results: list[dict] = Field(default_factory=list)
    delegated_to: list[str] = Field(default_factory=list)
    error: str | None = None
    invalid: list[str] | None = None
    hint: str | None = None


# ---------------------------------------------------------------------------
# 6. vat-guidance
# ---------------------------------------------------------------------------
class VATGuidanceIn(BaseModel):
    country: str = Field(..., min_length=1, max_length=50)
    scenario: str = Field(..., min_length=1, max_length=500)


class VATGuidanceOut(BaseModel):
    country: str
    vat_rate_pct: float
    threshold_eur: float
    registration_required: bool
    filing_frequency: str
    deadline_pattern: str
    recommended_steps: list[str]
    forms_to_prepare: list[str]
    disclaimer: str


# ---------------------------------------------------------------------------
# 7. dashboard
# ---------------------------------------------------------------------------
class DashboardOut(BaseModel):
    """跨境电商运营 dashboard 汇总。

    P7-E 阶段返回 mock；P8 后由 P6-D 5 source 真实聚合。
    """

    persona_id: str = "ecommerce_assistant"
    listings_active: int = 0
    orders_pending: int = 0
    orders_in_transit: int = 0
    inventory_low_count: int = 0
    revenue_30d_usd: float = 0.0
    by_platform: list[dict] = Field(default_factory=list)
    last_updated: str | None = None


__all__ = [
    "AnalyzeNicheIn",
    "NicheReportOut",
    "CompetitorOut",
    "CitationOut",
    "VerifySupplierIn",
    "SupplierVerificationOut",
    "NegotiateIn",
    "NegotiationMoveOut",
    "SetupStoreIn",
    "SetupStoreOut",
    "ProductSpecIn",
    "ListToPlatformsIn",
    "ListToPlatformsOut",
    "VATGuidanceIn",
    "VATGuidanceOut",
    "DashboardOut",
]
