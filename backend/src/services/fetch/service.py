"""
FetchService 统一门面 — 信息获取栈对外的唯一入口。

职责：
1. **路由**：调用 ``router.route()`` 选择 Tier
2. **合规**：黑名单硬拦截（403 + blocked_reason）；白名单状态写入审计
3. **限流**：per-domain QPS（默认 1/s）
4. **执行**：把 request 交给对应 Tier；失败时按降级链 L3→L2→L1 重试
5. **审计**：每次抓取写一条 AuditRecord（90d 保留）
6. **批量**：``fetch_batch()`` 受信号量并发控制

P6-B / P6-C / P6-D 接入点见模块尾部「Plugin 接入约定」一节。
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from loguru import logger

from src.services.fetch.compliance import (
    AuditLogger,
    AuditRecord,
    is_allowed,
    is_blocked,
)
from src.services.fetch.models import (
    ExtractConfig,
    ExtractFormat,
    FetchRequest,
    FetchResponse,
    FetchTier,
)
from src.services.fetch.rate_limiter import PerDomainRateLimiter
from src.services.fetch.robots import RobotsCache
from src.services.fetch.router import route as route_request
from src.services.fetch.tiers import (
    BaseTier,
    L1HttpTier,
    L2Crawl4AITier,
    L3HeadlessXTier,
)


class FetchService:
    """信息获取栈门面。

    通常使用全局单例 ``fetch_service``，不要在每个调用方 new 一份。
    """

    DEFAULT_DOMAIN_QPS = 1.0  # 礼貌默认值
    DEFAULT_BATCH_CONCURRENCY = 5

    def __init__(
        self,
        *,
        l1: BaseTier | None = None,
        l2: BaseTier | None = None,
        l3: BaseTier | None = None,
        rate_limiter: PerDomainRateLimiter | None = None,
        audit: AuditLogger | None = None,
        robots: RobotsCache | None = None,
        respect_robots: bool = True,
    ) -> None:
        self._tiers: dict[FetchTier, BaseTier] = {
            FetchTier.L1_HTTP: l1 or L1HttpTier(),
            FetchTier.L2_CRAWL4AI: l2 or L2Crawl4AITier(),
            FetchTier.L3_HEADLESSX: l3 or L3HeadlessXTier(),
        }
        self._rate_limiter = rate_limiter or PerDomainRateLimiter(
            default_qps=self.DEFAULT_DOMAIN_QPS,
        )
        self._audit = audit or AuditLogger()
        self._robots = robots or RobotsCache()
        self._respect_robots = respect_robots

    # ------------------------------------------------------------------ public

    async def fetch(self, request: FetchRequest) -> FetchResponse:
        """单次抓取（含合规 / 限流 / 路由 / 降级 / 审计）。"""
        start = time.monotonic()

        # 1. 合规黑名单硬拦截
        block = is_blocked(request.url)
        if block is not None:
            response = FetchResponse(
                request=request,
                status_code=403,
                tier_used=FetchTier.L1_HTTP,
                duration_ms=int((time.monotonic() - start) * 1000),
                error=block.message,
                blocked_reason=block.code,
            )
            await self._audit_record(response)
            return response

        # 2. robots.txt（可关闭，默认开）
        if self._respect_robots:
            try:
                allowed = await self._robots.can_fetch(request.url)
            except Exception:  # noqa: BLE001
                allowed = True
            if not allowed:
                response = FetchResponse(
                    request=request,
                    status_code=403,
                    tier_used=FetchTier.L1_HTTP,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error="robots.txt 禁止抓取",
                    blocked_reason="ROBOTS_DISALLOW",
                )
                await self._audit_record(response)
                return response

        # 3. per-domain 限流
        host = (urlparse(request.url).hostname or "").lower()
        if host:
            ok = await self._rate_limiter.acquire(host, timeout=request.timeout)
            if not ok:
                response = FetchResponse(
                    request=request,
                    status_code=429,
                    tier_used=FetchTier.L1_HTTP,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    error="rate_limited",
                )
                await self._audit_record(response)
                return response

        # 4. 路由 + 执行 + 降级链
        chosen_tier = route_request(request)
        response = await self._fetch_with_fallback(request, chosen_tier)

        # 5. 标注白名单状态（审计扩展信息）
        in_allowlist = is_allowed(request.url)
        if response.extracted is None:
            response.extracted = {}
        response.extracted.setdefault("_allowlist", in_allowlist)

        await self._audit_record(response)
        return response

    async def fetch_batch(
        self,
        requests: list[FetchRequest],
        concurrency: int = DEFAULT_BATCH_CONCURRENCY,
    ) -> list[FetchResponse]:
        """批量抓取（受信号量控制并发）。

        per-domain 限流仍生效，因此对同一域名的并发会被自然串行化。
        """
        sem = asyncio.Semaphore(max(1, concurrency))

        async def _bounded(req: FetchRequest) -> FetchResponse:
            async with sem:
                return await self.fetch(req)

        return await asyncio.gather(*[_bounded(r) for r in requests])

    async def fetch_with_extract(
        self,
        url: str,
        schema: dict[str, Any] | None = None,
        *,
        css_selectors: dict[str, str] | None = None,
        format: ExtractFormat = ExtractFormat.MARKDOWN,
        user_id: str | None = None,
        timeout: int = 30,
    ) -> FetchResponse:
        """一站式：抓 + 抽取，常用于业务侧快速调用。"""
        extract = ExtractConfig(
            css_selectors=css_selectors or {},
            schema=schema or {},
            format=format,
        )
        return await self.fetch(
            FetchRequest(
                url=url,
                extract=extract,
                user_id=user_id,
                timeout=timeout,
            )
        )

    async def aclose(self) -> None:
        for tier in self._tiers.values():
            try:
                await tier.aclose()
            except Exception:  # noqa: BLE001
                pass

    # ------------------------------------------------------------------ admin

    async def get_audit_logs(
        self,
        *,
        user_id: str | None = None,
        tier: FetchTier | None = None,
        blocked_only: bool = False,
        limit: int = 100,
    ) -> list[AuditRecord]:
        return await self._audit.query(
            user_id=user_id,
            tier=tier,
            blocked_only=blocked_only,
            limit=limit,
        )

    async def get_audit_stats(self) -> dict[str, int]:
        return await self._audit.stats()

    def check_compliance(self, url: str) -> dict[str, Any]:
        """检查域名合规性 — 不发请求，只返回判断。"""
        block = is_blocked(url)
        return {
            "url": url,
            "allowed": is_allowed(url),
            "blocked": block is not None,
            "block_reason": (
                {
                    "code": block.code,
                    "message": block.message,
                    "suggestion": block.suggestion,
                }
                if block
                else None
            ),
            "tier_hint": route_request(FetchRequest(url=url)).value,
        }

    # ------------------------------------------------------------------ internal

    async def _fetch_with_fallback(
        self,
        request: FetchRequest,
        chosen: FetchTier,
    ) -> FetchResponse:
        """按降级链 L3 → L2 → L1 / L2 → L1 尝试。

        降级触发条件：``response.error`` 非空 或 status_code >= 500。
        显式 ``tier_hint`` 不会被降级（信任调用方决策）。
        """
        chain = self._fallback_chain(chosen, has_hint=request.tier_hint is not None)
        last_response: FetchResponse | None = None
        for tier in chain:
            handler = self._tiers.get(tier)
            if handler is None:
                continue
            response = await handler.fetch(request)
            last_response = response
            if self._should_fallback(response):
                logger.debug(
                    f"[FetchService] {tier.value} 失败 ({response.status_code} / {response.error}), 尝试降级"
                )
                continue
            return response
        # 所有层都失败 — 返回最后一次响应
        assert last_response is not None
        return last_response

    @staticmethod
    def _fallback_chain(chosen: FetchTier, *, has_hint: bool) -> list[FetchTier]:
        if has_hint:
            return [chosen]
        if chosen == FetchTier.L3_HEADLESSX:
            return [FetchTier.L3_HEADLESSX, FetchTier.L2_CRAWL4AI, FetchTier.L1_HTTP]
        if chosen == FetchTier.L2_CRAWL4AI:
            return [FetchTier.L2_CRAWL4AI, FetchTier.L1_HTTP]
        return [FetchTier.L1_HTTP]

    @staticmethod
    def _should_fallback(response: FetchResponse) -> bool:
        if response.error:
            return True
        if response.status_code >= 500:
            return True
        return False

    async def _audit_record(self, response: FetchResponse) -> None:
        record = AuditRecord(
            request_ts=datetime.now(UTC),
            user_id=response.request.user_id,
            url=response.request.url,
            tier_used=response.tier_used,
            status_code=response.status_code,
            duration_ms=response.duration_ms,
            blocked_reason=response.blocked_reason,
            error=response.error,
        )
        await self._audit.record(record)


# 全局单例（业务侧 ``from src.services.fetch import fetch_service``）
fetch_service = FetchService()


# ---------------------------------------------------------------------------
# Plugin 接入约定（给 P6-B / P6-C / P6-D 阅读）
# ---------------------------------------------------------------------------
# - P6-B HeadlessX 实装：替换 ``L3HeadlessXTier``，
#   通过 ``FetchService(l3=YourHeadlessImpl())`` 注入或直接修改 default。
# - P6-C 法律源（裁判文书 / 北大法宝 / 公报）：
#   新建 ``backend/src/services/fetch/sources/legal/`` 子包，
#   每个源是一个使用 ``fetch_service`` 的 client，**不要新建 Tier**。
# - P6-D 电商 / 官方 API（Shopify / Amazon SP-API / 1688）：
#   新建 ``sources/ecommerce/``；如果是官方 API 走 L4 — 在这里新增
#   ``L4OfficialAPITier`` 并注册到 ``self._tiers``。
