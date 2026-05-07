"""
WAF 中间件 — 激活 security_config.py 中已定义的 SQL 注入 / XSS 规则

功能：
- 启动时预编译正则，避免每次请求重新编译
- 扫描 URL query params + JSON body 字符串值 + Referer 头
- 跳过 multipart 上传和白名单路径
- LOG_ONLY 模式仅记录不拦截
"""

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from src.core.config import settings
from src.core.security_config import INPUT_VALIDATION

# 白名单路径（不做 WAF 检查）
_SKIP_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})


class _CompiledRules:
    """启动时预编译的 WAF 规则"""

    def __init__(self) -> None:
        self.sql_patterns: list[tuple[re.Pattern[str], str]] = []
        self.xss_patterns: list[tuple[re.Pattern[str], str]] = []

        sql_patterns = INPUT_VALIDATION.get("sql_injection_patterns", [])
        if not isinstance(sql_patterns, list):
            sql_patterns = []
        for p in sql_patterns:
            if not isinstance(p, str):
                continue
            try:
                self.sql_patterns.append((re.compile(p, re.IGNORECASE), p))
            except re.error as e:
                logger.warning(f"WAF: 无法编译 SQL 规则 {p!r}: {e}")

        xss_patterns = INPUT_VALIDATION.get("xss_patterns", [])
        if not isinstance(xss_patterns, list):
            xss_patterns = []
        for p in xss_patterns:
            if not isinstance(p, str):
                continue
            try:
                self.xss_patterns.append((re.compile(p, re.IGNORECASE), p))
            except re.error as e:
                logger.warning(f"WAF: 无法编译 XSS 规则 {p!r}: {e}")

        logger.info(
            f"WAF 规则编译完成: {len(self.sql_patterns)} SQL + {len(self.xss_patterns)} XSS"
        )


_rules = _CompiledRules()


def _scan_value(value: str) -> str | None:
    """扫描单个字符串值，返回匹配的攻击类型或 None"""
    for pattern, raw in _rules.sql_patterns:
        if pattern.search(value):
            return f"SQL_INJECTION({raw})"
    for pattern, raw in _rules.xss_patterns:
        if pattern.search(value):
            return f"XSS({raw})"
    return None


def _scan_dict(data: dict[str, Any], path: str = "") -> str | None:
    """递归扫描 dict 中所有字符串值"""
    for key, value in data.items():
        current = f"{path}.{key}" if path else key
        if isinstance(value, str):
            hit = _scan_value(value)
            if hit:
                return f"{current}: {hit}"
        elif isinstance(value, dict):
            hit = _scan_dict(value, current)
            if hit:
                return hit
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, str):
                    hit = _scan_value(item)
                    if hit:
                        return f"{current}[{i}]: {hit}"
                elif isinstance(item, dict):
                    hit = _scan_dict(item, f"{current}[{i}]")
                    if hit:
                        return hit
    return None


class WAFMiddleware(BaseHTTPMiddleware):
    """Web Application Firewall 中间件"""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 跳过白名单路径
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        # 跳过 multipart（文件上传）
        content_type = request.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            return await call_next(request)

        try:
            hit = None

            # 1. 扫描 URL query parameters
            for key, value in request.query_params.items():
                hit = _scan_value(value)
                if hit:
                    hit = f"query.{key}: {hit}"
                    break

            # 2. 扫描 Referer 头
            if not hit:
                referer = request.headers.get("referer", "")
                if referer:
                    hit = _scan_value(referer)
                    if hit:
                        hit = f"header.referer: {hit}"

            # 3. 扫描 JSON body
            if not hit and "application/json" in content_type:
                try:
                    body = await request.body()
                    if body:
                        data = json.loads(body)
                        if isinstance(data, dict):
                            hit = _scan_dict(data)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass  # 非 JSON body，跳过

            if hit:
                client_ip = request.headers.get(
                    "x-forwarded-for", request.client.host if request.client else "unknown"
                )
                logger.warning(
                    f"WAF 检测到攻击: {hit} | IP={client_ip} | "
                    f"Path={request.method} {request.url.path}"
                )
                request.state.waf_result = {"blocked": True, "reason": hit}

                if not getattr(settings, "ANTIBOT_WAF_LOG_ONLY", True):
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "请求被安全策略拦截", "code": "WAF_BLOCKED"},
                    )
            else:
                request.state.waf_result = {"blocked": False, "reason": None}

        except Exception as e:
            logger.debug(f"WAF 中间件异常（已降级放行）: {e}")
            request.state.waf_result = {"blocked": False, "reason": None, "degraded": True}

        return await call_next(request)
