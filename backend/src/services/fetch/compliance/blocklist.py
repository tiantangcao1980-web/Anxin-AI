"""
抓取域名 / 路径硬黑名单 — 命中即拒绝（HTTP 403 + blocked_reason）。

来源：
- 司法 / 政务公开 API 替代了爬取（如裁判文书网，应走司法部公开数据接口）
- ToS 明确禁止机器抓取（公众号文章列表、Shopify admin 后台）
- 反爬强 + 法律风险（部分内容平台）

policy 与 ``allowlist.py`` 互补：
- 黑名单优先级最高，无视任何 ``tier_hint``
- 即使域名在白名单，路径黑名单仍生效（例如 ``*.myshopify.com/admin``）
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class BlockReason:
    """黑名单命中说明（写入审计 + 返回给调用方）。"""

    code: str
    message: str
    suggestion: str | None = None


# 域名级硬拦截
BLOCKED_DOMAINS: dict[str, BlockReason] = {
    "wenshu.court.gov.cn": BlockReason(
        code="WENSHU_FORBIDDEN",
        message="裁判文书网禁止机器抓取，请改用最高人民法院司法公开数据 API。",
        suggestion="走 P6-C 法律源里的 court-open-data 适配。",
    ),
    "mp.weixin.qq.com": BlockReason(
        code="WECHAT_MP_FORBIDDEN",
        message="微信公众号文章 / 列表禁止抓取（违反《微信公众平台运营规范》）。",
        suggestion="改走授权的微信开放平台「素材管理」API，或人工导出。",
    ),
    "weixin.qq.com": BlockReason(
        code="WECHAT_FORBIDDEN",
        message="微信域整体禁止机器抓取。",
        suggestion="使用官方开放平台 API。",
    ),
}

# 路径级黑名单（域名通配 + 路径前缀）
BLOCKED_PATH_PATTERNS: list[tuple[str, str, BlockReason]] = [
    (
        "*.myshopify.com",
        "/admin",
        BlockReason(
            code="SHOPIFY_ADMIN_FORBIDDEN",
            message="Shopify 后台 /admin 路径禁止抓取，请改用 Admin API。",
            suggestion="P6-D 电商源接入 Shopify Admin REST/GraphQL API。",
        ),
    ),
    (
        "*.myshopify.com",
        "/api",
        BlockReason(
            code="SHOPIFY_API_DIRECT",
            message="不要绕过 Admin API 直接抓取私有接口。",
            suggestion="P6-D 适配层应使用官方 API key + REST 客户端。",
        ),
    ),
]


def _hostname(url: str) -> tuple[str | None, str]:
    parsed = urlparse(url)
    host = parsed.hostname.lower() if parsed.hostname else None
    return host, parsed.path or "/"


def _domain_match(host: str, pattern: str) -> bool:
    if pattern.startswith("*."):
        suffix = pattern[1:]
        return host.endswith(suffix) or host == suffix.lstrip(".")
    return host == pattern


def is_blocked(url: str) -> BlockReason | None:
    """命中黑名单返回 BlockReason，否则返回 None。"""
    host, path = _hostname(url)
    if not host:
        return BlockReason(
            code="INVALID_URL",
            message="URL 无效或缺少 host。",
        )

    # 1. 域名级
    for domain, reason in BLOCKED_DOMAINS.items():
        if _domain_match(host, domain):
            return reason

    # 2. 路径级（域名通配 + 路径前缀）
    for pattern, path_prefix, reason in BLOCKED_PATH_PATTERNS:
        if _domain_match(host, pattern) and path.startswith(path_prefix):
            return reason

    return None
