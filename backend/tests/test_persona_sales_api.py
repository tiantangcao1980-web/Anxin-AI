"""persona_sales 6 endpoint API 测试 (P7-C 获客猎手)。

⚠️ 设计说明：
v3/main 当前主 app 在 P6 fetch / P4 app_authorization 的 import 链上有
**预先存在**的损坏（``TierName`` / ``OAuthError`` 未导出，与本 P7-C 无关），
导致 ``src.api.main:app`` 无法启动；因此本测试用 **隔离 FastAPI app + 路由 mount + dep override**
直接挂载 P7-C 的 router，独立验证 6 endpoint 的契约。

覆盖：
    POST /personas/sales/discover-leads
    POST /personas/sales/draft-email
    POST /personas/sales/generate-quote
    POST /personas/sales/sync-crm
    POST /personas/sales/linkedin-outreach
    GET  /personas/sales/leads
"""

from __future__ import annotations

import sys
import types
import uuid
from types import SimpleNamespace

import pytest
import pytest_asyncio
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient

# 与其它 P4/P6 路由测试同款：让 conftest 的 SQLite engine 能编译 JSONB 列
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")  # type: ignore[misc]
def _compile_jsonb_for_sqlite(type_, compiler, **kw):  # noqa: ARG001
    return "JSON"


# ---------------------------------------------------------------------------
# 临时 import shim
# ---------------------------------------------------------------------------
# v3/main 当前在 P6 fetch tier 链上有 *预先存在* 的 ImportError
# (``TierName`` 没在 ``src.services.fetch.tiers.base`` 导出)，
# 导致 ``src.api.routes/__init__.py`` 在 import ``fetch`` 时崩溃，
# 进而阻塞整个 ``src.api.routes`` 包的子模块加载。
#
# 这与本 P7-C 工单无关，且修它不在本 worktree 文件边界内。
# 这里在 import 任何 routes 之前先把 ``src.api.routes.fetch`` 替换成
# 一个空的 APIRouter stub，让 routes/__init__.py 能跑完，进而能加载
# ``persona_sales`` 模块本身。上游修复后此 shim 自然失活。
if "src.api.routes.fetch" not in sys.modules:
    _fetch_stub = types.ModuleType("src.api.routes.fetch")
    _fetch_stub.router = APIRouter()
    sys.modules["src.api.routes.fetch"] = _fetch_stub

from src.api.routes.persona_sales import router as persona_sales_router  # noqa: E402
from src.core.deps import get_current_user_required  # noqa: E402

