"""跨境电商助手 7 个 API endpoint 集成测试（P7-E）。

覆盖：
    POST /api/v1/personas/ecommerce/analyze-niche
    POST /api/v1/personas/ecommerce/verify-supplier
    POST /api/v1/personas/ecommerce/negotiate
    POST /api/v1/personas/ecommerce/setup-store
    POST /api/v1/personas/ecommerce/list-to-platforms
    POST /api/v1/personas/ecommerce/vat-guidance
    GET  /api/v1/personas/ecommerce/dashboard

鉴权：所有 endpoint 都要求登录用户（401 守卫）。
"""

from __future__ import annotations

# SQLite ↔ JSONB 兼容补丁（与其它 API 测试保持一致）
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler as _SQLiteTC

if not hasattr(_SQLiteTC, "visit_JSONB"):

    def _visit_JSONB(self, type_, **kw):  # noqa: N802
        return self.visit_JSON(type_, **kw)

    _SQLiteTC.visit_JSONB = _visit_JSONB  # type: ignore[attr-defined]


import pytest
from httpx import AsyncClient

PREFIX = "/api/v1/personas/ecommerce"


# ---------------------------------------------------------------------------
# 1. analyze-niche
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_analyze_niche_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/analyze-niche",
        json={"niche": "瑜伽垫", "target_markets": ["US", "DE"]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["niche"] == "瑜伽垫"
    assert body["recommended_action"] in {"enter", "wait", "skip"}
    assert isinstance(body["avg_price_band"], list) and len(body["avg_price_band"]) == 2
    assert len(body["citations"]) >= 1


@pytest.mark.asyncio
async def test_analyze_niche_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        f"{PREFIX}/analyze-niche",
        json={"niche": "瑜伽垫", "target_markets": []},
    )
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 2. verify-supplier
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_verify_supplier_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/verify-supplier",
        json={"supplier_id_or_url": "1688:SH123456", "source": "alibaba_1688"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["recommendation"] in {"trust", "verify_more", "avoid"}
    assert "moq" in body


# ---------------------------------------------------------------------------
# 3. negotiate
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_negotiate_round1_anchor(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/negotiate",
        json={"target_price": 100.0, "mood": "moderate", "history": []},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["move_type"] == "anchor"
    assert body["proposed_price"] == pytest.approx(70.0, abs=0.01)


@pytest.mark.asyncio
async def test_negotiate_invalid_mood_returns_400(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/negotiate",
        json={"target_price": 100.0, "mood": "hostile", "history": []},
    )
    # pydantic 校验 → 422
    assert r.status_code in {400, 422}


@pytest.mark.asyncio
async def test_negotiate_walk_away_via_api(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/negotiate",
        json={
            "target_price": 100.0,
            "mood": "moderate",
            "history": [{"round": 1, "our_price": 70.0, "their_price": 130.0}],
        },
    )
    assert r.status_code == 200
    assert r.json()["move_type"] == "walk_away"


# ---------------------------------------------------------------------------
# 4. setup-store
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_setup_store_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/setup-store",
        json={
            "oauth_token": "shpca_FAKE_TOKEN",
            "theme": "dawn",
            "products": [{"sku": "A001"}],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["installed_theme"] == "dawn"
    assert body["products_created"] == 1


# ---------------------------------------------------------------------------
# 5. list-to-platforms
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_to_platforms_multi_lang(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/list-to-platforms",
        json={
            "product": {
                "sku": "SKU-XYZ",
                "title": {"zh": "智能水杯", "en": "Smart Bottle"},
                "description": {"en": "Keeps cold 12h"},
                "price": 29.99,
                "currency": "USD",
                "images": ["https://cdn.example.com/1.jpg"],
                "weight_g": 350,
                "dimensions_cm": [8.0, 8.0, 22.0],
                "hs_code": "3924100000",
                "origin_country": "CN",
            },
            "platforms": ["shopify", "amazon_sp"],
            "languages": ["en", "ja"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["total"] == 4  # 2 平台 × 2 语言
    assert "content_director_persona" in body["delegated_to"]


@pytest.mark.asyncio
async def test_list_to_platforms_unsupported(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/list-to-platforms",
        json={
            "product": {
                "sku": "SKU-001",
                "title": {"en": "X"},
                "description": {"en": "X"},
                "price": 10.0,
                "currency": "USD",
                "images": [],
                "weight_g": 100,
                "dimensions_cm": [1, 1, 1],
                "hs_code": None,
                "origin_country": "CN",
            },
            "platforms": ["ebay"],  # 不在 supported_apps
            "languages": ["en"],
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is False
    assert body["error"] == "unsupported_platforms"


# ---------------------------------------------------------------------------
# 6. vat-guidance
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_vat_guidance_endpoint_germany(auth_client: AsyncClient) -> None:
    r = await auth_client.post(
        f"{PREFIX}/vat-guidance",
        json={"country": "德国", "scenario": "Amazon FBA"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["vat_rate_pct"] == 19.0
    assert body["filing_frequency"] == "monthly"
    # disclaimer 必须返回（合规风险防护）
    assert body["disclaimer"]
    assert "不构成专业" in body["disclaimer"]


@pytest.mark.asyncio
async def test_vat_guidance_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        f"{PREFIX}/vat-guidance",
        json={"country": "德国", "scenario": "FBA"},
    )
    assert r.status_code in {401, 403}


# ---------------------------------------------------------------------------
# 7. dashboard
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_dashboard_endpoint(auth_client: AsyncClient) -> None:
    r = await auth_client.get(f"{PREFIX}/dashboard")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["persona_id"] == "ecommerce_assistant"
    # 5 个平台 by_platform 都返回
    assert len(body["by_platform"]) == 5
    platform_ids = {p["platform"] for p in body["by_platform"]}
    assert platform_ids == {"shopify", "amazon_sp", "alibaba_1688", "shopee", "tiktok_shop"}
    assert body["last_updated"]
