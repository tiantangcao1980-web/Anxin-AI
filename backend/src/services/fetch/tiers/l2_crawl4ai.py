"""
L2 crawl4ai 抓取 — 包装现有 ``src.services.crawl4ai_service.crawl4ai_service``。

边界：
- **绝不修改**底层 ``crawl4ai_service`` — 只在这里转换 request/response 格式
- 已有 service 自带 httpx 降级，所以即使 crawl4ai 不可用也不影响 L2 调用
- ``ExtractConfig.schema``（CSS-style schema）会转给 ``extract_structured()``
"""

from __future__ import annotations

import time
from typing import Any

from src.services.fetch.models import (
    FetchRequest,
    FetchResponse,
    FetchTier,
)
from src.services.fetch.ssrf_guard import SSRFError, validate_url
from src.services.fetch.tiers.base import BaseTier


class L2Crawl4AITier(BaseTier):
    """L2 crawl4ai 适配。"""

    tier = FetchTier.L2_CRAWL4AI

    def __init__(self, *, service: Any | None = None) -> None:
        # 延迟 import — 单测可注入 mock 而不触发真实 crawl4ai
        if service is None:
            from src.services.crawl4ai_service import crawl4ai_service  # noqa: WPS433

            service = crawl4ai_service
        self._service = service

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        start = time.monotonic()

        # SSRF 防护：crawl4ai 内部 headless 浏览器同样能访问内网 / 元数据
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

        # crawl4ai 仅支持 GET，POST 等显式降级到 L1（由 FetchService 处理）
        if request.method.upper() != "GET":
            return FetchResponse(
                request=request,
                status_code=0,
                tier_used=self.tier,
                duration_ms=int((time.monotonic() - start) * 1000),
                error="L2 crawl4ai 不支持非 GET 方法，请显式 tier_hint=L1_HTTP",
            )

        try:
            # 优先结构化抽取
            if request.extract is not None and request.extract.schema:
                result = await self._service.extract_structured(
                    url=request.url,
                    schema=request.extract.schema,
                    timeout=request.timeout,
                )
                if result.get("success"):
                    return FetchResponse(
                        request=request,
                        status_code=200,
                        tier_used=self.tier,
                        duration_ms=int((time.monotonic() - start) * 1000),
                        extracted=result.get("data") or {},
                    )
                return FetchResponse(
                    request=request,
                    status_code=502,
                    tier_used=self.tier,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error=result.get("error") or "structured_extract_failed",
                )

            # 普通抓取
            result = await self._service.crawl_url(
                url=request.url,
                timeout=request.timeout,
            )
            if result.get("success"):
                text = result.get("content") or ""
                html = result.get("html") or ""
                return FetchResponse(
                    request=request,
                    status_code=200,
                    headers={},
                    body=html.encode("utf-8", errors="ignore"),
                    text=text,
                    tier_used=self.tier,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    extracted={
                        "title": result.get("title", ""),
                        "links": result.get("links", []),
                        "metadata": result.get("metadata", {}),
                        "_source": result.get("source"),
                    },
                )

            return FetchResponse(
                request=request,
                status_code=502,
                tier_used=self.tier,
                duration_ms=int((time.monotonic() - start) * 1000),
                error=result.get("error") or "crawl_failed",
            )
        except Exception as e:  # noqa: BLE001
            return FetchResponse(
                request=request,
                status_code=0,
                tier_used=self.tier,
                duration_ms=int((time.monotonic() - start) * 1000),
                error=f"l2_exception: {e}",
            )

    async def aclose(self) -> None:
        # 复用全局实例，不在这里关闭 — 进程退出由全局 service 自己 cleanup
        return None
