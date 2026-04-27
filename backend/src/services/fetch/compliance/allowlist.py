# -*- coding: utf-8 -*-
"""
抓取域名白名单 — 默认开放给 FetchService 的可信源。

匹配规则：
- 完全等值：``example.com`` 严格只允许 ``example.com``
- 通配符：``*.gov.cn`` 允许 ``npc.gov.cn`` / ``court.gov.cn`` / ``a.b.gov.cn``

实践原则：
- 白名单未命中并不立即拒绝（仍可走默认 Tier），但 ``is_allowed()`` 返回 False
  会被 ``FetchService`` 用于在审计日志中标注「域名未在白名单」，
  以便后续运营评估是否扩充。
- 真正的硬拦截在 blocklist.py。
"""

from __future__ import annotations

from urllib.parse import urlparse

# 政府 / 司法 / 公共数据
_GOV_DOMAINS = [
    "*.gov.cn",
    "*.npc.gov.cn",
    "*.court.gov.cn",
    "*.customs.gov.cn",
    "*.scio.gov.cn",
    "*.creditchina.gov.cn",
    "*.miit.gov.cn",
    "*.samr.gov.cn",
    "*.cnipa.gov.cn",
    "*.pkulaw.com",
]

# 主流新闻 / 行业资讯
_NEWS_DOMAINS = [
    "people.com.cn",
    "*.people.com.cn",
    "xinhuanet.com",
    "*.xinhuanet.com",
    "cctv.com",
    "*.cctv.com",
    "iyiou.com",
    "*.iyiou.com",
    "36kr.com",
    "*.36kr.com",
]

# 电商 / 跨境 — 仅允许 Shopify 公开店铺与 1688 商品详情
_ECOMMERCE_DOMAINS = [
    "1688.com",
    "*.1688.com",
    "shopify.com",
    "*.myshopify.com",
]


ALLOWED_DOMAINS: list[str] = _GOV_DOMAINS + _NEWS_DOMAINS + _ECOMMERCE_DOMAINS


def _hostname(url: str) -> str | None:
    parsed = urlparse(url)
    if not parsed.hostname:
        return None
    return parsed.hostname.lower()


def _matches(host: str, pattern: str) -> bool:
    pattern = pattern.lower()
    if pattern.startswith("*."):
        suffix = pattern[1:]  # ".gov.cn"
        return host.endswith(suffix) or host == suffix.lstrip(".")
    return host == pattern


def is_allowed(url: str, *, extra: list[str] | None = None) -> bool:
    """判断 URL 域名是否在白名单内。

    Args:
        url: 完整 URL（必须含 scheme）
        extra: 临时追加的允许域名（运营在管理后台动态加入）
    """
    host = _hostname(url)
    if not host:
        return False
    patterns = ALLOWED_DOMAINS + (extra or [])
    return any(_matches(host, p) for p in patterns)
