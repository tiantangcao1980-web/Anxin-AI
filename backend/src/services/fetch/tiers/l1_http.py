"""
L1 纯 HTTP 抓取 — httpx + selectolax / lxml。

适用场景：
- 政府 / 司法静态页面（基本无 JS、无反爬）
- RSS / Atom / sitemap 等 XML
- 简单 HTML 内容页

解析策略（按优先级）：
1. ``selectolax``（基于 modest-engine，比 BS4 快 5-10x）
2. ``lxml``（XPath 用例）
3. ``BeautifulSoup4``（已有依赖，作为兜底）

任意解析库缺失都不影响 raw fetch 工作 — extract 阶段会跳过。
"""

from __future__ import annotations

import time
from typing import Any

import httpx
from loguru import logger

from src.services.fetch.models import (
    ExtractConfig,
    ExtractFormat,
    FetchRequest,
    FetchResponse,
    FetchTier,
)
from src.services.fetch.ssrf_guard import (
    MAX_REDIRECT_DEPTH,
    SSRFError,
    validate_redirect,
    validate_url,
)
from src.services.fetch.tiers.base import BaseTier

try:
    from selectolax.parser import HTMLParser as _SelectolaxParser
    _HAS_SELECTOLAX = True
except ImportError:  # pragma: no cover
    _HAS_SELECTOLAX = False
    _SelectolaxParser = None  # type: ignore[assignment]

try:
    from lxml import html as _lxml_html
    _HAS_LXML = True
except ImportError:  # pragma: no cover
    _HAS_LXML = False
    _lxml_html = None  # type: ignore[assignment]

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:  # pragma: no cover
    _HAS_BS4 = False
    BeautifulSoup = None  # type: ignore[assignment]


_DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; AnxinFetcher/1.0; +https://anxin.legal/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}


