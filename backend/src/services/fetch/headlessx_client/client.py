"""
HeadlessXClient — 反检测抓取服务的 Python HTTP 客户端。

通过 HTTP API 调用 self-hosted HeadlessX (Camoufox-based) 实例。
HeadlessX 上游：https://github.com/saifyxpro/HeadlessX
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

import httpx

from .exceptions import (
    HeadlessXAuthError,
    HeadlessXClientError,
    HeadlessXError,
    HeadlessXRateLimitError,
    HeadlessXServerError,
    HeadlessXTimeoutError,
)
from .models import RenderRequest, RenderResult
from .retry import RetryConfig, with_retry

logger = logging.getLogger(__name__)


class HeadlessXClient:
    """HeadlessX HTTP 客户端。

    线程安全：单实例可复用，内部维护 httpx.AsyncClient 连接池。
    退出时务必调用 ``await client.aclose()`` 或用 ``async with`` 上下文。
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 60,
        retry_config: RetryConfig | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not base_url:
            raise ValueError("HeadlessX base_url 必填")
        if not api_key:
            raise ValueError("HeadlessX api_key 必填")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retry_config = retry_config or RetryConfig()
        # 注入便于测试 mock；否则按需懒构建
        self._client: httpx.AsyncClient | None = http_client
        self._owns_client = http_client is None

    # ============ 生命周期 ============

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"x-api-key": self.api_key},
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> HeadlessXClient:
        await self._get_client()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.aclose()

    # ============ 公共 API ============

    async def render(
        self,
        url: str,
        wait_for_selector: str | None = None,
        wait_ms: int = 0,
        screenshot: bool = False,
        full_page: bool = True,
        viewport: tuple[int, int] = (1920, 1080),
        user_agent: str | None = None,
        proxy: str | None = None,
        cookies: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
        execute_js: str | None = None,
    ) -> RenderResult:
        """渲染目标 URL，返回完整 HTML（可选截图）。

        Args:
            url: 目标 URL
            wait_for_selector: 等待该 CSS 选择器出现后再抓取
            wait_ms: 额外等待毫秒数
            screenshot: 是否同时截图
            full_page: 截全页（False 仅截 viewport）
            viewport: (宽, 高) 像素
            user_agent: 自定义 UA（None=Camoufox 默认随机）
            proxy: socks5/http proxy URI
            cookies: 预置 cookies
            headers: 额外请求头
            execute_js: 渲染完成后执行的 JS

        Returns:
            RenderResult — html / screenshot / cookies / bot_score 等

        Raises:
            HeadlessXAuthError: 401/403
            HeadlessXTimeoutError: 超时
            HeadlessXRateLimitError: 429
            HeadlessXServerError: 5xx
            HeadlessXClientError: 4xx 参数错
        """
        req = RenderRequest(
            url=url,
            wait_for_selector=wait_for_selector,
            wait_ms=wait_ms,
            screenshot=screenshot,
            full_page=full_page,
            viewport_width=viewport[0],
            viewport_height=viewport[1],
            user_agent=user_agent,
            proxy=proxy,
            cookies=cookies or [],
            headers=headers or {},
            execute_js=execute_js,
            return_pdf=False,
        )

        async def _do() -> RenderResult:
            return await self._render_once(req)

        return await with_retry(_do, self.retry_config)

    async def screenshot(
        self,
        url: str,
        full_page: bool = True,
        viewport: tuple[int, int] = (1920, 1080),
        wait_ms: int = 0,
        wait_for_selector: str | None = None,
        **kw: Any,
    ) -> bytes:
        """仅返回截图字节流（PNG）。

        本质是 render(..., screenshot=True) 后丢弃 HTML。
        """
        result = await self.render(
            url,
            screenshot=True,
            full_page=full_page,
            viewport=viewport,
            wait_ms=wait_ms,
            wait_for_selector=wait_for_selector,
            **kw,
        )
        if result.screenshot_png is None:
            raise HeadlessXError(
                "HeadlessX 未返回截图字节",
                status_code=result.status_code,
                url=url,
            )
        return result.screenshot_png

    async def pdf(
        self,
        url: str,
        viewport: tuple[int, int] = (1920, 1080),
        wait_ms: int = 0,
        wait_for_selector: str | None = None,
        **kw: Any,
    ) -> bytes:
        """渲染为 PDF。"""
        req = RenderRequest(
            url=url,
            wait_for_selector=wait_for_selector,
            wait_ms=wait_ms,
            screenshot=False,
            full_page=True,
            viewport_width=viewport[0],
            viewport_height=viewport[1],
            return_pdf=True,
        )

        async def _do() -> RenderResult:
            return await self._render_once(req, expect_pdf=True)

        result = await with_retry(_do, self.retry_config)
        if result.pdf_bytes is None:
            raise HeadlessXError(
                "HeadlessX 未返回 PDF 字节",
                status_code=result.status_code,
                url=url,
            )
        return result.pdf_bytes

    async def health(self) -> dict[str, Any]:
        """健康检查，调用 HeadlessX /health。

        不做重试 — 健康检查本身就是探活。
        """
        client = await self._get_client()
        try:
            resp = await client.get("/health")
        except httpx.TimeoutException as exc:
            raise HeadlessXTimeoutError(
                "HeadlessX /health 超时",
                url="/health",
            ) from exc
        except httpx.HTTPError as exc:
            raise HeadlessXError(
                f"HeadlessX /health 网络错误: {exc}",
                url="/health",
            ) from exc

        if resp.status_code >= 500:
            raise HeadlessXServerError(
                f"HeadlessX /health 5xx: {resp.status_code}",
                status_code=resp.status_code,
            )
        try:
            return resp.json()
        except ValueError:
            return {"status": "ok" if resp.is_success else "error", "raw": resp.text}

    # ============ 内部 ============

    async def _render_once(
        self,
        req: RenderRequest,
        expect_pdf: bool = False,
    ) -> RenderResult:
        """单次渲染调用 — 不带重试，由 with_retry 包装。"""
        client = await self._get_client()
        payload = req.to_payload()
        started = time.perf_counter()

        try:
            resp = await client.post("/render", json=payload)
        except httpx.TimeoutException as exc:
            raise HeadlessXTimeoutError(
                f"HeadlessX /render 超时 (timeout={self.timeout}s)",
                url=req.url,
            ) from exc
        except httpx.HTTPError as exc:
            # 网络层错误归类为 server error 以触发重试
            raise HeadlessXServerError(
                f"HeadlessX /render 网络错误: {exc}",
                url=req.url,
            ) from exc

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        self._raise_for_status(resp, req.url)

        return self._parse_response(resp, req, elapsed_ms, expect_pdf)

    @staticmethod
    def _raise_for_status(resp: httpx.Response, url: str) -> None:
        """把 HTTP 状态码翻译成具体异常类。"""
        sc = resp.status_code
        if sc < 400:
            return
        body_preview = resp.text[:512] if resp.text else ""
        if sc in (401, 403):
            raise HeadlessXAuthError(
                f"HeadlessX 认证失败 ({sc}) — 检查 HEADLESSX_API_KEY",
                status_code=sc,
                url=url,
                body=body_preview,
            )
        if sc == 429:
            retry_after = None
            ra_header = resp.headers.get("Retry-After")
            if ra_header:
                try:
                    retry_after = float(ra_header)
                except ValueError:
                    retry_after = None
            raise HeadlessXRateLimitError(
                f"HeadlessX 触发限流 ({sc})",
                retry_after=retry_after,
                status_code=sc,
                url=url,
                body=body_preview,
            )
        if sc == 408 or sc == 504:
            raise HeadlessXTimeoutError(
                f"HeadlessX 渲染超时 ({sc})",
                status_code=sc,
                url=url,
                body=body_preview,
            )
        if 500 <= sc < 600:
            raise HeadlessXServerError(
                f"HeadlessX 服务端错误 ({sc})",
                status_code=sc,
                url=url,
                body=body_preview,
            )
        # 4xx 兜底
        raise HeadlessXClientError(
            f"HeadlessX 客户端错误 ({sc})",
            status_code=sc,
            url=url,
            body=body_preview,
        )

    @staticmethod
    def _parse_response(
        resp: httpx.Response,
        req: RenderRequest,
        elapsed_ms: int,
        expect_pdf: bool,
    ) -> RenderResult:
        """解析 HeadlessX JSON 响应为 RenderResult。

        约定 HeadlessX 返回 JSON：
            {
              "url": "...",
              "finalUrl": "...",
              "statusCode": 200,
              "html": "...",
              "screenshot": "<base64 PNG>",   # 可选
              "pdf": "<base64 PDF>",          # 可选
              "cookies": [...],
              "durationMs": 1234,
              "botScore": 0.12                # 可选
            }
        """
        try:
            data = resp.json()
        except ValueError as exc:
            raise HeadlessXServerError(
                f"HeadlessX 返回非 JSON: {exc}",
                status_code=resp.status_code,
                url=req.url,
                body=resp.text[:512],
            ) from exc

        screenshot_b64 = data.get("screenshot")
        screenshot_bytes = (
            base64.b64decode(screenshot_b64) if screenshot_b64 else None
        )
        pdf_b64 = data.get("pdf")
        pdf_bytes = base64.b64decode(pdf_b64) if pdf_b64 else None

        if expect_pdf and pdf_bytes is None:
            raise HeadlessXServerError(
                "HeadlessX 应返回 PDF 但 payload 中无 pdf 字段",
                status_code=resp.status_code,
                url=req.url,
            )

        return RenderResult(
            url=data.get("url", req.url),
            final_url=data.get("finalUrl", data.get("url", req.url)),
            status_code=int(data.get("statusCode", resp.status_code)),
            html=data.get("html", ""),
            screenshot_png=screenshot_bytes,
            pdf_bytes=pdf_bytes,
            cookies=list(data.get("cookies", [])),
            duration_ms=int(data.get("durationMs", elapsed_ms)),
            bot_score=_safe_float(data.get("botScore")),
        )


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
