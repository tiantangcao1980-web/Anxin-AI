"""信用中国（creditchina.gov.cn）公开企业信用查询数据源。

仅查询公开企业信用：
- 失信被执行人
- 行政处罚记录
- 经营异常名录

输入：公司全称 / 统一社会信用代码（USCC，18 位）
输出：以 LawSearchResult 形式返回的"信用条目"列表（law_type=case 的近似映射）
"""

from __future__ import annotations

import logging
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar
from urllib.parse import urljoin

import httpx

from .base import (
    BaseLegalSource,
    LawSearchQuery,
    LawSearchResult,
    LawStatus,
    LawType,
)

logger = logging.getLogger(__name__)

# 18 位统一社会信用代码（GB 32100-2015）
USCC_PATTERN = re.compile(r"^[0-9A-HJ-NPQRTUWXY]{18}$")


def is_valid_uscc(code: str) -> bool:
    """简版 USCC 校验：长度 + 字符集；不做校验码摘要计算。"""
    if not code or len(code) != 18:
        return False
    return bool(USCC_PATTERN.match(code))


@dataclass
class CreditEntry:
    """信用条目（不直接对外，封装在 LawSearchResult.extra 内）。"""

    category: str  # "失信" / "行政处罚" / "经营异常"
    title: str
    issued_at: date | None
    issuing_authority: str
    detail: dict[str, Any]


class CreditChinaSource(BaseLegalSource):
    """信用中国公开数据源。"""

    source_id: ClassVar[str] = "credit_china"
    display_name: ClassVar[str] = "信用中国"
    requires_credentials: ClassVar[bool] = False
    base_host: ClassVar[str] = "public.creditchina.gov.cn"

    BASE_URL: ClassVar[str] = "https://public.creditchina.gov.cn"
    SEARCH_PATH: ClassVar[str] = "/credit-publicity/search"
    DETAIL_PATH: ClassVar[str] = "/credit-publicity/detail"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        rate_limiter: Callable[[], Awaitable[None]] | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._client = client
        self._owned_client = client is None
        self._timeout = timeout
        self._rate_limit = rate_limiter or self._noop_rate_limit

    @staticmethod
    async def _noop_rate_limit() -> None:
        return None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={"User-Agent": "AnxinLegal-FetchService/1.0 (+compliance@anxin)"},
            )
        return self._client

    async def aclose(self) -> None:
        if self._owned_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    # ---- BaseLegalSource ----

    async def search(self, query: LawSearchQuery) -> list[LawSearchResult]:
        """以 query.keyword 为公司名/USCC 进行查询。"""
        kw = query.keyword.strip()
        if not kw:
            raise ValueError("公司名或统一社会信用代码不能为空")
        # 输入鉴别：纯数字+大写字母 18 位 -> USCC，否则按公司名
        is_uscc = is_valid_uscc(kw)
        url = urljoin(self.BASE_URL, self.SEARCH_PATH)
        self._ensure_compliant(url)

        payload = {
            "keyword": kw,
            "queryType": "USCC" if is_uscc else "NAME",
            "pageSize": query.limit,
            "pageNum": (query.offset // max(query.limit, 1)) + 1,
        }
        await self._rate_limit()
        client = await self._get_client()
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json() if "json" in resp.headers.get("content-type", "") else {}

        return self._parse_search_response(data, kw)

    async def get_full_text(self, law_id: str) -> str:
        """信用中国的"全文"对应单条记录详情；law_id 为 detail id。"""
        if not law_id:
            raise ValueError("law_id 不能为空")
        url = urljoin(self.BASE_URL, self.DETAIL_PATH)
        self._ensure_compliant(url)

        await self._rate_limit()
        client = await self._get_client()
        resp = await client.get(url, params={"id": law_id})
        resp.raise_for_status()
        if "json" in resp.headers.get("content-type", ""):
            data = resp.json()
            return str(data.get("data") or data)
        return resp.text

    async def health_check(self) -> bool:
        try:
            self._ensure_compliant(self.BASE_URL)
            await self._rate_limit()
            client = await self._get_client()
            resp = await client.get(self.BASE_URL, timeout=5.0)
            return resp.status_code < 500
        except Exception as exc:  # pragma: no cover
            logger.warning("credit_china.health_check failed: %s", exc)
            return False

    # ---- 解析 ----

    def _parse_search_response(self, data: dict, kw: str) -> list[LawSearchResult]:
        items = data.get("data", {}).get("list") or data.get("list") or data.get("records") or []
        out: list[LawSearchResult] = []
        for item in items:
            category = str(
                item.get("type") or item.get("category") or item.get("信用类别") or "信用记录"
            )
            title = str(item.get("title") or item.get("subject") or category)
            out.append(
                LawSearchResult(
                    source=self.source_id,
                    law_id=str(item.get("id") or item.get("recordId") or ""),
                    title=f"[{category}] {title}",
                    law_type=LawType.CASE.value,  # 信用记录归入 CASE 近似
                    issuing_authority=str(
                        item.get("authority") or item.get("publisher") or item.get("处罚机关") or ""
                    ),
                    issued_date=_parse_date(
                        item.get("issuedAt") or item.get("publishDate") or item.get("发布时间")
                    ),
                    effective_date=None,
                    status=LawStatus.ACTIVE.value,
                    full_text_url=urljoin(
                        self.BASE_URL,
                        f"/credit-publicity/detail?id={item.get('id', '')}",
                    ),
                    summary=item.get("summary") or item.get("摘要"),
                    extra={
                        "query": kw,
                        "category": category,
                        "raw": item,
                    },
                )
            )
        return out


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None
