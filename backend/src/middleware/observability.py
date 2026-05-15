"""
ObservabilityMiddleware（P19-A）

职责：
1. 注入 / 透传 X-Request-ID（client 提供则透传，否则生成 uuid4）
2. Prometheus 计时 + 计数（按 method/endpoint/status）
3. Sentry breadcrumb（标注 endpoint / status / duration / request_id）
4. 慢请求告警 — duration >= SLOW_THRESHOLD_SECONDS 走 WARN 日志 + sentry tag

设计：使用 starlette BaseHTTPMiddleware，零侵入业务路由；记录失败不抛出。
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

REQUEST_ID_HEADER = "X-Request-ID"
SLOW_THRESHOLD_SECONDS = 1.0   # 慢请求阈值


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """统一可观测中间件。"""

    def __init__(
        self,
        app: ASGIApp,
        slow_threshold_seconds: float = SLOW_THRESHOLD_SECONDS,
        skip_paths: tuple[str, ...] | None = None,
    ):
        super().__init__(app)
        self.slow_threshold_seconds = slow_threshold_seconds
        # 默认跳过自身的 /metrics 与静态健康端点（避免自我递归 + cardinality）
        self.skip_paths = skip_paths or ("/metrics", "/health", "/health/ready", "/health/detailed")

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 1. request_id 注入
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        # 暴露到 request.state，业务路由可读
        request.state.request_id = rid

        # 跳过 metrics 自身（避免 metric 循环膨胀）
        path = request.url.path
        skip_metrics = path in self.skip_paths

        t0 = time.perf_counter()
        status_code = 500  # 兜底（500 表示中间件链失败）
        response: Response | None = None
        exc: BaseException | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except BaseException as e:  # noqa: BLE001 — 透传后 raise
            exc = e
            raise
        finally:
            duration = time.perf_counter() - t0

            # 2. 写回 request_id 到响应 header
            if response is not None:
                try:
                    response.headers[REQUEST_ID_HEADER] = rid
                except Exception:
                    pass

            # 3. prometheus（跳过自身 metric 端点）
            if not skip_metrics:
                try:
                    from src.services.monitoring.prometheus_metrics import record_http_request
                    record_http_request(
                        method=request.method,
                        endpoint=path,
                        status=status_code,
                        duration_seconds=duration,
                    )
                except Exception as me:  # pragma: no cover — 不允许影响主流程
                    logger.warning(f"[observability] prometheus 记录失败: {me}")

            # 4. 慢请求 WARN
            if duration >= self.slow_threshold_seconds:
                logger.warning(
                    f"[slow-request] {request.method} {path} "
                    f"status={status_code} duration={duration*1000:.1f}ms request_id={rid}"
                )
                try:  # sentry 加 tag
                    import sentry_sdk
                    sentry_sdk.set_tag("slow_request", "true")
                    sentry_sdk.set_tag("slow_request.duration_ms", int(duration * 1000))
                except Exception:
                    pass

            # 5. sentry breadcrumb（请求维度）
            try:
                import sentry_sdk
                sentry_sdk.add_breadcrumb(
                    category="http",
                    type="http",
                    level="error" if status_code >= 500 else ("warning" if status_code >= 400 else "info"),
                    message=f"{request.method} {path} -> {status_code}",
                    data={
                        "request_id": rid,
                        "duration_ms": round(duration * 1000, 1),
                        "endpoint": path,
                        "status": status_code,
                    },
                )
                sentry_sdk.set_tag("request_id", rid)
            except Exception:
                pass

            # 6. 异常聚类（仅当未被全局 handler 接管才走这里）
            if exc is not None:
                try:
                    from src.services.monitoring.error_classifier import classify_error
                    classify_error(exc, endpoint=path, message=f"{request.method} {path}")
                except Exception:
                    pass
