"""法律数据源抽象基类与合规护栏。

所有 BaseLegalSource 的子类在 fetch / search / get_full_text 之前，
必须经过 ``assert_url_compliant`` 校验目标 URL，否则立刻抛出 ComplianceError。

合规底线（参考 P6-C 任务）:
- ❌ wenshu.court.gov.cn      —— 裁判文书网，走已落库历史
- ❌ mp.weixin.qq.com         —— 微信公众号，禁止爬列表/文章
- ✅ flk.npc.gov.cn           —— 国家法律法规数据库公开 API
- ✅ creditchina.gov.cn       —— 信用中国公开企业信用查询
- ✅ api.pkulaw.com           —— 北大法宝商业 API（需付费授权）
- ✅ api.wkinfo.com.cn        —— 威科先行商业 API（需付费授权）
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import ClassVar
from urllib.parse import urlparse

# ============== 合规白/黑名单 ==============

BANNED_HOSTS: frozenset[str] = frozenset(
    {
        # 裁判文书网（受 反爬 + ToS 双重约束，走 historical_wenshu 已落库表）
        "wenshu.court.gov.cn",
        "www.wenshu.court.gov.cn",
        # 微信公众号（mp.weixin.qq.com 禁止爬列表、禁止绕过 cookie）
        "mp.weixin.qq.com",
    }
)


class ComplianceError(RuntimeError):
    """合规底线被触发时抛出。永远不可在业务代码里 catch 后继续访问。"""


def assert_url_compliant(url: str) -> None:
    """在发起 HTTP 请求前对 URL 做合规校验。

    Args:
        url: 即将访问的完整 URL（http/https）。

    Raises:
        ComplianceError: 当 host 命中黑名单时立即抛出，附带说明文案。
    """
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if not host:
        raise ComplianceError(f"非法 URL：{url!r} 缺少 host，无法进行合规校验。")
    if host in BANNED_HOSTS:
        raise ComplianceError(
            f"合规拒绝：禁止直接访问 {host}（命中 P6-C 法律数据源黑名单）。"
            "请改用已落库历史数据（historical_wenshu）或商业授权 API（pkulaw / wkinfo）。"
        )


# ============== 数据模型 ==============


class LawType(str, Enum):
    """法律法规分类。"""

    LAW = "law"  # 法律（全国人大）
    REGULATION = "regulation"  # 行政法规 / 部门规章
    JUDICIAL_INTERPRETATION = "judicial_interpretation"  # 司法解释
    CASE = "case"  # 案例 / 裁判文书
    OTHER = "other"


class LawStatus(str, Enum):
    """法律法规状态。"""

    ACTIVE = "active"  # 现行有效
    AMENDED = "amended"  # 已修订
    ABOLISHED = "abolished"  # 已废止
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class LawSearchQuery:
    """法律检索请求参数。"""

    keyword: str
    law_type: str | None = None  # LawType 字符串值；None 表示不限
    jurisdiction: str | None = None  # 国家级 / 省级 / 市级；自由文本
    date_from: date | None = None
    date_to: date | None = None
    limit: int = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if not self.keyword or not self.keyword.strip():
            raise ValueError("LawSearchQuery.keyword 不能为空")
        if self.limit <= 0 or self.limit > 200:
            raise ValueError("LawSearchQuery.limit 必须在 (0, 200]")
        if self.offset < 0:
            raise ValueError("LawSearchQuery.offset 必须 >= 0")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("LawSearchQuery.date_from 不能晚于 date_to")


@dataclass
class LawSearchResult:
    """法律检索结果项。"""

    source: str  # 数据源 ID
    law_id: str  # 数据源内部唯一 ID
    title: str
    law_type: str  # LawType 字符串值
    issuing_authority: str  # 颁布机关
    issued_date: date | None = None
    effective_date: date | None = None
    status: str = LawStatus.UNKNOWN.value
    full_text_url: str = ""
    summary: str | None = None
    extra: dict = field(default_factory=dict)  # 数据源特有字段（如案号、地区）


# ============== 抽象基类 ==============


class BaseLegalSource(ABC):
    """所有法律数据源的统一抽象。"""

    source_id: ClassVar[str]
    display_name: ClassVar[str]
    requires_credentials: ClassVar[bool] = False
    # 子类可声明默认 host，便于 health_check 自检合规
    base_host: ClassVar[str] = ""

    @abstractmethod
    async def search(self, query: LawSearchQuery) -> list[LawSearchResult]:
        """按关键词检索法律法规/案例。"""

    @abstractmethod
    async def get_full_text(self, law_id: str) -> str:
        """获取指定 law_id 的全文。"""

    @abstractmethod
    async def health_check(self) -> bool:
        """健康检查：连通性 + 凭证可用性。"""

    # ---- 工具方法（子类可复用） ----

    def _ensure_compliant(self, url: str) -> None:
        """子类发起 HTTP 之前必须调用本方法，保证黑名单不被绕过。"""
        assert_url_compliant(url)
