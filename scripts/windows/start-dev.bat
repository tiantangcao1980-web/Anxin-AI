@echo off
chcp 65001 >nul
echo ================================================
echo   AI法务智能体系统 - 全面启动开发环境
echo ================================================
echo.

cd /d "%~dp0"

echo [1/3] 检查并启动基础设施...
call deploy-infrastructure.bat
if %errorlevel% neq 0 (
    echo ❌ 基础设施启动失败
    pause
    exit /b 1
)

echo.
echo [2/3] 启动后端服务 (Port: 8001)...
start "AI Legal Backend" cmd /k "cd backend && uv run uvicorn src.api.main:app --reload --port 8001 --host 0.0.0.0"

echo.
echo [3/3] 启动前端服务 (Port: 3000 -> Proxy: 8001)...
start "AI Legal Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ================================================
echo   ✅ 所有服务已启动!
echo ================================================
echo.
echo 请访问: http://localhost:3000
echo.
echo 登录账号: admin@example.com
echo 登录密码: admin123
echo.
pause
