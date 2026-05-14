"""
安心智能助手系统 - 主入口
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.routes import api_router
from src.api.routes.health import router as health_router
from src.core.config import settings
from src.core.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期管理"""
    webhook_retry_stop_event: asyncio.Event | None = None
    webhook_retry_task: asyncio.Task[None] | None = None

    # 启动时
    logger.info("🚀 安心智能助手系统启动中...")

    # P19-A: Sentry 初始化（DSN 缺失则 noop）
    try:
        from src.services.monitoring import setup_sentry
        setup_sentry()
    except Exception as e:
        logger.warning(f"Sentry 初始化失败（不影响启动）: {e}")

    # ===== [S-02] 安全检查：生产环境禁止启用 DEV_MODE =====
    # 原因：DEV_MODE 会跳过所有认证，生产环境如果误开等于无认证
    # 修复方式：启动时检测配置组合，不合法则拒绝启动
    if settings.ENVIRONMENT == "production" and settings.DEV_MODE:
        raise RuntimeError(
            "❌ 安全检查失败：生产环境禁止启用 DEV_MODE！\n"
            "请在 .env 中设置 DEV_MODE=false 或移除该配置。"
        )
    if settings.DEV_MODE:
        logger.warning("⚠️ DEV_MODE 已启用 - 认证将被跳过，仅限开发环境使用！")

    # 初始化数据库
    try:
        await init_db()
        logger.info("✅ 数据库初始化完成")
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败，应用停止启动: {e}")
        raise

    logger.info(f"📍 API文档: http://localhost:{settings.BACKEND_PORT}/docs")

    if settings.WEBHOOK_RETRY_WORKER_ENABLED:
        from src.services.webhook_retry_worker import webhook_retry_worker

        webhook_retry_stop_event = asyncio.Event()
        webhook_retry_task = asyncio.create_task(webhook_retry_worker(webhook_retry_stop_event))

    yield

    # 关闭时
    if webhook_retry_stop_event is not None and webhook_retry_task is not None:
        webhook_retry_stop_event.set()
        try:
            await asyncio.wait_for(webhook_retry_task, timeout=5)
        except TimeoutError:
            webhook_retry_task.cancel()
            logger.warning("webhook 自动重试 worker 关闭超时，已取消任务")

    # 关闭共享 httpx 连接池
    try:
        from src.agents.base import BaseLegalAgent

        close_http_client = cast(Callable[[], Awaitable[None]], BaseLegalAgent.close_http_client)
        await close_http_client()
        logger.info("已关闭共享 httpx 连接池")
    except Exception as e:
        logger.warning(f"关闭 httpx 连接池失败: {e}")

    # 关闭事件总线
    try:
        from src.services.event_bus import event_bus

        disconnect_event_bus = cast(Callable[[], Awaitable[None]], event_bus.disconnect)
        await disconnect_event_bus()
    except Exception as e:
        logger.warning(f"关闭事件总线失败: {e}")

    # 关闭图数据库连接
    try:
        from src.services.graph_service import graph_service
        await graph_service.close()
    except Exception as e:
        logger.warning(f"关闭图数据库连接失败: {e}")

    await close_db()
    logger.info("安心智能助手系统关闭")


app = FastAPI(
    title="Anxin AI API",
    description="安心智能助手系统 - 基于多智能体协作的超级AI 智能助手系统",
    version="0.1.1",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    # redirect_slashes 保持默认 True — 路由统一使用 "" 而非 "/"
)

# ===== [S-01 + B-03] CORS 配置：从 settings 读取，不再硬编码 "*" =====
# 原因：allow_origins=["*"] + allow_credentials=True 违反 CORS 规范
#       且允许任意网站发起跨域请求，存在安全风险
# 修复方式：使用 config.py 中已定义的 CORS_ORIGINS（默认 ["http://localhost:3000"]）
#          生产环境通过 .env 的 CORS_ORIGINS 配置实际域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# ===== 反Bot防御中间件（后注册先执行，顺序：WAF → HMAC → ClientIntel → RiskScoring） =====
if settings.ANTIBOT_ENABLED:
    # Phase 3: 风控评分（最后执行，综合所有信号）— 最先注册
    if settings.ANTIBOT_RISK_SCORING_ENABLED:
        from src.middleware.risk_scoring import RiskScoringMiddleware
        app.add_middleware(RiskScoringMiddleware)
        logger.info("反Bot: 风控评分引擎已启用")

    # Phase 2: 客户端情报
    if settings.ANTIBOT_FINGERPRINT_ENABLED:
        from src.middleware.client_intel import ClientIntelMiddleware
        app.add_middleware(ClientIntelMiddleware)
        logger.info("反Bot: 客户端情报分析已启用")

    # Phase 1: HMAC 签名
    if settings.ANTIBOT_HMAC_ENABLED:
        from src.middleware.hmac_signature import HMACSignatureMiddleware
        app.add_middleware(HMACSignatureMiddleware)
        logger.info(f"反Bot: HMAC 签名验证已启用 (enforce={settings.ANTIBOT_HMAC_ENFORCE})")

    # Phase 1: WAF（较早执行，拦截明显攻击）
    if settings.ANTIBOT_WAF_ENABLED:
        from src.middleware.waf import WAFMiddleware
        app.add_middleware(WAFMiddleware)
        logger.info(f"反Bot: WAF 已启用 (log_only={settings.ANTIBOT_WAF_LOG_ONLY})")


# ===== P19-A 可观测中间件（最先注册 → 最先执行 → 包住其他所有 middleware） =====
from src.middleware.observability import ObservabilityMiddleware
app.add_middleware(ObservabilityMiddleware)


# ===== 安全响应头 =====
@app.middleware("http")
async def add_security_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.is_production():
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """请求参数验证失败 — 返回可读的中文错误"""
    errors = []
    for err in exc.errors():
        field = " → ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "验证失败")
        errors.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=422,
        content={
            "detail": "请求参数验证失败",
            "errors": errors,
        },
    )


# ===== [Phase 6] 全局异常处理器：生产环境不泄露内部错误 =====
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """全局未捕获异常处理"""
    logger.error(f"未捕获异常: {request.method} {request.url.path} - {type(exc).__name__}: {exc}")

    # ===== CREAO 自愈闭环 Slice 1: 5xx 错误上报 incident =====
    # 包在 try/except 里，绝不能让 hook 自身错误影响主响应
    try:
        import traceback as _tb
        from src.core.database import get_db_context
        from src.harness.incident_collector import IncidentCollector
        from src.schemas.incident import IncidentSource, IncidentSeverity
        from src.services.pii_service import pii_service

        path = str(request.url.path)
        severity = (
            IncidentSeverity.P0
            if path.startswith("/api/v1/payments")
            else IncidentSeverity.P2
        )

        async with get_db_context() as db:
            await IncidentCollector(db, pii_service).collect(
                source=IncidentSource.API_5XX,
                title=f"5xx on {path}",
                payload={
                    "path": path,
                    "method": request.method,
                    "error": str(exc)[:1000],
                    "trace": _tb.format_exc()[:2000],
                },
                severity=severity,
                route=path,
                fingerprint_keys=["path", "error"],
            )
    except Exception as hook_err:
        logger.error(f"incident hook failed: {hook_err}")

    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=500,
            content={"detail": "服务器内部错误，请稍后重试"},
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "detail": str(exc),
                "type": type(exc).__name__,
                "path": str(request.url.path),
            },
        )


@app.get("/")
async def root() -> dict[str, str]:
    """根路径"""
    return {
        "name": "Anxin AI",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


app.include_router(health_router)
