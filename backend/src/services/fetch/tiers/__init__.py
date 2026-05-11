# -*- coding: utf-8 -*-
"""FetchService 4 层 Tier 适配。

- ``base.BaseTier`` 抽象
- ``l1_http.L1HttpTier`` 真实装（httpx + selectolax/lxml）
- ``l2_crawl4ai.L2Crawl4AITier`` 包装现有 ``crawl4ai_service``
- ``l3_headlessx.L3HeadlessXTier`` 占位（P6-B 实装）
"""

from src.services.fetch.tiers.base import BaseTier
from src.services.fetch.tiers.l1_http import L1HttpTier
from src.services.fetch.tiers.l2_crawl4ai import L2Crawl4AITier
from src.services.fetch.tiers.l3_headlessx import L3HeadlessXTier

__all__ = [
    "BaseTier",
    "L1HttpTier",
    "L2Crawl4AITier",
    "L3HeadlessXTier",
]
