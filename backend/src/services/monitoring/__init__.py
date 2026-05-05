# -*- coding: utf-8 -*-
"""
P19-A 后端可观测层入口

子模块：
- sentry_setup: Sentry SDK 初始化 + 敏感字段过滤 before_send
- prometheus_metrics: prometheus_client 业务指标注册中心
- health_check: 5 端组件健康检查（postgres / redis / neo4j / qdrant / celery）
- error_classifier: 错误聚类（exception type + frame + endpoint 三元组 hash）
- slo_definitions: SLO 矩阵（auth / chat / tasks / fetch / oauth）

外部入口：
    from src.services.monitoring import (
        setup_sentry,                  # 在 lifespan startup 调用
        REGISTRY,                      # prometheus 注册表（/metrics 暴露用）
        record_http_request,           # ObservabilityMiddleware 调用
        HealthChecker,                 # /health/ready & /health/detailed
        ErrorClassifier,               # 异常聚类器（before_send 调用）
        SLO_MATRIX,                    # SLO 字典（告警/dashboard 引用）
    )
"""

from .sentry_setup import setup_sentry, sanitize_event
from .prometheus_metrics import (
    REGISTRY,
    record_http_request,
    record_agent_task,
    record_oauth_callback,
    record_webhook,
    record_fetch_request,
    record_db_query,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    AGENT_TASKS_TOTAL,
    AGENT_TASK_DURATION_SECONDS,
    OAUTH_CALLBACK_TOTAL,
    WEBHOOK_RECEIVED_TOTAL,
    FETCH_REQUESTS_TOTAL,
    DB_QUERY_DURATION_SECONDS,
)
from .health_check import HealthChecker, ComponentStatus
from .error_classifier import ErrorClassifier, classify_error
from .slo_definitions import SLO_MATRIX, SLO

__all__ = [
    "setup_sentry",
    "sanitize_event",
    "REGISTRY",
    "record_http_request",
    "record_agent_task",
    "record_oauth_callback",
    "record_webhook",
    "record_fetch_request",
    "record_db_query",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "AGENT_TASKS_TOTAL",
    "AGENT_TASK_DURATION_SECONDS",
    "OAUTH_CALLBACK_TOTAL",
    "WEBHOOK_RECEIVED_TOTAL",
    "FETCH_REQUESTS_TOTAL",
    "DB_QUERY_DURATION_SECONDS",
    "HealthChecker",
    "ComponentStatus",
    "ErrorClassifier",
    "classify_error",
    "SLO_MATRIX",
    "SLO",
]
