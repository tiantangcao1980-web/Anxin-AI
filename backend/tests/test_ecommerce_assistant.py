"""跨境电商助手 6 大能力单元测试（P7-E）。

覆盖：
    1. analyze_niche  — red_ocean / emerging / unknown 三分支
    2. verify_supplier — trust / avoid 二分支
    3. negotiate       — 见 test_ai_bargaining.py（专门覆盖）
    4. setup_shopify_store — 缺 token / 正常路径
    5. list_to_platforms   — 不支持平台 / 多语言任务派发
    6. vat_guidance        — DE / US / 未知国家 + disclaimer 强制
    7. SYSTEM_PROMPT / class metadata 一致性
"""

from __future__ import annotations

import pytest

# SQLite JSONB 兼容（与 test_ecommerce_base.py 同款）
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


from src.agents.personas.ecommerce_assistant import EcommerceAssistantAgent  # noqa: E402
from src.agents.personas.ecommerce_models import (  # noqa: E402
    NicheReport,
    ProductSpec,
    SupplierVerification,
    VATGuidance,
)


# ---------------------------------------------------------------------------
# 元数据一致性
# ---------------------------------------------------------------------------
def test_persona_metadata():
    p = EcommerceAssistantAgent()
    assert p.persona_id == "ecommerce_assistant"
    assert p.display_name == "跨境电商助手"
    assert p.emoji == "🌍"
    assert "xlsx" in p.backed_by_skills and "pptx" in p.backed_by_skills
    assert set(p.supported_apps) == {
        "shopify",
        "amazon_sp",
        "alibaba_1688",
        "shopee",
        "tiktok_shop",
    }
    # 6 个核心能力齐全
    assert len(p.capabilities) == 6
    for cap in (
        "product_sourcing_analysis",
        "supplier_verification",
        "ai_bargaining",
        "store_setup",
        "multi_platform_listing",
        "vat_compliance",
    ):
        assert cap in p.capabilities
    assert "数据驱动" in p.SYSTEM_PROMPT
    assert "VAT" in p.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# 1. analyze_niche
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analyze_niche_red_ocean():
    p = EcommerceAssistantAgent()
    r = await p.analyze_niche("瑜伽垫", ["US", "DE"])
    assert isinstance(r, NicheReport)
    assert r.niche == "瑜伽垫"
    assert r.recommended_action == "wait"
    assert r.competition_level == "high"
    assert r.profit_margin_estimate_pct < 15
    assert len(r.citations) >= 2  # 至少 2 条数据来源
    # 价格带是 (min, max) tuple
    assert r.avg_price_band[0] < r.avg_price_band[1]


@pytest.mark.asyncio
async def test_analyze_niche_emerging_differentiated():
    p = EcommerceAssistantAgent()
    r = await p.analyze_niche("碳纤维便携桌", ["US"])
    assert r.recommended_action == "enter"
    assert r.profit_margin_estimate_pct > 15


@pytest.mark.asyncio
async def test_analyze_niche_unknown_keyword_waits():
    p = EcommerceAssistantAgent()
    r = await p.analyze_niche("XYZ-未知品", [])
    assert r.recommended_action == "wait"
    # rationale 必须解释为什么观望
    assert len(r.rationale) > 5


# ---------------------------------------------------------------------------
# 2. verify_supplier
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_verify_supplier_trust():
    p = EcommerceAssistantAgent()
    r = await p.verify_supplier("1688:SH123456")
    assert isinstance(r, SupplierVerification)
    assert r.recommendation == "trust"
    assert r.business_license_verified is True
    assert r.factory_audit_grade in {"A", "B", "C"}
    assert r.customs_records_count > 0
    assert r.risk_flags == []


@pytest.mark.asyncio
async def test_verify_supplier_avoid_for_demo_keyword():
    p = EcommerceAssistantAgent()
    r = await p.verify_supplier("https://detail.1688.com/test-supplier")
    assert r.recommendation == "avoid"
    assert "recently_registered" in r.risk_flags
    assert r.factory_audit_grade is None


