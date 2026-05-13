@echo off
chcp 65001 >nul
echo ================================================
echo   AI法务智能体系统 - 一键启动脚本
echo ================================================
echo.
echo [1/3] 启动基础设施服务...
docker-compose up -d postgres redis qdrant neo4j minio
echo.

echo [2/3] 启动后端服务...
start "AI Legal Agent - Backend" cmd /k "cd /d %~dp0backend && uv run uvicorn src.api.main:app --reload --port 8001 --host 0.0.0.0"
echo 后端服务启动中，请查看新打开的终端窗口
echo.

echo [3/3] 启动前端服务...
start "AI Legal Agent - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo 前端服务启动中，请查看新打开的终端窗口
echo.

echo ================================================
echo   服务启动完成！
echo ================================================
echo.
echo 访问地址:
echo   - 前端应用: http://localhost:3000
echo   - 后端API: http://localhost:8001
echo   - API文档: http://localhost:8001/docs
echo.
echo 服务日志查看:
echo   docker-compose logs -f backend
echo   docker-compose logs -f frontend
echo.
pause
