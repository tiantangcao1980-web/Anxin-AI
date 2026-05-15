"""
URL → FetchTier 路由 — FetchService 的「调度脑」。

规则优先级（自上而下短路）：
1. 显式 ``tier_hint`` 覆盖一切（除非黑名单命中）
2. RSS / Atom / sitemap 链接 → L1（纯静态 XML）
3. 已知反爬严格电商 → L3（反检测 headless）
4. 政府 / 司法域名（.gov.cn 系）→ L1（基本都是静态页 + 无 JS）
5. 其它默认 → L2（crawl4ai，能搞定大多数 JS 渲染）

实现刻意保持「纯函数」 — 无 IO、无锁、无状态，便于单测 & 在
``FetchService`` 中复用。
"""

from __future__ import annotations

from urllib.parse import urlparse

from src.services.fetch.models import FetchRequest, FetchTier

# 强反爬电商域 → L3 HeadlessX
_L3_DOMAINS = {
    "amazon.com",
    "amazon.cn",
    "amazon.co.jp",
    "amazon.de",
    "shopify.com",
    "shopee.com",
    "shopee.tw",
    "shopee.sg",
    "1688.com",
    "detail.1688.com",
    "tiktok.com",
    "tmall.com",
    "taobao.com",
    "jd.com",
    "lazada.com",
}

_L3_DOMAIN_SUFFIXES = (
    ".myshopify.com",
    ".amazon.com",
    ".amazon.cn",
    ".shopee.com",
    ".tiktok.com",
    ".tmall.com",
    ".taobao.com",
)

# 政府 / 司法 / 公共数据 → L1（一般是静态 HTML / XML）
_L1_DOMAIN_SUFFIXES = (
    ".gov.cn",
    ".npc.gov.cn",
    ".court.gov.cn",
    ".customs.gov.cn",
    ".scio.gov.cn",
    ".creditchina.gov.cn",
    ".miit.gov.cn",
)

# RSS / sitemap 等纯静态资源 → L1
_L1_PATH_HINTS = (
    "/rss",
    "/feed",
    "/atom",
    "/sitemap",
    ".xml",
    ".rss",
    ".atom",
)


def _hostname(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def _path(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.path or "/").lower()


def is_l3_domain(host: str) -> bool:
    return host in _L3_DOMAINS or host.endswith(_L3_DOMAIN_SUFFIXES)


def is_l1_gov(host: str) -> bool:
    return host.endswith(_L1_DOMAIN_SUFFIXES)


def is_static_feed(path: str) -> bool:
    return any(hint in path for hint in _L1_PATH_HINTS)


def route(request: FetchRequest) -> FetchTier:
    """根据 URL + hint 决定走哪一层。

    注意：
    - 这里只做「层选择」，不做合规检查。合规由 ``FetchService`` 在调用
      ``route()`` 之前 / 之后单独执行（黑名单 → 提前 403）。
    """
    if request.tier_hint is not None:
        return request.tier_hint

    host = _hostname(request.url)
    path = _path(request.url)

    # RSS / atom / sitemap 优先
    if is_static_feed(path):
        return FetchTier.L1_HTTP

    # 反爬严格电商 → L3
    if is_l3_domain(host):
        return FetchTier.L3_HEADLESSX

    # 政府 / 司法 → L1
    if is_l1_gov(host):
        return FetchTier.L1_HTTP

    # 其它默认 L2
    return FetchTier.L2_CRAWL4AI
