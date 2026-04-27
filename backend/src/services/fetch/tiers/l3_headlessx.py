# -*- coding: utf-8 -*-
"""
L3 HeadlessX — 反检测 headless 浏览器（占位，由 P6-B 实装）。

预期接入方案：
- 使用 ``headlessx`` / undetected-playwright / patchright 等反检测方案
- 支持 device profile / proxy rotation / 真实指纹（canvas / WebGL / fonts）
- 失败时由 FetchService 自动降级到 L2 crawl4ai

P6-B 接入步骤：
1. 替换 ``fetch()`` 中的 ``raise NotImplementedError``
2. 在 ``__init__`` 中初始化 headless 实例池（建议 3-5 实例）
3. 透传 ``request.extra`` 中的 ``device``/``proxy``/``viewport``
4. 实装完成后，在 ``L3HeadlessXTier.available`` 类属性置 True
"""

from __future__ import annotations

import time

from src.services.fetch.models import (
    FetchRequest,
    FetchResponse,
    FetchTier,
)
from src.services.fetch.tiers.base import BaseTier


class L3HeadlessXTier(BaseTier):
    """L3 反检测 headless 浏览器抓取（占位）。

    在 P6-B 实装之前，所有 L3 请求会返回 503 + ``error="l3_not_implemented"``，
    由 ``FetchService`` 自动降级到 L2 crawl4ai。
    """

    tier = FetchTier.L3_HEADLESSX
    available: bool = False  # P6-B 实装后置 True

    def __init__(self, *, instance_pool_size: int = 3) -> None:
        self._pool_size = instance_pool_size

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        start = time.monotonic()
        # 显式占位 — 不抛 NotImplementedError，让 FetchService 能优雅降级
        return FetchResponse(
            request=request,
            status_code=503,
            tier_used=self.tier,
            duration_ms=int((time.monotonic() - start) * 1000),
            error="l3_not_implemented (P6-B 待实装)",
        )

    async def aclose(self) -> None:
        return None
