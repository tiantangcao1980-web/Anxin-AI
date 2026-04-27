# -*- coding: utf-8 -*-
"""法律数据源模块（P6-C）。

合规底线（强制）:
- 禁止爬取 wenshu.court.gov.cn（裁判文书网）
- 禁止爬取 mp.weixin.qq.com（微信公众号）
- 仅允许政府公开数据库 / 商业付费 API / 已落库历史数据
"""

from .base import (
    BaseLegalSource,
    LawSearchQuery,
    LawSearchResult,
    LawType,
    LawStatus,
    BANNED_HOSTS,
    ComplianceError,
    assert_url_compliant,
)
from .flk_npc_gov import FlkNpcGovSource
from .credit_china import CreditChinaSource
from .pkulaw import PkuLawSource
from .wkinfo import WkInfoSource
from .historical_wenshu import HistoricalWenshuSource

__all__ = [
    "BaseLegalSource",
    "LawSearchQuery",
    "LawSearchResult",
    "LawType",
    "LawStatus",
    "BANNED_HOSTS",
    "ComplianceError",
    "assert_url_compliant",
    "FlkNpcGovSource",
    "CreditChinaSource",
    "PkuLawSource",
    "WkInfoSource",
    "HistoricalWenshuSource",
]
