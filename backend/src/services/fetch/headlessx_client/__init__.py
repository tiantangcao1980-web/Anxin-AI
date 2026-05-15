"""
HeadlessX Python 客户端。

通过 HTTP 调用 self-hosted HeadlessX (Camoufox-based 反检测抓取)
作为 FetchService 的 L3 (反检测层) 实现。

使用：

    from src.services.fetch.headlessx_client import HeadlessXClient

    async with HeadlessXClient(base_url, api_key) as client:
        result = await client.render("https://example.com")
        print(result.html)
"""

from .client import HeadlessXClient
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

__all__ = [
    "HeadlessXClient",
    "RenderRequest",
    "RenderResult",
    "RetryConfig",
    "with_retry",
    # Exceptions
    "HeadlessXError",
    "HeadlessXAuthError",
    "HeadlessXTimeoutError",
    "HeadlessXRateLimitError",
    "HeadlessXServerError",
    "HeadlessXClientError",
]