# ---------------------------------------------------------------------------
# 4. setup_shopify_store
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_setup_store_missing_oauth():
    p = EcommerceAssistantAgent()
    out = await p.setup_shopify_store(oauth_token="", theme="dawn", products=[])
    assert out["ok"] is False
    assert out["error"] == "missing_oauth_token"
    assert "应用授权" in out["hint"]


@pytest.mark.asyncio
async def test_setup_store_happy_path():
    p = EcommerceAssistantAgent()
    out = await p.setup_shopify_store(
        oauth_token="shpca_FAKE_TOKEN",
        theme="refresh",
        products=[{"sku": "A001"}, {"sku": "A002"}],
    )
    assert out["ok"] is True
    assert out["installed_theme"] == "refresh"
    assert out["products_created"] == 2
    assert out["store_url"].startswith("https://")
    assert any("Stripe" in s for s in out["next_steps"])


# ---------------------------------------------------------------------------
# 5. list_to_platforms
# ---------------------------------------------------------------------------
def _spec() -> ProductSpec:
    return ProductSpec(
        sku="SKU-001",
        title={"zh": "智能水杯", "en": "Smart Bottle"},
        description={"zh": "保温 12 小时", "en": "Keeps cold 12h"},
        price=29.99,
        currency="USD",
        images=["https://cdn.example.com/1.jpg"],
        weight_g=350,
        dimensions_cm=(8.0, 8.0, 22.0),
        hs_code="3924100000",
        origin_country="CN",
    )


@pytest.mark.asyncio
async def test_list_to_platforms_invalid_platform_rejected():
    p = EcommerceAssistantAgent()
    out = await p.list_to_platforms(
        product=_spec(),
        platforms=["shopify", "ebay"],  # ebay 不支持
        languages=["en"],
    )
    assert out["ok"] is False
    assert out["error"] == "unsupported_platforms"
    assert out["invalid"] == ["ebay"]


@pytest.mark.asyncio
async def test_list_to_platforms_multi_lang_delegates_to_content_director():
    p = EcommerceAssistantAgent()
    out = await p.list_to_platforms(
        product=_spec(),
        platforms=["shopify", "amazon_sp"],
        languages=["en", "ja"],
    )
    assert out["ok"] is True
    assert out["sku"] == "SKU-001"
    # 2 平台 × 2 语言 = 4 个上架任务
    assert out["total"] == 4
    # 多语言时必须委派内容总监 persona
    assert "content_director_persona" in out["delegated_to"]


@pytest.mark.asyncio
async def test_list_to_platforms_falls_back_when_lang_missing():
    p = EcommerceAssistantAgent()
    spec = _spec()
    spec.title.pop("zh", None)  # 只剩 en
    out = await p.list_to_platforms(
        product=spec,
        platforms=["shopify"],
        languages=["de"],  # 没有 de，应回落到 en
    )
    assert out["ok"] is True
    assert out["results"][0]["preview_title"] == "Smart Bottle"


# ---------------------------------------------------------------------------
# 6. vat_guidance
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_vat_guidance_germany():
    p = EcommerceAssistantAgent()
    g = await p.vat_guidance("德国", "Amazon FBA")
    assert isinstance(g, VATGuidance)
    assert g.vat_rate_pct == 19.0
    assert g.filing_frequency == "monthly"
    assert g.registration_required is True
    # disclaimer 必须存在并提示找税务师
    assert "税务师" in g.disclaimer or "律师" in g.disclaimer
    assert "不构成专业" in g.disclaimer


@pytest.mark.asyncio
async def test_vat_guidance_us_uses_sales_tax_path():
    p = EcommerceAssistantAgent()
    g = await p.vat_guidance("US", "海外仓直发")
    assert g.vat_rate_pct == 0.0  # 美国没联邦 VAT，走 sales tax
    # 步骤里必须出现 nexus 概念
    assert any("nexus" in s.lower() for s in g.recommended_steps)
    assert g.disclaimer  # 强制 disclaimer


@pytest.mark.asyncio
async def test_vat_guidance_unknown_country_safe_default():
    p = EcommerceAssistantAgent()
    g = await p.vat_guidance("不存在国", "独立站")
    assert g.registration_required is True
    assert g.disclaimer  # 即使是默认值也必须带 disclaimer
