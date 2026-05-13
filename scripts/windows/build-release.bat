@echo off
chcp 65001 >nul
echo ================================================
echo   安心智能助手系统 - 生产环境构建与部署
echo ================================================
echo.

cd /d "%~dp0"

echo [1/4] 检查Docker环境...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker 未安装或未运行
    pause
    exit /b 1
)
echo ✅ Docker 环境检查通过

echo.
echo [2/4] 构建生产镜像 (这可能需要几分钟)...
echo 正在构建 Frontend 和 Backend...
docker-compose build
if %errorlevel% neq 0 (
    echo ❌ 镜像构建失败
    pause
    exit /b 1
)
echo ✅ 镜像构建完成

echo.
echo [3/4] 启动全栈服务 (生产模式)...
docker-compose up -d
if %errorlevel% neq 0 (
    echo ❌ 服务启动失败
    pause
    exit /b 1
)

echo.
echo [4/4] 检查服务状态...
timeout /t 5 >nul
docker-compose ps

echo.
echo ================================================
echo   🎉 部署完成！
echo ================================================
echo.
echo 访问地址:
echo - 前端应用: http://localhost:3000
echo - 后端API: http://localhost:8001
echo.
echo 管理员账号: admin@example.com / admin123
echo.
echo 如需停止服务，请运行: docker-compose down
echo.
pause
