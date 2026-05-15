"""
HeadlessX 客户端异常类型

按"可恢复 / 不可恢复"二分。FetchService 上层据此决定是否
fallback 到 L2 (crawl4ai) 还是直接返回失败。
"""

from __future__ import annotations


class HeadlessXError(Exception):
    """HeadlessX 通用基类异常 — 上层捕获用"""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        url: str | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.url = url
        self.body = body

    def __repr__(self) -> str:  # pragma: no cover - 调试用
        return (
            f"<{type(self).__name__} status={self.status_code} url={self.url!r} "
            f"msg={self.message!r}>"
        )


class HeadlessXAuthError(HeadlessXError):
    """401 / 403 — API Key 错误或权限不足。

    **不可重试** — 上层应直接放弃 L3，回退到 L2 而不是反复试。
    """


class HeadlessXTimeoutError(HeadlessXError):
    """请求超时（HTTP 504 / 客户端 timeout / Camoufox 渲染超时）。

    **可重试**（指数退避）；多次失败后由上层决定回退。
    """


class HeadlessXRateLimitError(HeadlessXError):
    """429 — 触发限流。

    **可重试**，建议遵循 Retry-After header；如果连续失败则回退。
    """

    def __init__(
        self,
        message: str,
        *,
        retry_after: float | None = None,
        **kw,
    ) -> None:
        super().__init__(message, **kw)
        self.retry_after = retry_after


class HeadlessXServerError(HeadlessXError):
    """5xx 服务端错误（503 / 502 / 500），HeadlessX 内部异常。

    **可重试**。
    """


class HeadlessXClientError(HeadlessXError):
    """4xx 客户端错误（参数非法等），**不可重试**。"""
