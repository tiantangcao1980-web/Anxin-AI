# -*- coding: utf-8 -*-
"""跨境电商助手 persona 路由（P7-E）。

挂载点（在 ``api/routes/__init__.py`` 用 ``prefix="/personas/ecommerce"`` 注册）::

    POST   /api/v1/personas/ecommerce/analyze-niche
    POST   /api/v1/personas/ecommerce/verify-supplier
    POST   /api/v1/personas/ecommerce/negotiate
    POST   /api/v1/personas/ecommerce/setup-store
    POST   /api/v1/personas/ecommerce/list-to-platforms
    POST   /api/v1/personas/ecommerce/vat-guidance
    GET    /api/v1/personas/ecommerce/dashboard

权限：所有路由都需要登录用户（与现有 fetch / skills 一致）。
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from src.agents.personas.ecommerce_assistant import EcommerceAssistantAgent
from src.agents.personas.ecommerce_models import ProductSpec
from src.api.routes.schemas.persona_ecommerce import (
    AnalyzeNicheIn,
    DashboardOut,
    ListToPlatformsIn,
    ListToPlatformsOut,
    NegotiateIn,
    NegotiationMoveOut,
    NicheReportOut,
    SetupStoreIn,
    SetupStoreOut,
    SupplierVerificationOut,
    VATGuidanceIn,
    VATGuidanceOut,
    VerifySupplierIn,
)
from src.core.deps import get_current_user_required
from src.models.user import User

router = APIRouter()


# ---------------------------------------------------------------------------
# Persona 单例（无副作用，可线程安全共享）
# ---------------------------------------------------------------------------
_PERSONA = EcommerceAssistantAgent()


def _get_persona() -> EcommerceAssistantAgent:
    """依赖注入入口；测试可通过 ``app.dependency_overrides`` 替换。"""
    return _PERSONA


# ---------------------------------------------------------------------------
# 1. analyze-niche
# ---------------------------------------------------------------------------
@router.post(
    "/analyze-niche",
    response_model=NicheReportOut,
    summary="选品分析（细分赛道 / 竞品 / 利润测算）",
)
async def analyze_niche(
    payload: AnalyzeNicheIn,
    persona: EcommerceAssistantAgent = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001 — 仅鉴权
) -> NicheReportOut:
    report = await persona.analyze_niche(payload.niche, payload.target_markets)
    return NicheReportOut(
        niche=report.niche,
        market_size_usd=report.market_size_usd,
        growth_rate_pct=report.growth_rate_pct,
        competition_level=report.competition_level,
        avg_price_band=list(report.avg_price_band),
        profit_margin_estimate_pct=report.profit_margin_estimate_pct,
        top_competitors=report.top_competitors,
        seasonal_pattern=report.seasonal_pattern,
        recommended_action=report.recommended_action,
        rationale=report.rationale,
        citations=report.citations,
    )


# ---------------------------------------------------------------------------
# 2. verify-supplier
# ---------------------------------------------------------------------------
@router.post(
    "/verify-supplier",
    response_model=SupplierVerificationOut,
    summary="供应商验真（资质 / 信用 / 出货能力）",
)
async def verify_supplier(
    payload: VerifySupplierIn,
    persona: EcommerceAssistantAgent = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> SupplierVerificationOut:
    result = await persona.verify_supplier(payload.supplier_id_or_url, payload.source)
    return SupplierVerificationOut(
        supplier_id=result.supplier_id,
        name=result.name,
        business_license_verified=result.business_license_verified,
        factory_audit_grade=result.factory_audit_grade,
        years_in_business=result.years_in_business,
        moq=result.moq,
        capacity_per_month=result.capacity_per_month,
        customs_records_count=result.customs_records_count,
        risk_flags=result.risk_flags,
        recommendation=result.recommendation,
    )


# ---------------------------------------------------------------------------
# 3. negotiate
# ---------------------------------------------------------------------------
@router.post(
    "/negotiate",
    response_model=NegotiationMoveOut,
    summary="AI 议价（多轮策略：anchor / concede / trade / walk_away）",
)
async def negotiate(
    payload: NegotiateIn,
    persona: EcommerceAssistantAgent = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> NegotiationMoveOut:
    try:
        move = await persona.negotiate(
            target_price=payload.target_price,
            mood=payload.mood,
            history=payload.history,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return NegotiationMoveOut(
        move_type=move.move_type,
        proposed_price=move.proposed_price,
        proposed_terms=move.proposed_terms,
        script_text=move.script_text,
        rationale=move.rationale,
        expected_supplier_reaction=move.expected_supplier_reaction,
        bottom_line_distance_pct=move.bottom_line_distance_pct,
    )


# ---------------------------------------------------------------------------
# 4. setup-store
# ---------------------------------------------------------------------------
@router.post(
    "/setup-store",
    response_model=SetupStoreOut,
    summary="独立站搭建（Shopify 主题 + 选品上架）",
)
async def setup_store(
    payload: SetupStoreIn,
    persona: EcommerceAssistantAgent = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> SetupStoreOut:
    result = await persona.setup_shopify_store(
        oauth_token=payload.oauth_token,
        theme=payload.theme,
        products=payload.products,
    )
    return SetupStoreOut(**result)


# ---------------------------------------------------------------------------
# 5. list-to-platforms
# ---------------------------------------------------------------------------
@router.post(
    "/list-to-platforms",
    response_model=ListToPlatformsOut,
    summary="多平台铺货（一品多平台 + 标题/描述翻译）",
)
async def list_to_platforms(
    payload: ListToPlatformsIn,
    persona: EcommerceAssistantAgent = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> ListToPlatformsOut:
    spec_in = payload.product
    dim = spec_in.dimensions_cm
    if len(dim) != 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="dimensions_cm 必须是 [length, width, height] 三元数组",
        )
    spec = ProductSpec(
        sku=spec_in.sku,
        title=spec_in.title,
        description=spec_in.description,
        price=spec_in.price,
        currency=spec_in.currency,
        images=spec_in.images,
        weight_g=spec_in.weight_g,
        dimensions_cm=(dim[0], dim[1], dim[2]),
        hs_code=spec_in.hs_code,
        origin_country=spec_in.origin_country,
    )
    result = await persona.list_to_platforms(
        product=spec,
        platforms=payload.platforms,
        languages=payload.languages,
    )
    return ListToPlatformsOut(**result)


# ---------------------------------------------------------------------------
# 6. vat-guidance
# ---------------------------------------------------------------------------
@router.post(
    "/vat-guidance",
    response_model=VATGuidanceOut,
    summary="VAT 跨境合规指引（带专业税务师 disclaimer）",
)
async def vat_guidance(
    payload: VATGuidanceIn,
    persona: EcommerceAssistantAgent = Depends(_get_persona),
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> VATGuidanceOut:
    g = await persona.vat_guidance(payload.country, payload.scenario)
    return VATGuidanceOut(
        country=g.country,
        vat_rate_pct=g.vat_rate_pct,
        threshold_eur=g.threshold_eur,
        registration_required=g.registration_required,
        filing_frequency=g.filing_frequency,
        deadline_pattern=g.deadline_pattern,
        recommended_steps=g.recommended_steps,
        forms_to_prepare=g.forms_to_prepare,
        disclaimer=g.disclaimer,
    )


# ---------------------------------------------------------------------------
# 7. dashboard
# ---------------------------------------------------------------------------
@router.get(
    "/dashboard",
    response_model=DashboardOut,
    summary="跨境电商运营 dashboard（在售品 / 订单 / 库存 / 物流）",
)
async def dashboard(
    persona: EcommerceAssistantAgent = Depends(_get_persona),  # noqa: ARG001
    user: User = Depends(get_current_user_required),  # noqa: ARG001
) -> DashboardOut:
    """汇总 5 个 source 的近 30 天数据；P7-E 阶段返回 mock。"""
    return DashboardOut(
        persona_id="ecommerce_assistant",
        listings_active=128,
        orders_pending=12,
        orders_in_transit=37,
        inventory_low_count=4,
        revenue_30d_usd=84_320.50,
        by_platform=[
            {"platform": "shopify", "listings": 52, "orders_30d": 88, "revenue_usd": 38_240.00},
            {"platform": "amazon_sp", "listings": 31, "orders_30d": 64, "revenue_usd": 27_810.50},
            {"platform": "alibaba_1688", "listings": 18, "orders_30d": 9, "revenue_usd": 12_650.00},
            {"platform": "shopee", "listings": 15, "orders_30d": 22, "revenue_usd": 3_980.00},
            {"platform": "tiktok_shop", "listings": 12, "orders_30d": 18, "revenue_usd": 1_640.00},
        ],
        last_updated=datetime.now(timezone.utc).isoformat(),
    )
