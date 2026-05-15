"""compliance 子模块单测：allowlist + blocklist + WeChat / 裁判文书拒绝。"""

from __future__ import annotations

import pytest

from src.services.fetch.compliance import (
    ALLOWED_DOMAINS,
    BLOCKED_DOMAINS,
    is_allowed,
    is_blocked,
)
from src.services.fetch.models import FetchRequest

# ---------- allowlist ----------


@pytest.mark.parametrize(
    "url",
    [
        "https://www.npc.gov.cn/abc",
        "https://www.court.gov.cn/x",
        "https://www.creditchina.gov.cn/y",
        "https://detail.1688.com/abc.html",
        "https://test-shop.myshopify.com/products",
        "https://www.people.com.cn/news",
        "https://www.36kr.com/article",
    ],
)
def test_allowlist_known_domains(url: str) -> None:
    assert is_allowed(url) is True


def test_allowlist_rejects_unknown() -> None:
    assert is_allowed("https://random-blog.example.io") is False


def test_allowlist_extra_domain() -> None:
    assert is_allowed("https://my-internal.lan", extra=["my-internal.lan"]) is True


def test_allowlist_invalid_url() -> None:
    assert is_allowed("not-a-url") is False


# ---------- blocklist ----------


def test_blocklist_wenshu_court_returns_reason() -> None:
    reason = is_blocked("https://wenshu.court.gov.cn/case/abc")
    assert reason is not None
    assert reason.code == "WENSHU_FORBIDDEN"
    assert "裁判文书网" in reason.message
    assert reason.suggestion is not None


def test_blocklist_wechat_mp_returns_reason() -> None:
    reason = is_blocked("https://mp.weixin.qq.com/s?biz=abc")
    assert reason is not None
    assert reason.code == "WECHAT_MP_FORBIDDEN"
    assert "公众号" in reason.message


def test_blocklist_wechat_root_returns_reason() -> None:
    reason = is_blocked("https://weixin.qq.com/some")
    assert reason is not None
    assert reason.code == "WECHAT_FORBIDDEN"


def test_blocklist_shopify_admin_path_returns_reason() -> None:
    reason = is_blocked("https://my-store.myshopify.com/admin/orders")
    assert reason is not None
    assert reason.code == "SHOPIFY_ADMIN_FORBIDDEN"
    # 同域 product 路径应放行
    assert is_blocked("https://my-store.myshopify.com/products/abc") is None


def test_blocklist_returns_none_for_allowed_url() -> None:
    assert is_blocked("https://www.npc.gov.cn/article") is None


def test_blocklist_invalid_url_returns_invalid_url() -> None:
    reason = is_blocked("not-a-url")
    assert reason is not None
    assert reason.code == "INVALID_URL"


# ---------- FetchService 集成：WeChat / 裁判文书 → 403 ----------


@pytest.mark.asyncio
async def test_fetch_service_wechat_returns_403_with_reason() -> None:
    from src.services.fetch import FetchService

    svc = FetchService(respect_robots=False)
    resp = await svc.fetch(FetchRequest(url="https://mp.weixin.qq.com/s?biz=abc"))

    assert resp.status_code == 403
    assert resp.blocked_reason == "WECHAT_MP_FORBIDDEN"
    assert resp.error is not None and "公众号" in resp.error


@pytest.mark.asyncio
async def test_fetch_service_wenshu_returns_403_with_reason() -> None:
    from src.services.fetch import FetchService

    svc = FetchService(respect_robots=False)
    resp = await svc.fetch(FetchRequest(url="https://wenshu.court.gov.cn/case/abc"))

    assert resp.status_code == 403
    assert resp.blocked_reason == "WENSHU_FORBIDDEN"


@pytest.mark.asyncio
async def test_check_compliance_returns_full_judgment() -> None:
    from src.services.fetch import FetchService

    svc = FetchService()
    result = svc.check_compliance("https://wenshu.court.gov.cn/abc")

    assert result["blocked"] is True
    assert result["block_reason"]["code"] == "WENSHU_FORBIDDEN"
    assert result["allowed"] is True  # 域名在白名单（gov.cn）


def test_blocked_domains_dictionary_contents() -> None:
    """显式断言关键域已注册（防止后续误删）。"""
    assert "wenshu.court.gov.cn" in BLOCKED_DOMAINS
    assert "mp.weixin.qq.com" in BLOCKED_DOMAINS


def test_allowed_domains_list_has_gov() -> None:
    assert any(".gov.cn" in d for d in ALLOWED_DOMAINS)
