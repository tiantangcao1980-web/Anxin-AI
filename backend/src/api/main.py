"""
AI法务智能体系统 - 主入口
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from src.api.routes import api_router
from src.core.config import settings
from src.core.database import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("🚀 AI法务智能体系统启动中...")

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
        logger.warning(f"⚠️ 数据库初始化跳过: {e}")
    
    logger.info(f"📍 API文档: http://localhost:{settings.BACKEND_PORT}/docs")
    
    yield
    
    # 关闭时
    # 关闭共享 httpx 连接池
    try:
        from src.agents.base import BaseLegalAgent
        await BaseLegalAgent.close_http_client()
        logger.info("已关闭共享 httpx 连接池")
    except Exception as e:
        logger.warning(f"关闭 httpx 连接池失败: {e}")
    
    # 关闭事件总线
    try:
        from src.services.event_bus import event_bus
        await event_bus.disconnect()
    except Exception as e:
        logger.warning(f"关闭事件总线失败: {e}")
    
    await close_db()
    logger.info("AI法务智能体系统关闭")


app = FastAPI(
    title="AI Legal Agent API",
    description="AI法务智能体系统 - 基于多智能体协作的超级AI法务系统",
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

# 注册路由
app.include_router(api_router, prefix="/api/v1")


# ===== 请求验证错误处理（Pydantic 校验失败时返回友好消息） =====
from fastapi.exceptions import RequestValidationError

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
async def global_exception_handler(request: Request, exc: Exception):
    """全局未捕获异常处理"""
    logger.error(f"未捕获异常: {request.method} {request.url.path} - {type(exc).__name__}: {exc}")

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
async def root():
    """根路径"""
    return {
        "name": "AI Legal Agent",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


# 注册增强健康检查路由（替代简单的 /health）
from src.api.routes.health import router as health_router
app.include_router(health_router)