class L1HttpTier(BaseTier):
    """L1 纯 HTTP + 静态解析。"""

    tier = FetchTier.L1_HTTP

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        default_headers: dict[str, str] | None = None,
    ) -> None:
        self._client = client
        self._default_headers = {**_DEFAULT_HEADERS, **(default_headers or {})}
        self._owns_client = client is None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            # SSRF 防护：禁用自动 redirect，由 fetch() 手动 chain 校验每一跳
            self._client = httpx.AsyncClient(
                follow_redirects=False,
                headers=self._default_headers,
            )
        return self._client

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        start = time.monotonic()

        # SSRF 校验：协议 / 域名 / IP 黑名单 + DNS rebinding 兜底
        try:
            validate_url(request.url)
        except SSRFError as exc:
            return FetchResponse(
                request=request,
                status_code=400,
                tier_used=self.tier,
                duration_ms=int((time.monotonic() - start) * 1000),
                error=f"ssrf_blocked:{exc.code}",
                blocked_reason=f"SSRF:{exc.code}",
            )

        client = await self._get_client()
        merged_headers = {**self._default_headers, **request.headers}

        current_url = request.url
        resp: httpx.Response | None = None

        try:
            for hop in range(MAX_REDIRECT_DEPTH + 1):
                resp = await client.request(
                    method=request.method,
                    url=current_url,
                    headers=merged_headers,
                    content=request.body,
                    timeout=request.timeout,
                )
                # 非 3xx → 终态
                if not (300 <= resp.status_code < 400):
                    break
                next_location = resp.headers.get("location")
                if not next_location:
                    break
                # 解析为绝对 URL
                next_url = str(httpx.URL(current_url).join(next_location))
                # SSRF：每一跳重新校验（含协议 / IP / 元数据 / 内网）
                try:
                    validate_redirect(next_url)
                except SSRFError as exc:
                    return FetchResponse(
                        request=request,
                        status_code=400,
                        tier_used=self.tier,
                        duration_ms=int((time.monotonic() - start) * 1000),
                        error=f"ssrf_blocked:{exc.code}",
                        blocked_reason=f"SSRF:{exc.code}",
                    )
                current_url = next_url
            else:
                # for-else：循环跑满未 break = 超出最大重定向数
                return FetchResponse(
                    request=request,
                    status_code=400,
                    tier_used=self.tier,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error="ssrf_blocked:redirect_depth",
                    blocked_reason="SSRF:redirect_depth",
                )
        except httpx.TimeoutException as e:
            return FetchResponse(
                request=request,
                status_code=0,
                tier_used=self.tier,
                duration_ms=int((time.monotonic() - start) * 1000),
                error=f"timeout: {e}",
            )
        except httpx.HTTPError as e:
            return FetchResponse(
                request=request,
                status_code=0,
                tier_used=self.tier,
                duration_ms=int((time.monotonic() - start) * 1000),
                error=f"http_error: {e}",
            )

        assert resp is not None  # noqa: S101 — 循环至少跑一次

        text: str | None = None
        try:
            text = resp.text
        except Exception:  # noqa: BLE001 — 二进制响应
            text = None

        extracted: dict[str, Any] | None = None
        if request.extract is not None and text:
            extracted = self._extract(text, request.extract)

        return FetchResponse(
            request=request,
            status_code=resp.status_code,
            headers=dict(resp.headers),
            body=resp.content,
            text=text,
            tier_used=self.tier,
            duration_ms=int((time.monotonic() - start) * 1000),
            extracted=extracted,
        )

    # ------------------------------------------------------------------ extract

    def _extract(self, html: str, config: ExtractConfig) -> dict[str, Any]:
        """根据 ExtractConfig 抽取结构化数据。"""
        out: dict[str, Any] = {}

        # 1. CSS 选择器（优先 selectolax）
        if config.css_selectors:
            out.update(self._extract_css(html, config.css_selectors))

        # 2. XPath（依赖 lxml）
        if config.xpath:
            out.update(self._extract_xpath(html, config.xpath))

        # 3. format 转换
        if config.format == ExtractFormat.TEXT:
            out["_text"] = self._html_to_text(html)
        elif config.format == ExtractFormat.MARKDOWN:
            out["_markdown"] = self._html_to_text(html)  # 简化：复用 text
        elif config.format == ExtractFormat.HTML:
            out["_html"] = html

        return out

    def _extract_css(self, html: str, selectors: dict[str, str]) -> dict[str, Any]:
        if _HAS_SELECTOLAX:
            try:
                tree = _SelectolaxParser(html)
                return {
                    field: [n.text(strip=True) for n in tree.css(sel)]
                    for field, sel in selectors.items()
                }
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[L1] selectolax 失败: {e}, 回退 BS4")

        if _HAS_BS4:
            try:
                soup = BeautifulSoup(html, "html.parser")
                return {
                    field: [el.get_text(strip=True) for el in soup.select(sel)]
                    for field, sel in selectors.items()
                }
            except Exception as e:  # noqa: BLE001
                logger.debug(f"[L1] BS4 失败: {e}")

        return {field: [] for field in selectors}

    def _extract_xpath(self, html: str, xpaths: dict[str, str]) -> dict[str, Any]:
        if not _HAS_LXML:
            return {field: [] for field in xpaths}
        try:
            tree = _lxml_html.fromstring(html)
            out: dict[str, Any] = {}
            for field, xp in xpaths.items():
                try:
                    nodes = tree.xpath(xp)
                    out[field] = [
                        n.text_content().strip() if hasattr(n, "text_content") else str(n).strip()
                        for n in nodes
                    ]
                except Exception:  # noqa: BLE001
                    out[field] = []
            return out
        except Exception as e:  # noqa: BLE001
            logger.debug(f"[L1] lxml XPath 失败: {e}")
            return {field: [] for field in xpaths}

    def _html_to_text(self, html: str) -> str:
        if _HAS_SELECTOLAX:
            try:
                return _SelectolaxParser(html).body.text(separator="\n", strip=True)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass
        if _HAS_BS4:
            try:
                return BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
            except Exception:  # noqa: BLE001
                pass
        # 极简兜底：粗暴去标签
        import re
        return re.sub(r"<[^>]+>", "", html).strip()

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None
