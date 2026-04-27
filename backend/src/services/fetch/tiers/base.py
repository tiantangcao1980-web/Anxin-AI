# -*- coding: utf-8 -*-
"""BaseTier — 所有抓取层的统一抽象。

每个 Tier 实现的最小契约：
- ``tier`` 类属性：声明自己属于哪一层
- ``async fetch(request) -> FetchResponse``：核心抓取
- ``async aclose()``：资源回收（HTTP 池、Browser 实例等）

FetchService 只与该接口打交道，不关心底层是 httpx / crawl4ai / Playwright。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.services.fetch.models import FetchRequest, FetchResponse, FetchTier


class BaseTier(ABC):
    """抓取层抽象基类。"""

    tier: FetchTier  # 子类必须覆盖

    @abstractmethod
    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """执行抓取，返回统一 FetchResponse。

        实现注意：
        - 不要在这里做合规检查（FetchService 已经做过）
        - 不要在这里做限流（FetchService 已经做过）
        - 失败请填 ``error`` 字段而不是抛异常 — FetchService 才能记审计
        """
        raise NotImplementedError

    async def aclose(self) -> None:  # pragma: no cover — 默认 no-op
        """关闭底层资源。子类按需覆盖。"""
        return None
