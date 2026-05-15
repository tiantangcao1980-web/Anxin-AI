"""
P19-A 健康检查端点测试

覆盖：
- liveness 200 / 不查依赖
- readiness 5 端组件 mock，全 OK -> 200
- readiness 核心组件 DOWN -> 503
- detailed 鉴权（无 token + 非生产 -> 200；token 不匹配 -> 403）

实现说明：为避免 `from src.api.routes.health import router` 触发整个
`src.api.routes` 包的初始化（连锁拉入 `services/im_gateway/models.py` 的
PG 专属 JSONB 类型，破坏 conftest 的 SQLite create_all），本文件用
importlib 直接加载 health 模块文件，绕过包级 __init__。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# ===== 直接从文件路径加载 health 模块，绕过 src.api.routes 包初始化 =====
_HEALTH_PATH = Path(__file__).resolve().parent.parent / "src" / "api" / "routes" / "health.py"


def _load_health_module():
    """每个测试单独加载，避免缓存导致 mock 失效。"""
    spec = importlib.util.spec_from_file_location("_test_p19a_health_module", str(_HEALTH_PATH))
    assert spec and spec.loader, "无法加载 health 模块"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_test_p19a_health_module"] = mod
    spec.loader.exec_module(mod)
    return mod


from src.services.monitoring.health_check import ComponentStatus  # 不会拉 routes 包


@pytest.fixture
def health_module():
    return _load_health_module()


@pytest.fixture
def app(health_module):
    a = FastAPI()
    a.include_router(health_module.router)
    return a


# ==================== 1. liveness ====================
async def test_liveness_returns_200_without_db(app):
    """liveness 不应触碰任何依赖。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "alive"
    assert "uptime_seconds" in body
    assert "timestamp" in body


# ==================== 2. readiness 全 OK ====================
async def test_readiness_all_ok_returns_200(app, health_module):
    fake_result = {
        "overall": "healthy",
        "components": {
            "postgres": {"status": "up", "latency_ms": 1.0},
            "redis": {"status": "up", "latency_ms": 1.0},
            "neo4j": {"status": "up", "latency_ms": 1.0},
            "qdrant": {"status": "up", "latency_ms": 1.0},
            "celery": {"status": "up", "latency_ms": 1.0},
        },
        "checked_at": "2026-05-01T00:00:00+00:00",
    }

    async def fake_get_db():
        yield None

    from src.core.database import get_db

    app.dependency_overrides[get_db] = fake_get_db

    with patch.object(health_module, "HealthChecker") as MockChecker:
        instance = MockChecker.return_value

        async def _check_all():
            return fake_result

        instance.check_all = _check_all

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/health/ready")

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    assert resp.json()["overall"] == "healthy"


# ==================== 3. readiness 核心 DOWN -> 503 ====================
async def test_readiness_core_down_returns_503(app, health_module):
    fake_result = {
        "overall": "unhealthy",
        "components": {
            "postgres": {"status": "down", "error": "connection refused"},
            "redis": {"status": "up", "latency_ms": 1.0},
            "neo4j": {"status": "up", "latency_ms": 1.0},
            "qdrant": {"status": "up", "latency_ms": 1.0},
            "celery": {"status": "up", "latency_ms": 1.0},
        },
        "checked_at": "2026-05-01T00:00:00+00:00",
    }

    async def fake_get_db():
        yield None

    from src.core.database import get_db

    app.dependency_overrides[get_db] = fake_get_db

    with patch.object(health_module, "HealthChecker") as MockChecker:
        instance = MockChecker.return_value

        async def _check_all():
            return fake_result

        instance.check_all = _check_all

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/health/ready")

    app.dependency_overrides.clear()
    assert resp.status_code == 503
    body = resp.json()
    assert body["detail"]["overall"] == "unhealthy"
    assert body["detail"]["components"]["postgres"]["status"] == "down"


# ==================== 4. detailed 鉴权 ====================
async def test_detailed_token_mismatch_returns_403(app, health_module):
    async def fake_get_db():
        yield None

    from src.core.database import get_db

    app.dependency_overrides[get_db] = fake_get_db

    with patch.object(health_module, "settings") as mock_settings:
        mock_settings.METRICS_AUTH_TOKEN = "correct-secret"
        mock_settings.is_production.return_value = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/health/detailed", headers={"X-Metrics-Token": "wrong"})

    app.dependency_overrides.clear()
    assert resp.status_code == 403
    assert "invalid metrics token" in resp.json()["detail"]


async def test_detailed_no_token_dev_returns_200(app, health_module):
    fake_result = {
        "overall": "healthy",
        "components": {
            "postgres": {"status": "up"},
            "redis": {"status": "up"},
            "neo4j": {"status": "up"},
            "qdrant": {"status": "up"},
            "celery": {"status": "up"},
        },
        "checked_at": "2026-05-01T00:00:00+00:00",
    }

    async def fake_get_db():
        yield None

    from src.core.database import get_db

    app.dependency_overrides[get_db] = fake_get_db

    with (
        patch.object(health_module, "HealthChecker") as MockChecker,
        patch.object(health_module, "settings") as mock_settings,
    ):
        mock_settings.METRICS_AUTH_TOKEN = ""
        mock_settings.is_production.return_value = False
        mock_settings.ENVIRONMENT = "development"
        mock_settings.APP_VERSION = "0.0.0-test"

        instance = MockChecker.return_value

        async def _check_all():
            return fake_result

        instance.check_all = _check_all

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.get("/health/detailed")

    app.dependency_overrides.clear()
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall"] == "healthy"
    assert "uptime_seconds" in body
    assert body["app_version"] == "0.0.0-test"


# ==================== 5. ComponentStatus enum sanity ====================
def test_component_status_enum_values():
    assert ComponentStatus.UP.value == "up"
    assert ComponentStatus.DOWN.value == "down"
    assert ComponentStatus.DEGRADED.value == "degraded"
