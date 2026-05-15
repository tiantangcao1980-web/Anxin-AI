"""
L3 反检测层 — HeadlessX 接入。

行为约定：
- 401/403 → 抛 HeadlessXAuthError，让 service 直接降级且告警
- 超时/限流/5xx → 客户端已做指数退避，仍失败时返回 None 让 service 走 fallback
- 成功但 bot_score >= 0.7 → 仍返回结果，但 FetchResponse.bot_score 透传给 service
  让 service 决定是否再换 proxy 重试

配置来源：core/config.py 的 HEADLESSX_* 字段。
若 HEADLESSX_BASE_URL 为空 → 视为未启用，fetch() 立即返回 None。
"""

from __future__ import annotations

import logging

from src.core.config import settings

from ..headlessx_client import (
    HeadlessXAuthError,
    HeadlessXClient,
    HeadlessXClientError,
    HeadlessXError,
    HeadlessXRateLimitError,
    HeadlessXServerError,
    HeadlessXTimeoutError,
    RetryConfig,
)
from ..ssrf_guard import SSRFError, validate_url
from .base import BaseTier, FetchRequest, FetchResponse, TierName

logger = logging.getLogger(__name__)


class HeadlessXTier(BaseTier):
    """FetchService 的 L3 (反检测) 实现。"""

    name = TierName.L3_HEADLESSX

    def __init__(
        self,
        client: HeadlessXClient | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        # 允许显式注入（测试场景）；否则从 settings 读取
        self._injected_client = client
        self._base_url = base_url if base_url is not None else settings.HEADLESSX_BASE_URL
        self._api_key = api_key if api_key is not None else settings.HEADLESSX_API_KEY
        self._timeout = timeout if timeout is not None else settings.HEADLESSX_TIMEOUT
        self._client: HeadlessXClient | None = client

    @property
    def is_enabled(self) -> bool:
        """配置完整时才认为启用。"""
        return bool(self._base_url and self._api_key)

    async def _ensure_client(self) -> HeadlessXClient | None:
        if self._client is not None:
            return self._client
        if not self.is_enabled:
            return None
        self._client = HeadlessXClient(
            base_url=self._base_url,
            api_key=self._api_key,
            timeout=self._timeout,
            retry_config=RetryConfig(max_attempts=3, base_delay=1.0, max_delay=15.0),
        )
        return self._client

    async def fetch(self, request: FetchRequest) -> FetchResponse | None:
        """执行 L3 抓取。

        Returns:
            FetchResponse — 成功（包括被 bot 检测到的成功）
            None         — 不可用 / 重试耗尽 / 超时 → 让 service 回退到 L2
        Raises:
            HeadlessXAuthError — Key 错；service 应停用 L3 并告警，不再重试本层
        """
        client = await self._ensure_client()
        if client is None:
            logger.debug("L3 HeadlessX 未配置，跳过")
            return None

        # SSRF 防护：headless 渲染同样能命中内网 / 云元数据。
        # 命中即返回 None，让 service 走兜底（L1/L2 也带 SSRF guard 会再次拒绝）。
        try:
            validate_url(request.url)
        except SSRFError as exc:
            logger.warning("L3 HeadlessX SSRF blocked url=%s code=%s", request.url, exc.code)
            return None

        try:
            result = await client.render(
                url=request.url,
                wait_for_selector=request.wait_for_selector,
                wait_ms=request.wait_ms,
                screenshot=request.screenshot,
                full_page=request.full_page,
                viewport=request.viewport,
                user_agent=request.user_agent,
                proxy=request.proxy,
                cookies=list(request.cookies) if request.cookies else None,
                headers=dict(request.headers) if request.headers else None,
                execute_js=request.execute_js,
            )
        except HeadlessXAuthError:
            # 不可恢复，向上抛 → service 应禁用 L3 并告警
            logger.error("L3 HeadlessX 认证失败 — 检查 HEADLESSX_API_KEY")
            raise
        except (HeadlessXTimeoutError, HeadlessXRateLimitError, HeadlessXServerError) as exc:
            # 重试已耗尽 → 让 service 回退
            logger.warning(
                "L3 HeadlessX 重试耗尽 url=%s reason=%s — fallback",
                request.url,
                type(exc).__name__,
            )
            return None
        except HeadlessXClientError as exc:
            # 4xx 参数错 — 标记为失败但返回 FetchResponse 便于审计
            logger.warning(
                "L3 HeadlessX 客户端错误 url=%s status=%s",
                request.url,
                exc.status_code,
            )
            return FetchResponse(
                url=request.url,
                final_url=request.url,
                status_code=exc.status_code or 400,
                html="",
                tier=self.name,
                success=False,
                error=str(exc),
            )
        except HeadlessXError as exc:
            logger.warning(
                "L3 HeadlessX 未分类错误 url=%s err=%r — fallback",
                request.url,
                exc,
            )
            return None

        return FetchResponse(
            url=result.url,
            final_url=result.final_url,
            status_code=result.status_code,
            html=result.html,
            tier=self.name,
            success=result.status_code < 400,
            duration_ms=result.duration_ms,
            bot_score=result.bot_score,
            screenshot_png=result.screenshot_png,
            pdf_bytes=result.pdf_bytes,
            cookies=result.cookies,
        )

    async def close(self) -> None:
        if self._client is not None and self._injected_client is None:
            await self._client.aclose()
            self._client = None


# P8-A 兼容别名：``__init__.py`` 与 ``service.py`` 引用 ``L3HeadlessXTier``。
# P6-B 实装时把类命名成了 ``HeadlessXTier``，此处补齐别名以恢复 import 链。
L3HeadlessXTier = HeadlessXTier
