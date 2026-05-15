"""
多组件健康检查 service（P19-A）

支持 5 个核心后端组件：
- postgres   核心 — DOWN 视为 unhealthy
- redis      核心 — DOWN 视为 unhealthy
- neo4j      可选 — DOWN 视为 degraded（图谱降级仍可用主要功能）
- qdrant     可选 — DOWN 视为 degraded（RAG 降级到 BM25）
- celery     可选 — DOWN 视为 degraded（异步任务延迟，不影响同步 API）

返回结构（HealthChecker.check_all）：
    {
        "overall": "healthy" | "degraded" | "unhealthy",
        "components": {
            "postgres": {"status": "up"|"down", "latency_ms": 12.3, "error": "..."?},
            ...
        },
        "checked_at": "2026-05-01T12:00:00Z"
    }
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import httpx
from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# 单组件超时（秒），避免单个组件阻塞整个 readiness 检查
COMPONENT_TIMEOUT_SECONDS = 5.0


class ComponentStatus(str, Enum):
    UP = "up"
    DOWN = "down"
    DEGRADED = "degraded"


@dataclass
class CheckResult:
    status: ComponentStatus
    latency_ms: float | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"status": self.status.value}
        if self.latency_ms is not None:
            d["latency_ms"] = round(self.latency_ms, 1)
        if self.error:
            d["error"] = self.error
        return d


async def _with_timeout(coro: Awaitable[CheckResult], name: str) -> CheckResult:
    """超时保护包装。"""
    try:
        return await asyncio.wait_for(coro, timeout=COMPONENT_TIMEOUT_SECONDS)
    except TimeoutError:
        logger.warning(f"[health] {name} 检查超时 (>{COMPONENT_TIMEOUT_SECONDS}s)")
        return CheckResult(
            status=ComponentStatus.DOWN,
            error=f"timeout > {COMPONENT_TIMEOUT_SECONDS}s",
        )
    except Exception as e:
        logger.warning(f"[health] {name} 检查异常：{e}")
        return CheckResult(status=ComponentStatus.DOWN, error=str(e))


# ===== 单组件 check 函数（独立 async function，便于测试 mock） =====

async def check_postgres(db: AsyncSession) -> CheckResult:
    """SELECT 1 健康检查。"""
    t0 = time.perf_counter()
    await db.execute(text("SELECT 1"))
    return CheckResult(status=ComponentStatus.UP, latency_ms=(time.perf_counter() - t0) * 1000)


async def check_redis(redis_url: str) -> CheckResult:
    """Redis PING 健康检查。"""
    import redis.asyncio as aioredis

    t0 = time.perf_counter()
    r = aioredis.from_url(redis_url, socket_connect_timeout=3)
    try:
        await r.ping()
        return CheckResult(status=ComponentStatus.UP, latency_ms=(time.perf_counter() - t0) * 1000)
    finally:
        try:
            await r.aclose()
        except Exception:
            pass


async def check_neo4j(neo4j_uri: str) -> CheckResult:
    """Neo4j HTTP 端口 (7474) 健康检查（兼容 Community 版）。"""
    t0 = time.perf_counter()
    host = neo4j_uri.split("://")[-1].split(":")[0] or "localhost"
    url = f"http://{host}:7474/"
    async with httpx.AsyncClient(timeout=3) as c:
        resp = await c.get(url)
    if resp.status_code == 200:
        return CheckResult(status=ComponentStatus.UP, latency_ms=(time.perf_counter() - t0) * 1000)
    return CheckResult(status=ComponentStatus.DOWN, error=f"HTTP {resp.status_code}")


async def check_qdrant(qdrant_url: str) -> CheckResult:
    """Qdrant /healthz 健康检查。"""
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=3) as c:
        resp = await c.get(f"{qdrant_url.rstrip('/')}/healthz")
    if resp.status_code == 200:
        return CheckResult(status=ComponentStatus.UP, latency_ms=(time.perf_counter() - t0) * 1000)
    return CheckResult(status=ComponentStatus.DOWN, error=f"HTTP {resp.status_code}")


async def check_celery(redis_url: str) -> CheckResult:
    """Celery 检查策略：通过 Redis broker key 是否有 worker 心跳判断。

    Celery 5.x 自身的 inspect API 同步且会阻塞较长时间，这里采用低成本的
    broker 探活：能 PING Redis + Redis 中存在 celery 队列 key 即视为 UP。
    无 worker 注册不视为 DOWN（开发环境可能未起 worker），仅作 DEGRADED 提示。
    """
    import redis.asyncio as aioredis

    t0 = time.perf_counter()
    r = aioredis.from_url(redis_url, socket_connect_timeout=3)
    try:
        await r.ping()
        # 检查是否有 celery 控制频道在线（不强制）
        try:
            channels = await r.execute_command("PUBSUB", "CHANNELS", "celery*")
            if channels:
                return CheckResult(status=ComponentStatus.UP, latency_ms=(time.perf_counter() - t0) * 1000)
            return CheckResult(
                status=ComponentStatus.DEGRADED,
                latency_ms=(time.perf_counter() - t0) * 1000,
                error="no celery worker channels (broker reachable)",
            )
        except Exception:
            return CheckResult(status=ComponentStatus.UP, latency_ms=(time.perf_counter() - t0) * 1000)
    finally:
        try:
            await r.aclose()
        except Exception:
            pass


# ===== Aggregator =====

class HealthChecker:
    """5 端组件健康检查聚合器。

    用法：
        checker = HealthChecker(db_factory=lambda: get_db_session())
        result = await checker.check_all()
    """

    # 核心组件：DOWN 即 overall=unhealthy
    CORE = ("postgres", "redis")
    # 可选组件：DOWN 仅 overall=degraded
    OPTIONAL = ("neo4j", "qdrant", "celery")

    def __init__(
        self,
        db: AsyncSession | None = None,
        redis_url: str | None = None,
        neo4j_uri: str | None = None,
        qdrant_url: str | None = None,
    ):
        # 缺省从 settings 读取
        try:
            from src.core.config import settings
            self.redis_url = redis_url or settings.REDIS_URL
            self.neo4j_uri = neo4j_uri or getattr(settings, "NEO4J_URI", "bolt://localhost:7687")
            self.qdrant_url = qdrant_url or settings.QDRANT_URL
        except Exception:
            self.redis_url = redis_url or "redis://localhost:6379/0"
            self.neo4j_uri = neo4j_uri or "bolt://localhost:7687"
            self.qdrant_url = qdrant_url or "http://localhost:6333"
        self.db = db

    async def check_all(self) -> dict[str, Any]:
        """并发检查所有组件。"""
        tasks: dict[str, Awaitable[CheckResult]] = {}

        if self.db is not None:
            tasks["postgres"] = _with_timeout(check_postgres(self.db), "postgres")
        else:
            tasks["postgres"] = _with_timeout(
                _missing("postgres", "db session not provided"), "postgres"
            )

        tasks["redis"] = _with_timeout(check_redis(self.redis_url), "redis")
        tasks["neo4j"] = _with_timeout(check_neo4j(self.neo4j_uri), "neo4j")
        tasks["qdrant"] = _with_timeout(check_qdrant(self.qdrant_url), "qdrant")
        tasks["celery"] = _with_timeout(check_celery(self.redis_url), "celery")

        keys = list(tasks.keys())
        results = await asyncio.gather(*[tasks[k] for k in keys], return_exceptions=False)
        components = {k: r.to_dict() for k, r in zip(keys, results, strict=True)}

        overall = self._compute_overall(components)
        return {
            "overall": overall,
            "components": components,
            "checked_at": datetime.now(UTC).isoformat(),
        }

    def _compute_overall(self, components: dict[str, dict[str, Any]]) -> str:
        core_down = any(
            components.get(name, {}).get("status") == ComponentStatus.DOWN.value
            for name in self.CORE
        )
        if core_down:
            return "unhealthy"
        optional_down = any(
            components.get(name, {}).get("status") in (ComponentStatus.DOWN.value, ComponentStatus.DEGRADED.value)
            for name in self.OPTIONAL
        )
        if optional_down:
            return "degraded"
        return "healthy"


async def _missing(name: str, reason: str) -> CheckResult:
    return CheckResult(status=ComponentStatus.DOWN, error=f"{name}: {reason}")


# 提供给单组件检查的便捷字典（测试用）
SINGLE_CHECK_FUNCS: dict[str, Callable[..., Awaitable[CheckResult]]] = {
    "postgres": check_postgres,
    "redis": check_redis,
    "neo4j": check_neo4j,
    "qdrant": check_qdrant,
    "celery": check_celery,
}