BASE = "/personas/sales"


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    app = FastAPI()
    app.include_router(persona_sales_router, prefix="/personas/sales")

    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        email="sales@anxin.cn",
        role="user",
        organization_id=None,
    )

    async def _fake_user():
        return fake_user

    app.dependency_overrides[get_current_user_required] = _fake_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# 1. discover-leads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_discover_leads_endpoint(client):
    payload = {
        "industry": "新能源汽车配件",
        "company_size": "50-500",
        "limit": 5,
        "candidates": [
            {
                "id": "c1",
                "company_name": "广州绿能",
                "industry": "新能源汽车配件",
                "country": "中国",
                "employees_estimate": 200,
                "contacts": [{"name": "张总", "title": "采购总监"}],
                "tags": ["funded"],
                "source": "linkedin",
            },
            {
                "id": "c2",
                "company_name": "外行业 Co",
                "industry": "餐饮",
                "country": "中国",
                "employees_estimate": 100,
                "contacts": [],
                "tags": [],
                "source": "manual",
            },
        ],
    }
    res = await client.post(f"{BASE}/discover-leads", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    ids = [it["id"] for it in data["items"]]
    assert "c1" in ids and "c2" not in ids
    assert data["items"][0]["score"] > 0
    assert "icp_fit" in data["items"][0]["score_breakdown"]


# ---------------------------------------------------------------------------
# 2. draft-email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_email_endpoint_zh(client):
    payload = {
        "lead": {
            "company_name": "深圳新动力",
            "industry": "新能源汽车配件",
            "country": "中国",
            "contacts": [{"name": "李", "title": "采购总监"}],
        },
        "intent": "cold_intro",
        "language": "zh",
        "sender": {"name": "Anxin", "company": "安心智能"},
        "hooks": {"hook_recent_news": "完成 A 轮融资"},
    }
    res = await client.post(f"{BASE}/draft-email", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["language"] == "zh"
    assert data["template_id"] == "cold_intro_zh"
    assert "深圳新动力" in data["subject"] or "深圳新动力" in data["body"]
    assert 0 < data["estimated_response_rate"] <= 0.5


@pytest.mark.asyncio
async def test_draft_email_endpoint_follow_up_en(client):
    payload = {
        "lead": {
            "company_name": "Acme",
            "industry": "Industrial",
            "country": "US",
            "contacts": [{"name": "John", "title": "CTO"}],
        },
        "intent": "follow_up",
        "language": "en",
        "sender": {"name": "Sam", "company": "Anxin"},
    }
    res = await client.post(f"{BASE}/draft-email", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["template_id"] == "follow_up_en"
    assert data["language"] == "en"


# ---------------------------------------------------------------------------
# 3. generate-quote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_quote_endpoint(client):
    payload = {
        "lead": {
            "company_name": "ACME",
            "industry": "Hardware",
            "country": "US",
            "contacts": [],
        },
        "items": [
            {
                "sku": "SKU-A",
                "name": "Widget",
                "quantity": 10,
                "unit_price": 25.5,
                "currency": "USD",
                "discount_pct": 5,
            }
        ],
        "terms": {"payment_terms": "T/T 100%"},
    }
    res = await client.post(f"{BASE}/generate-quote", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["file_url"].startswith("data:application/")
    assert data["bytes_size"] > 0
    assert data["items_count"] == 1
    assert abs(data["subtotal"] - 242.25) < 1e-6  # 25.5 * 10 * 0.95
    assert data["currency"] == "USD"


@pytest.mark.asyncio
async def test_generate_quote_rejects_empty_items(client):
    payload = {
        "lead": {"company_name": "X", "industry": "i", "country": "US", "contacts": []},
        "items": [],
        "terms": {},
    }
    res = await client.post(f"{BASE}/generate-quote", json=payload)
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# 4. sync-crm
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_crm_endpoint_with_token_returns_created(client):
    payload = {
        "leads": [
            {
                "company_name": "ACME",
                "industry": "Hardware",
                "country": "US",
                "contacts": [],
            }
        ],
        "crm": "hubspot",
        "oauth_token": "fake-token",
    }
    res = await client.post(f"{BASE}/sync-crm", json=payload)
    assert res.status_code == 200, res.text
    data = res.json()
    # 没注入 client 时占位实现 → created = len(leads)
    assert data["crm"] == "hubspot"
    assert data["created"] == 1
    assert data["failed"] == 0


# ---------------------------------------------------------------------------
# 5. linkedin-outreach
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_linkedin_outreach_endpoint_invalid_url(client):
    payload = {
        "profile_url": "https://twitter.com/x",
        "message_template": "hi",
        "oauth_token": "tok",
    }
    res = await client.post(f"{BASE}/linkedin-outreach", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is False
    assert data["error"] == "invalid_profile_url"


@pytest.mark.asyncio
async def test_linkedin_outreach_endpoint_queued_when_no_client(client):
    payload = {
        "profile_url": "https://www.linkedin.com/in/abc/",
        "message_template": "Hi there",
        "oauth_token": "tok",
    }
    res = await client.post(f"{BASE}/linkedin-outreach", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["status"] == "queued"


# ---------------------------------------------------------------------------
# 6. GET /leads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_leads_after_discovery(client):
    # 先 discover 几条
    discover_payload = {
        "industry": "新能源汽车配件",
        "limit": 10,
        "candidates": [
            {
                "id": "L1",
                "company_name": "Hot Co",
                "industry": "新能源汽车配件",
                "country": "中国",
                "employees_estimate": 100,
                "contacts": [{"name": "X", "title": "采购总监"}],
                "tags": ["funded", "uses-bosch"],
                "source": "linkedin",
            },
            {
                "id": "L2",
                "company_name": "Warm Co",
                "industry": "新能源汽车配件",
                "country": "中国",
                "employees_estimate": 100,
                "contacts": [{"name": "Y", "title": "工程师"}],
                "tags": [],
                "source": "linkedin",
            },
        ],
    }
    r1 = await client.post(f"{BASE}/discover-leads", json=discover_payload)
    assert r1.status_code == 200

    r2 = await client.get(f"{BASE}/leads")
    assert r2.status_code == 200
    data = r2.json()
    assert data["total"] >= 2
    scores = [it["score"] for it in data["items"]]
    assert scores == sorted(scores, reverse=True)

    r3 = await client.get(f"{BASE}/leads?score_min=0.99")
    assert r3.status_code == 200
    assert r3.json()["total"] == 0

    r4 = await client.get(f"{BASE}/leads?status=hot")
    assert r4.status_code == 200
