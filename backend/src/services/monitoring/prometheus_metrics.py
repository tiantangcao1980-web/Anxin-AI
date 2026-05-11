# -*- coding: utf-8 -*-
"""
Prometheus 业务指标注册中心（P19-A）

模块导入即注册到独立 CollectorRegistry，避免污染全局 prometheus_client
注册表（多次 import 不会引发 Duplicated timeseries 错误）。

19 个业务 metric:
- HTTP                  http_requests_total / http_request_duration_seconds
- Agent 任务            agent_tasks_total / agent_task_duration_seconds
- OAuth                 oauth_callback_total
- Webhook               webhook_received_total
- Fetch                 fetch_requests_total
- DB                    db_query_duration_seconds
- 进程信息（自动）       process_*（prometheus_client 内置 ProcessCollector）

P19-C Prometheus / Grafana 直接 scrape `/metrics` 端点。
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    ProcessCollector,
    PlatformCollector,
)

# 独立 registry，避免与第三方库冲突 + 便于测试 reset
REGISTRY = CollectorRegistry(auto_describe=True)

# 进程级标准 collector（CPU / RSS / fd / start_time / python info）
ProcessCollector(registry=REGISTRY)
PlatformCollector(registry=REGISTRY)

# ===== HTTP =====
HTTP_REQUESTS_TOTAL = Counter(
    "anxin_http_requests_total",
    "HTTP 请求总数",
    labelnames=("method", "endpoint", "status"),
    registry=REGISTRY,
)

# 默认 buckets 适用于 0~10s API；超长任务走 Agent 桶
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "anxin_http_request_duration_seconds",
    "HTTP 请求耗时（秒）",
    labelnames=("method", "endpoint"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

# ===== Agent 任务（personas / agent_tasks） =====
AGENT_TASKS_TOTAL = Counter(
    "anxin_agent_tasks_total",
    "智能体任务执行总数",
    labelnames=("persona", "status"),  # status: success / failed / timeout
    registry=REGISTRY,
)

AGENT_TASK_DURATION_SECONDS = Histogram(
    "anxin_agent_task_duration_seconds",
    "智能体任务耗时（秒）",
    labelnames=("persona",),
    buckets=(0.5, 1, 2.5, 5, 10, 30, 60, 120, 300, 600),
    registry=REGISTRY,
)

# ===== OAuth =====
OAUTH_CALLBACK_TOTAL = Counter(
    "anxin_oauth_callback_total",
    "OAuth 回调总数",
    labelnames=("provider", "result"),  # provider: wechat/alipay/notion/dingtalk/shopify
    registry=REGISTRY,                  # result: success / state_mismatch / token_error / network_error
)

# ===== Webhook =====
WEBHOOK_RECEIVED_TOTAL = Counter(
    "anxin_webhook_received_total",
    "Webhook 接收总数",
    labelnames=("source", "result"),  # source: wechat_pay/alipay/esign/feishu/...
    registry=REGISTRY,                # result: ok / signature_invalid / parse_error
)

# ===== Fetch（统一抓取栈 — L1 静态/L2 crawl4ai/L3 HeadlessX/L4 SearXNG） =====
FETCH_REQUESTS_TOTAL = Counter(
    "anxin_fetch_requests_total",
    "外部抓取请求总数",
    labelnames=("tier", "result"),  # tier: l1_static/l2_crawl4ai/l3_headlessx/l4_searxng
    registry=REGISTRY,              # result: success / timeout / blocked / error
)

# ===== DB =====
DB_QUERY_DURATION_SECONDS = Histogram(
    "anxin_db_query_duration_seconds",
    "数据库查询耗时（秒）",
    labelnames=("operation",),  # select / insert / update / delete / other
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
    registry=REGISTRY,
)


# ===== 工具函数：稳定 endpoint label，避免 high-cardinality =====
def normalize_endpoint(path: str) -> str:
    """将 /api/v1/cases/123 → /api/v1/cases/{id}，避免 metric 爆炸。"""
    if not path:
        return "/"
    parts = []
    for seg in path.split("/"):
        if not seg:
            parts.append(seg)
            continue
        # 数字 ID
        if seg.isdigit():
            parts.append("{id}")
        # UUID
        elif len(seg) == 36 and seg.count("-") == 4:
            parts.append("{uuid}")
        else:
            parts.append(seg)
    return "/".join(parts)


# ===== 简洁记录 API（middleware / service 调用） =====
def record_http_request(method: str, endpoint: str, status: int, duration_seconds: float) -> None:
    ep = normalize_endpoint(endpoint)
    HTTP_REQUESTS_TOTAL.labels(method=method.upper(), endpoint=ep, status=str(status)).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method.upper(), endpoint=ep).observe(duration_seconds)


def record_agent_task(persona: str, status: str, duration_seconds: float) -> None:
    AGENT_TASKS_TOTAL.labels(persona=persona, status=status).inc()
    AGENT_TASK_DURATION_SECONDS.labels(persona=persona).observe(duration_seconds)


def record_oauth_callback(provider: str, result: str) -> None:
    OAUTH_CALLBACK_TOTAL.labels(provider=provider, result=result).inc()


def record_webhook(source: str, result: str) -> None:
    WEBHOOK_RECEIVED_TOTAL.labels(source=source, result=result).inc()


def record_fetch_request(tier: str, result: str) -> None:
    FETCH_REQUESTS_TOTAL.labels(tier=tier, result=result).inc()


def record_db_query(operation: str, duration_seconds: float) -> None:
    DB_QUERY_DURATION_SECONDS.labels(operation=operation.lower()).observe(duration_seconds)


@contextmanager
def time_db_query(operation: str) -> Iterator[None]:
    """上下文管理器：自动记录 DB 查询耗时。

    用法：
        with time_db_query("select"):
            await db.execute(stmt)
    """
    t0 = time.perf_counter()
    try:
        yield
    finally:
        record_db_query(operation, time.perf_counter() - t0)


def render_exposition() -> bytes:
    """Render prometheus exposition text。供 /metrics 端点直接返回。"""
    from prometheus_client import generate_latest
    return generate_latest(REGISTRY)


CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
