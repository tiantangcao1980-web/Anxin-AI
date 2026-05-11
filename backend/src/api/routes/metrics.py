"""
Prometheus Metrics 端点

为 Grafana 监控面板提供应用级指标：
- 请求计数和延迟
- 活跃用户数
- AI 调用统计
- 知识库和调查模块指标
"""

from typing import Any, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.models.webhook import WebhookReceived

from src.core.config import settings

router = APIRouter()

# 简易指标收集器（生产环境建议用 prometheus_client 库）
_metrics: dict[str, float] = {
    "http_requests_total": 0,
    "http_request_duration_seconds_sum": 0.0,
    "active_investigations": 0,
    "ai_calls_total": 0,
    "ai_calls_errors": 0,
    "knowledge_searches_total": 0,
    "dream_consolidations_total": 0,
    "experience_extractions_total": 0,
}


def increment(metric: str, value: float = 1.0) -> None:
    """递增指标"""
    _metrics[metric] = _metrics.get(metric, 0) + value


def set_gauge(metric: str, value: float) -> None:
    """设置 gauge 指标"""
    _metrics[metric] = value


@router.get("/metrics")
async def prometheus_metrics(db: AsyncSession = Depends(get_db)) -> Response:
    """Prometheus 拉取端点（text/plain 格式）"""
    lines: list[str] = []

    for key, value in _metrics.items():
        metric_type = "counter" if "total" in key or "errors" in key else "gauge"
        lines.append(f"# TYPE anxin_{key} {metric_type}")
        lines.append(f"anxin_{key} {value}")

    # 追加运行时信息
    try:
        import psutil
        proc = psutil.Process()
        lines.append("# TYPE anxin_process_memory_bytes gauge")
        lines.append(f"anxin_process_memory_bytes {proc.memory_info().rss}")
        lines.append("# TYPE anxin_process_cpu_percent gauge")
        lines.append(f"anxin_process_cpu_percent {proc.cpu_percent()}")
    except ImportError:
        pass

    # 追加数据库连接池信息
    try:
        from src.core.database import engine
        pool = cast(Any, engine.pool)
        lines.append("# TYPE anxin_db_pool_size gauge")
        lines.append(f"anxin_db_pool_size {pool.size()}")
        lines.append("# TYPE anxin_db_pool_checkedin gauge")
        lines.append(f"anxin_db_pool_checkedin {pool.checkedin()}")
        lines.append("# TYPE anxin_db_pool_checkedout gauge")
        lines.append(f"anxin_db_pool_checkedout {pool.checkedout()}")
    except Exception:
        pass

    try:
        result = await db.execute(
            select(WebhookReceived.status, func.count(WebhookReceived.id)).group_by(WebhookReceived.status)
        )
        webhook_stats: dict[str, int] = {
            str(row[0]): int(row[1])
            for row in result.all()
        }
        webhook_total = sum(webhook_stats.values())
        lines.append("# TYPE anxin_webhook_received_total counter")
        lines.append(f"anxin_webhook_received_total {webhook_total}")
        lines.append("# TYPE anxin_webhook_failed_total counter")
        lines.append(f"anxin_webhook_failed_total {webhook_stats.get('failed', 0)}")
        lines.append("# TYPE anxin_webhook_processing gauge")
        lines.append(f"anxin_webhook_processing {webhook_stats.get('processing', 0)}")
    except Exception as exc:
        logger.warning(f"导出 webhook 指标失败: {exc}")

    # P19-A: 追加业务级 prometheus_client 暴露（19 个 metric）
    if getattr(settings, "METRICS_ENABLED", True):
        try:
            from src.services.monitoring.prometheus_metrics import CONTENT_TYPE_LATEST, render_exposition
            return Response(
                content="\n".join(lines) + "\n" + render_exposition().decode("utf-8"),
                media_type=CONTENT_TYPE_LATEST,
            )
        except Exception as e:
            logger.warning(f"prometheus exposition 失败: {e}")

    return Response(
        content="\n".join(lines) + "\n",
        media_type="text/plain; charset=utf-8",
    )


@router.get("/metrics/business", tags=["监控指标"])
async def business_metrics_only(
    x_metrics_token: str = Header(default="", alias="X-Metrics-Token"),
) -> Response:
    """业务级 prometheus 暴露（admin 鉴权）— 仅返回 P19-A 业务 metric。"""
    expected = (getattr(settings, "METRICS_AUTH_TOKEN", "") or "").strip()
    if expected and x_metrics_token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid metrics token")
    from src.services.monitoring.prometheus_metrics import CONTENT_TYPE_LATEST, render_exposition
    return Response(content=render_exposition(), media_type=CONTENT_TYPE_LATEST)
