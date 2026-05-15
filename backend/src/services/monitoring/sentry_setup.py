"""
Sentry SDK 初始化

负责：
1. 根据 settings.SENTRY_DSN 决定是否启用（DSN 为空 → noop）
2. 注入 FastAPI / SQLAlchemy / Celery / Redis / httpx 集成
3. before_send 过滤敏感字段（手机号 / 身份证 / token / password / secret / cookie）
4. release 与 environment 跟 CI build artifact 关联（P19-D 注入 SENTRY_RELEASE）
5. traces_sample_rate 默认 0.1 — 高 QPS 端点慢慢调

外部调用：
    from src.services.monitoring import setup_sentry
    setup_sentry()  # lifespan startup 单次调用
"""

from __future__ import annotations

import os
import re
from typing import Any

from loguru import logger

# ===== 敏感字段正则（before_send 过滤） =====
# 仅做"key 命中即 redact"+"高熵 token 字符串 redact"
_SENSITIVE_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|"
    r"authorization|cookie|session|csrf|"
    r"id[_-]?card|身份证|手机号|mobile|phone|"
    r"bank[_-]?card|card[_-]?no|"
    r"jwt|bearer|refresh[_-]?token)",
    re.IGNORECASE,
)

# 高熵字符串近似检测（>=20 char 全为 [A-Za-z0-9_-+/=.] 视为可能 token）
_HIGH_ENTROPY_RE = re.compile(r"^[A-Za-z0-9_\-+/=.]{20,}$")

# 中国手机号 / 身份证 简化匹配
_PHONE_RE = re.compile(r"\b1[3-9]\d{9}\b")
_ID_CARD_RE = re.compile(r"\b\d{17}[\dXx]\b")

REDACTED = "[REDACTED]"


def _redact_value(key: str, value: Any) -> Any:
    """根据 key 决定是否 redact，并对字符串值做 PII 脱敏。"""
    if value is None:
        return None
    if _SENSITIVE_KEY_RE.search(key or ""):
        return REDACTED
    if isinstance(value, str):
        if _HIGH_ENTROPY_RE.match(value):
            return REDACTED
        # 字符串内嵌的手机号/身份证脱敏
        v = _PHONE_RE.sub(REDACTED, value)
        v = _ID_CARD_RE.sub(REDACTED, v)
        return v
    if isinstance(value, dict):
        return {k: _redact_value(k, v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_value(key, v) for v in value]
    return value


def sanitize_event(
    event: dict[str, Any], hint: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Sentry before_send 钩子：过滤敏感字段。

    返回 None 表示丢弃事件；返回 event 表示放行（可被修改）。
    保留原结构便于 Sentry UI 展示，仅替换敏感值。
    """
    if not isinstance(event, dict):
        return event

    # 1. request 部分（headers / cookies / data / query_string）
    req = event.get("request") or {}
    if isinstance(req, dict):
        for field in ("headers", "cookies", "data", "query_string", "env"):
            if field in req:
                req[field] = _redact_value(field, req[field])
        event["request"] = req

    # 2. extra / contexts / tags 顶层
    for top in ("extra", "tags", "contexts"):
        if top in event and isinstance(event[top], dict):
            event[top] = {k: _redact_value(k, v) for k, v in event[top].items()}

    # 3. user 字段：仅保留 id，移除 email/ip_address/username 中可能的 PII
    user = event.get("user") or {}
    if isinstance(user, dict):
        for sensitive in ("email", "username", "ip_address"):
            if sensitive in user:
                user[sensitive] = REDACTED
        event["user"] = user

    # 4. message / breadcrumb 文本中的内嵌 PII
    if "message" in event and isinstance(event["message"], str):
        event["message"] = _redact_value("message", event["message"])
    if "breadcrumbs" in event:
        crumbs = event["breadcrumbs"]
        if isinstance(crumbs, dict) and isinstance(crumbs.get("values"), list):
            for c in crumbs["values"]:
                if isinstance(c, dict):
                    if "message" in c:
                        c["message"] = _redact_value("message", c["message"])
                    if "data" in c:
                        c["data"] = _redact_value("data", c["data"])
    return event


def setup_sentry() -> bool:
    """初始化 Sentry。返回 True=启用，False=DSN 缺失（noop）。"""
    try:
        from src.core.config import settings
    except Exception as e:  # pragma: no cover — settings 加载失败兜底
        logger.warning(f"[Sentry] settings 加载失败：{e}")
        return False

    dsn = (getattr(settings, "SENTRY_DSN", "") or "").strip()
    if not dsn:
        logger.info("[Sentry] SENTRY_DSN 未配置，跳过初始化（noop）")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    except ImportError:
        logger.warning("[Sentry] sentry-sdk 未安装，跳过初始化")
        return False

    integrations = [
        FastApiIntegration(transaction_style="endpoint"),
        SqlalchemyIntegration(),
    ]

    # 可选集成：Celery / Redis / httpx — import 失败不致命
    try:
        from sentry_sdk.integrations.celery import CeleryIntegration

        integrations.append(CeleryIntegration())
    except Exception:
        pass
    try:
        from sentry_sdk.integrations.redis import RedisIntegration

        integrations.append(RedisIntegration())
    except Exception:
        pass
    try:
        from sentry_sdk.integrations.httpx import HttpxIntegration

        integrations.append(HttpxIntegration())
    except Exception:
        pass

    sentry_sdk.init(
        dsn=dsn,
        environment=getattr(settings, "SENTRY_ENVIRONMENT", "development"),
        release=os.environ.get(
            "SENTRY_RELEASE", f"anxin@{getattr(settings, 'APP_VERSION', '0.0.0')}"
        ),
        traces_sample_rate=float(getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.1)),
        send_default_pii=False,
        attach_stacktrace=True,
        integrations=integrations,
        before_send=sanitize_event,
        before_send_transaction=sanitize_event,
        max_breadcrumbs=50,
        ignore_errors=[KeyboardInterrupt],
    )
    logger.info(
        f"[Sentry] 已启用 environment={getattr(settings, 'SENTRY_ENVIRONMENT', 'development')} "
        f"traces_sample_rate={getattr(settings, 'SENTRY_TRACES_SAMPLE_RATE', 0.1)}"
    )
    return True
