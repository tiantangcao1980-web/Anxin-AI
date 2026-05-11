# -*- coding: utf-8 -*-
"""
安心智能助手 - 健康检查端点（P19-A 重构）

提供 3 个分层端点：
- GET /health           liveness  — 进程存在即 200（不查依赖，避免依赖故障引发熔断重启）
- GET /health/ready     readiness — 5 端组件全 OK 才 200，否则 503（K8s readiness probe）
- GET /health/detailed  详细组件 — admin only，列出每个组件 status/latency/error

此文件由 P19-A 重构，统一 HealthChecker 聚合器（见 services/monitoring/health_check.py）。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db
from src.services.monitoring.health_check import HealthChecker

router = APIRouter()

_start_time = time.time()


@router.get("/health", tags=["健康检查"])
async def liveness() -> Dict[str, Any]:
    """Liveness probe — 进程是否活着。

    不检查任何外部依赖。K8s liveness probe 应配置此端点：依赖故障不应触发
    应用重启（重启不会让 Postgres 恢复，反而中断尚在工作的请求）。
    """
    return {
        "status": "alive",
        "uptime_seconds": int(time.time() - _start_time),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/ready", tags=["健康检查"])
async def readiness(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Readiness probe — 5 端组件就绪检查。

    返回:
        200: overall in {"healthy", "degraded"} 仍可服务流量
        503: overall == "unhealthy" 核心组件 DOWN，应从 LB 摘除
    """
    checker = HealthChecker(db=db)
    result = await checker.check_all()
    if result["overall"] == "unhealthy":
        # 503 让 K8s readiness probe 把 pod 从 service 摘除
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"overall": result["overall"], "components": result["components"]},
        )
    return result


@router.get("/health/detailed", tags=["健康检查"])
async def detailed_health(
    db: AsyncSession = Depends(get_db),
    x_metrics_token: str = Header(default="", alias="X-Metrics-Token"),
) -> Dict[str, Any]:
    """详细组件健康检查（admin only）。

    鉴权：X-Metrics-Token header 必须等于 settings.METRICS_AUTH_TOKEN。
    若 token 未配置（空），仅在 development 环境放行；生产/staging 拒绝。
    """
    expected = (getattr(settings, "METRICS_AUTH_TOKEN", "") or "").strip()
    if expected:
        if x_metrics_token != expected:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid metrics token")
    else:
        # token 缺失：仅 dev 放行
        if settings.is_production():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="METRICS_AUTH_TOKEN not configured (production)",
            )

    checker = HealthChecker(db=db)
    result = await checker.check_all()
    # 附加运行时信息
    result["uptime_seconds"] = int(time.time() - _start_time)
    result["environment"] = settings.ENVIRONMENT
    result["app_version"] = getattr(settings, "APP_VERSION", "0.0.0")
    return result
