# -*- coding: utf-8 -*-
"""
FetchService 数据模型 — Request / Response / Tier 枚举

核心约定：
- ``FetchRequest`` 在门面层统一表达「我要抓什么 / 怎么抓 / 谁在抓」
- ``FetchResponse`` 统一表达「抓到了什么 / 用了哪一层 / 是否被合规拦截」
- 所有 Tier 实现（L1/L2/L3/L4）都以这两个对象为唯一入参 / 出参，
  方便在 ``FetchService`` 内做路由 / 限流 / 审计装饰，而无需关心底层细节。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FetchTier(str, Enum):
    """信息获取栈的 5 级分层（与 docs/v3/CAPABILITY_MATRIX.md 对齐）。

    L0 是 cache 命中（短路返回，不真正发请求）。
    L4 由 P6-D 的官方 API 适配实现（Shopify / Amazon SP-API / 北大法宝等）。
    """

    L0_CACHE = "L0_CACHE"
    L1_HTTP = "L1_HTTP"
    L2_CRAWL4AI = "L2_CRAWL4AI"
    L3_HEADLESSX = "L3_HEADLESSX"
    L4_OFFICIAL_API = "L4_OFFICIAL_API"


class ExtractFormat(str, Enum):
    """抽取产物格式。"""

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


@dataclass
class ExtractConfig:
    """结构化抽取配置（可选）。

    - ``css_selectors`` / ``xpath`` 二选一，由 L1 / L2 解析时使用
    - ``schema`` 用于 LLM 友好抽取（L2 crawl4ai 的 JsonCssExtractionStrategy）
    - ``format`` 决定返回 ``FetchResponse.extracted`` 的形态
    """

    css_selectors: dict[str, str] = field(default_factory=dict)
    xpath: dict[str, str] = field(default_factory=dict)
    schema: dict[str, Any] = field(default_factory=dict)
    format: ExtractFormat = ExtractFormat.MARKDOWN


@dataclass
class FetchRequest:
    """统一抓取请求。

    所有字段都可序列化为 JSON，方便在 API 层用 Pydantic 做镜像。
    """

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes | None = None
    timeout: int = 30
    tier_hint: FetchTier | None = None
    extract: ExtractConfig | None = None
    user_id: str | None = None
    bypass_cache: bool = False
    # 透传给 Tier 适配器的额外参数（例如 L3 的 device profile）
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchResponse:
    """统一抓取响应。

    - ``tier_used`` 让上层知道实际走了哪一层（可能 L2 失败降级到 L1）
    - ``blocked_reason`` 非空表示被合规层拦截（status_code=403）
    - ``extracted`` 是按 ``ExtractConfig`` 抽取出来的结构化数据
    """

    request: FetchRequest
    status_code: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    text: str | None = None
    tier_used: FetchTier = FetchTier.L1_HTTP
    duration_ms: int = 0
    extracted: dict[str, Any] | None = None
    cached: bool = False
    error: str | None = None
    blocked_reason: str | None = None

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300 and self.error is None
