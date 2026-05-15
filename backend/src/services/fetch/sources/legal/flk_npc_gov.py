"""国家法律法规数据库（flk.npc.gov.cn）数据源。

公开站点，提供宪法/法律/行政法规/部门规章/地方法规等的检索 API。
本实现：
- 通过 httpx.AsyncClient 调 ``/api/?type=...&searchType=...&sortTr=...&pageNo=...&pageSize=...``
- selectolax 用于（少量）HTML 提取分支（站点 API 主体返回 JSON，HTML 仅用于 fallback）
- 限流由调用方传入 ``rate_limiter``（P6-A 提供）；缺省回退为 1 req/s 的内置 token bucket
- robots.txt 校验：只校验目标 host 是否允许 ``/api/`` 路径，命中拒绝则抛 ComplianceError
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, ClassVar
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import httpx

try:  # selectolax 用于轻量 HTML 解析
    from selectolax.parser import HTMLParser  # type: ignore
except ImportError:  # pragma: no cover
    HTMLParser = None  # type: ignore[assignment]

from .base import (
    BaseLegalSource,
    ComplianceError,
    LawSearchQuery,
    LawSearchResult,
    LawStatus,
    LawType,
)

logger = logging.getLogger(__name__)


# 简易令牌桶：单进程内 1 req/s
@dataclass
class _TokenBucket:
    rate_per_sec: float = 1.0
    _last_call: float = 0.0
    _lock: asyncio.Lock = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            interval = 1.0 / self.rate_per_sec
            elapsed = time.monotonic() - self._last_call
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
            self._last_call = time.monotonic()


# robots.txt 校验缓存
_robots_cache: dict[str, RobotFileParser] = {}


def _check_robots(base_url: str, path: str, user_agent: str = "*") -> bool:
    """检查 robots.txt 是否允许访问指定路径。"""
    try:
        parser = _robots_cache.get(base_url)
        if parser is None:
            parser = RobotFileParser()
            parser.set_url(urljoin(base_url, "/robots.txt"))
            try:
                parser.read()
            except Exception as exc:  # pragma: no cover
                logger.warning("flk_npc_gov: 无法读取 robots.txt: %s", exc)
                return True  # 读不到就放行，但外层仍受 BANNED_HOSTS 兜底
            _robots_cache[base_url] = parser
        return parser.can_fetch(user_agent, urljoin(base_url, path))
    except Exception as exc:  # pragma: no cover
        logger.warning("flk_npc_gov: robots 校验异常: %s", exc)
        return True


class FlkNpcGovSource(BaseLegalSource):
    """国家法律法规数据库公开数据源。"""

    source_id: ClassVar[str] = "flk_npc_gov"
    display_name: ClassVar[str] = "国家法律法规数据库"
    requires_credentials: ClassVar[bool] = False
    base_host: ClassVar[str] = "flk.npc.gov.cn"

    BASE_URL: ClassVar[str] = "https://flk.npc.gov.cn"
    SEARCH_PATH: ClassVar[str] = "/api/"
    DETAIL_PATH: ClassVar[str] = "/api/detail"

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        rate_limiter: Callable[[], Awaitable[None]] | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._client = client
        self._owned_client = client is None
        self._timeout = timeout
        # P6-A 注入限流器优先；否则用内置 1 req/s
        if rate_limiter is None:
            bucket = _TokenBucket(rate_per_sec=1.0)
            self._rate_limit = bucket.acquire
        else:
            self._rate_limit = rate_limiter

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

    # ---- BaseLegalSource 接口 ----

    async def search(self, query: LawSearchQuery) -> list[LawSearchResult]:
        url = urljoin(self.BASE_URL, self.SEARCH_PATH)
        # 合规护栏：URL 校验 + robots 校验
        self._ensure_compliant(url)
        if not _check_robots(self.BASE_URL, self.SEARCH_PATH):
            raise ComplianceError(
                f"flk_npc_gov: robots.txt 拒绝访问 {self.SEARCH_PATH}"
            )

        params = self._build_search_params(query)
        await self._rate_limit()
        client = await self._get_client()
        resp = await client.get(url, params=params)
        resp.raise_for_status()

        return self._parse_search_response(resp)

    async def get_full_text(self, law_id: str) -> str:
        if not law_id:
            raise ValueError("law_id 不能为空")
        url = urljoin(self.BASE_URL, self.DETAIL_PATH)
        self._ensure_compliant(url)
        if not _check_robots(self.BASE_URL, self.DETAIL_PATH):
            raise ComplianceError(
                f"flk_npc_gov: robots.txt 拒绝访问 {self.DETAIL_PATH}"
            )

        await self._rate_limit()
        client = await self._get_client()
        resp = await client.get(url, params={"id": law_id})
        resp.raise_for_status()

        # 站点 API 多数情形返回 JSON，包含 body 字段；少数情形返回 HTML
        ctype = resp.headers.get("content-type", "")
        if "json" in ctype:
            data = resp.json()
            return (
                data.get("result", {}).get("body")
                or data.get("body")
                or data.get("content")
                or ""
            )
        # HTML fallback
        if HTMLParser is None:
            return resp.text
        tree = HTMLParser(resp.text)
        node = tree.css_first(".law-content") or tree.css_first("body")
        return node.text(strip=True) if node else resp.text

    async def health_check(self) -> bool:
        # 仅做连通性 ping；失败回 False，不抛
        try:
            self._ensure_compliant(self.BASE_URL)
            await self._rate_limit()
            client = await self._get_client()
            resp = await client.get(self.BASE_URL, timeout=5.0)
            return resp.status_code < 500
        except Exception as exc:  # pragma: no cover
            logger.warning("flk_npc_gov.health_check failed: %s", exc)
            return False

    # ---- 内部解析 ----

    def _build_search_params(self, query: LawSearchQuery) -> dict[str, Any]:
        page_no = (query.offset // max(query.limit, 1)) + 1
        params: dict[str, Any] = {
            "type": self._map_law_type(query.law_type),
            "searchType": "title;accurate",
            "sortTr": "f_bbrq_s;desc",
            "gbrqStart": query.date_from.isoformat() if query.date_from else "",
            "gbrqEnd": query.date_to.isoformat() if query.date_to else "",
            "sxrqStart": "",
            "sxrqEnd": "",
            "sort": "true",
            "page": page_no,
            "size": query.limit,
            "_": int(time.time() * 1000),
            "fgbt": query.keyword,  # 法规标题关键字
        }
        if query.jurisdiction:
            params["jurisdiction"] = query.jurisdiction
        return params

    @staticmethod
    def _map_law_type(law_type: str | None) -> str:
        # 站点 type 取值: flfg=法律法规, xzfg=行政法规, sfjs=司法解释, ...
        mapping = {
            LawType.LAW.value: "flfg",
            LawType.REGULATION.value: "xzfg",
            LawType.JUDICIAL_INTERPRETATION.value: "sfjs",
            LawType.CASE.value: "alk",
        }
        return mapping.get(law_type or "", "")

    def _parse_search_response(self, resp: httpx.Response) -> list[LawSearchResult]:
        try:
            data = resp.json()
        except ValueError:
            # 非 JSON：返回空，避免误吃 HTML 错误页
            logger.warning("flk_npc_gov: 非 JSON 响应 content-type=%s", resp.headers.get("content-type"))
            return []

        items = (
            data.get("result", {}).get("data")
            or data.get("data")
            or []
        )
        results: list[LawSearchResult] = []
        for item in items:
            results.append(
                LawSearchResult(
                    source=self.source_id,
                    law_id=str(item.get("id") or item.get("lawId") or ""),
                    title=str(item.get("title") or item.get("name") or ""),
                    law_type=str(item.get("type") or LawType.LAW.value),
                    issuing_authority=str(item.get("office") or item.get("issuing") or ""),
                    issued_date=_parse_date(item.get("publish") or item.get("issuedDate")),
                    effective_date=_parse_date(item.get("expiry") or item.get("effectiveDate")),
                    status=_map_status(item.get("status")),
                    full_text_url=urljoin(
                        self.BASE_URL,
                        f"/detail2.html?id={item.get('id', '')}",
                    ),
                    summary=item.get("summary"),
                    extra={"raw": item},
                )
            )
        return results


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _map_status(value: Any) -> str:
    if not value:
        return LawStatus.UNKNOWN.value
    text = str(value)
    if "废" in text or "abolish" in text.lower():
        return LawStatus.ABOLISHED.value
    if "修" in text or "amend" in text.lower():
        return LawStatus.AMENDED.value
    if "有效" in text or "active" in text.lower():
        return LawStatus.ACTIVE.value
    return LawStatus.UNKNOWN.value
