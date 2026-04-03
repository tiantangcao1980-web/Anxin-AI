# -*- coding: utf-8 -*-
"""
Prometheus Metrics 端点

为 Grafana 监控面板提供应用级指标：
- 请求计数和延迟
- 活跃用户数
- AI 调用统计
- 知识库和调查模块指标
"""

import time
from fastapi import APIRouter, Request, Response
from loguru import logger

router = APIRouter()

# 简易指标收集器（生产环境建议用 prometheus_client 库）
_metrics = {
    "http_requests_total": 0,
    "http_request_duration_seconds_sum": 0.0,
    "active_investigations": 0,
    "ai_calls_total": 0,
    "ai_calls_errors": 0,
    "knowledge_searches_total": 0,
    "dream_consolidations_total": 0,
    "experience_extractions_total": 0,
}


def increment(metric: str, value: float = 1.0):
    """递增指标"""
    _metrics[metric] = _metrics.get(metric, 0) + value


def set_gauge(metric: str, value: float):
    """设置 gauge 指标"""
    _metrics[metric] = value


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus 拉取端点（text/plain 格式）"""
    lines = []

    for key, value in _metrics.items():
        metric_type = "counter" if "total" in key or "errors" in key else "gauge"
        lines.append(f"# TYPE anxin_{key} {metric_type}")
        lines.append(f"anxin_{key} {value}")

    # 追加运行时信息
    try:
        import psutil
        proc = psutil.Process()
        lines.append(f"# TYPE anxin_process_memory_bytes gauge")
        lines.append(f"anxin_process_memory_bytes {proc.memory_info().rss}")
        lines.append(f"# TYPE anxin_process_cpu_percent gauge")
        lines.append(f"anxin_process_cpu_percent {proc.cpu_percent()}")
    except ImportError:
        pass

    # 追加数据库连接池信息
    try:
        from src.core.database import engine
        pool = engine.pool
        lines.append(f"# TYPE anxin_db_pool_size gauge")
        lines.append(f"anxin_db_pool_size {pool.size()}")
        lines.append(f"# TYPE anxin_db_pool_checkedin gauge")
        lines.append(f"anxin_db_pool_checkedin {pool.checkedin()}")
        lines.append(f"# TYPE anxin_db_pool_checkedout gauge")
        lines.append(f"anxin_db_pool_checkedout {pool.checkedout()}")
    except Exception:
        pass

    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; charset=utf-8",
    )
