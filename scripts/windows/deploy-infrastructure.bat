@echo off
chcp 65001 >nul
echo ================================================
echo   AI法务智能体系统 - 一键部署脚本
echo ================================================
echo.

cd /d "%~dp0"

echo [1/5] 检查Docker环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未安装或未运行
    echo 请先启动 Docker Desktop
    pause
    exit /b 1
)

docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose 未安装
    pause
    exit /b 1
)

echo ✅ Docker 环境检查通过
echo.

echo [2/5] 停止可能存在的旧服务...
docker-compose down >nul 2>&1
echo ✅ 旧服务已停止
echo.

echo [3/5] 启动基础设施服务 (PostgreSQL, Redis, Qdrant, Neo4j, MinIO)...
docker-compose up -d postgres redis qdrant neo4j minio
if %errorlevel% neq 0 (
    echo ❌ 基础设施服务启动失败
    pause
    exit /b 1
)
echo ✅ 基础设施服务已启动
echo.

echo [4/5] 等待服务健康检查...
echo 正在检查 PostgreSQL...
:wait_postgres
timeout /t 5 >nul
docker-compose exec -T postgres pg_isready -U postgres -q >nul 2>&1
if %errorlevel% neq 0 (
    echo 等待 PostgreSQL 启动...
    goto wait_postgres
)
echo ✅ PostgreSQL 就绪

echo 正在检查 Redis...
:wait_redis
timeout /t 3 >nul
docker-compose exec -T redis redis-cli ping >nul 2>&1
if %errorlevel% neq 0 (
    echo 等待 Redis 启动...
    goto wait_redis
)
echo ✅ Redis 就绪

echo 正在检查 Qdrant...
:wait_qdrant
timeout /t 3 >nul
curl -s http://localhost:6333/collections >nul 2>&1
if %errorlevel% neq 0 (
    echo 等待 Qdrant 启动...
    goto wait_qdrant
)
echo ✅ Qdrant 就绪

echo 正在检查 Neo4j...
:wait_neo4j
timeout /t 3 >nul
curl -s http://localhost:7474 >nul 2>&1
if %errorlevel% neq 0 (
    echo 等待 Neo4j 启动...
    goto wait_neo4j
)
echo ✅ Neo4j 就绪

echo 正在检查 MinIO...
:wait_minio
timeout /t 3 >nul
curl -s http://localhost:9000/minio/health/live >nul 2>&1
if %errorlevel% neq 0 (
    echo 等待 MinIO 启动...
    goto wait_minio
)
echo ✅ MinIO 就绪

echo.
echo [5/5] 验证所有服务状态...
docker-compose ps

echo.
echo ================================================
echo   基础设施部署完成！
echo ================================================
echo.
echo 接下来请执行以下步骤：
echo.
echo 1. 启动后端服务:
echo    cd backend
echo    uv run uvicorn src.api.main:app --reload --port 8001 --host 0.0.0.0
echo.
echo 2. 启动前端服务 (新终端):
echo    cd frontend
echo    npm run dev
echo.
echo 3. 访问地址:
echo    - 前端: http://localhost:3000
echo    - 后端API: http://localhost:8001
echo    - API文档: http://localhost:8001/docs
echo.
pause
