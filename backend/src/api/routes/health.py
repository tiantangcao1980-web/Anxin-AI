# -*- coding: utf-8 -*-
"""
安心法务 - 增强健康检查端点
检查各基础设施组件状态，支持 healthy / degraded / unhealthy 三级状态。
"""

import time
from typing import Any, Dict

import httpx
from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db

router = APIRouter()

# 应用启动时间（用于计算 uptime）
_start_time = time.time()


async def _check_postgres(db: AsyncSession) -> Dict[str, Any]:
    """检查 PostgreSQL 连接"""
    try:
        t0 = time.time()
        await db.execute(text("SELECT 1"))
        latency = round((time.time() - t0) * 1000, 1)
        return {"status": "up", "latency_ms": latency}
    except Exception as e:
        logger.warning(f"PostgreSQL 健康检查失败: {e}")
        return {"status": "down", "error": str(e)}


async def _check_redis() -> Dict[str, Any]:
    """检查 Redis 连接"""
    try:
        import redis.asyncio as aioredis

        t0 = time.time()
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=3)
        await r.ping()
        latency = round((time.time() - t0) * 1000, 1)
        await r.aclose()
        return {"status": "up", "latency_ms": latency}
    except Exception as e:
        logger.warning(f"Redis 健康检查失败: {e}")
        return {"status": "down", "error": str(e)}


async def _check_qdrant() -> Dict[str, Any]:
    """检查 Qdrant 向量数据库"""
    try:
        t0 = time.time()
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.QDRANT_URL}/healthz")
        latency = round((time.time() - t0) * 1000, 1)
        if resp.status_code == 200:
            return {"status": "up", "latency_ms": latency}
        return {"status": "down", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Qdrant 健康检查失败: {e}")
        return {"status": "down", "error": str(e)}


async def _check_minio() -> Dict[str, Any]:
    """检查 MinIO 对象存储"""
    try:
        t0 = time.time()
        protocol = "https" if settings.MINIO_USE_SSL else "http"
        url = f"{protocol}://{settings.MINIO_ENDPOINT}/minio/health/live"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(url)
        latency = round((time.time() - t0) * 1000, 1)
        if resp.status_code == 200:
            return {"status": "up", "latency_ms": latency}
        return {"status": "down", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"MinIO 健康检查失败: {e}")
        return {"status": "down", "error": str(e)}


async def _check_neo4j() -> Dict[str, Any]:
    """检查 Neo4j 图数据库"""
    try:
        t0 = time.time()
        # 将 bolt://host:7687 转换为 http://host:7474 进行 HTTP 健康检查
        neo4j_uri = getattr(settings, "NEO4J_URI", "bolt://localhost:7687")
        host = neo4j_uri.split("://")[-1].split(":")[0]
        http_url = f"http://{host}:7474/db/neo4j/cluster/available"
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(http_url)
        latency = round((time.time() - t0) * 1000, 1)
        if resp.status_code == 200:
            return {"status": "up", "latency_ms": latency}
        return {"status": "down", "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        logger.warning(f"Neo4j 健康检查失败: {e}")
        return {"status": "down", "error": str(e)}


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    增强健康检查端点

    返回各组件状态：
    - healthy: 所有核心组件正常
    - degraded: 可选组件异常，核心组件正常
    - unhealthy: 核心组件异常
    """
    # 核心组件：PostgreSQL、Redis
    pg_status = await _check_postgres(db)
    redis_status = await _check_redis()

    # 可选组件：Qdrant、MinIO、Neo4j
    qdrant_status = await _check_qdrant()
    minio_status = await _check_minio()
    neo4j_status = await _check_neo4j()

    components = {
        "database": pg_status,
        "redis": redis_status,
        "qdrant": qdrant_status,
        "minio": minio_status,
        "neo4j": neo4j_status,
    }

    # 判断整体状态
    core_components = [pg_status, redis_status]
    optional_components = [qdrant_status, minio_status, neo4j_status]

    core_down = any(c["status"] == "down" for c in core_components)
    optional_down = any(c["status"] == "down" for c in optional_components)

    if core_down:
        overall = "unhealthy"
    elif optional_down:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "brand": settings.BRAND_NAME,
        "uptime_seconds": round(time.time() - _start_time, 1),
        "components": components,
    }
