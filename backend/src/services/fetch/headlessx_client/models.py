"""
HeadlessX 客户端请求/响应数据模型。

刻意用 dataclass 而非 pydantic — 客户端是底层抓取层，
不希望被 pydantic 的校验耗时拖慢热路径。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RenderRequest:
    """HeadlessX /render API 请求体（内部使用）。

    与 HeadlessX 上游 OpenAPI 字段对齐：
    https://github.com/saifyxpro/HeadlessX/blob/main/docs/api.md
    """

    url: str
    wait_for_selector: str | None = None
    wait_ms: int = 0
    screenshot: bool = False
    full_page: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str | None = None
    proxy: str | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    execute_js: str | None = None
    return_pdf: bool = False

    def to_payload(self) -> dict[str, Any]:
        """转为 HeadlessX HTTP API JSON 体。仅包含非 None / 非空字段。"""
        payload: dict[str, Any] = {
            "url": self.url,
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "fullPage": self.full_page,
            "screenshot": self.screenshot,
            "pdf": self.return_pdf,
        }
        if self.wait_for_selector:
            payload["waitForSelector"] = self.wait_for_selector
        if self.wait_ms:
            payload["waitMs"] = self.wait_ms
        if self.user_agent:
            payload["userAgent"] = self.user_agent
        if self.proxy:
            payload["proxy"] = self.proxy
        if self.cookies:
            payload["cookies"] = self.cookies
        if self.headers:
            payload["headers"] = self.headers
        if self.execute_js:
            payload["executeJs"] = self.execute_js
        return payload


@dataclass
class RenderResult:
    """HeadlessX 渲染结果。

    bot_score: 0.0-1.0 区间。HeadlessX/Camoufox 自检（或上游 WAF
    回应）给出的"我看起来像 bot"分数。
    - 0.0 = 完全像真人；
    - 1.0 = 已被识别为 bot；
    - None = HeadlessX 未返回该字段（旧版本或未启用检测）。
    """

    url: str
    final_url: str
    status_code: int
    html: str
    screenshot_png: bytes | None = None
    pdf_bytes: bytes | None = None
    cookies: list[dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    bot_score: float | None = None

    @property
    def is_blocked(self) -> bool:
        """简单检测：HTTP 4xx 或 bot_score >= 0.7 视作被拦截。"""
        if self.status_code >= 400:
            return True
        if self.bot_score is not None and self.bot_score >= 0.7:
            return True
        return False
