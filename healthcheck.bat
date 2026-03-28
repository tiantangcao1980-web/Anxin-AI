@echo off
chcp 65001 >nul
echo ================================================
echo   AI法务智能体系统 - 健康检查脚本
echo ================================================
echo 时间: %date% %time%
echo.

setlocal

set FRONTEND=http://localhost:3000
set BACKEND=http://localhost:8001
set BACKEND_HEALTH=http://localhost:8001/health

echo [1/5] 检查前端服务...
curl -s -o nul -w "HTTP状态: %{http_code}" %FRONTEND% >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 前端服务正常运行
) else (
    echo ❌ 前端服务异常或未启动
)

echo [2/5] 检查后端服务...
curl -s -o nul -w "HTTP状态: %{http_code}" %BACKEND% >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 后端服务正常运行
) else (
    echo ❌ 后端服务异常或未启动
)

echo [3/5] 检查后端健康端点...
curl -s %BACKEND_HEALTH% | findstr /c:"healthy" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ 后端健康检查通过
) else (
    echo ⚠️  后端健康检查失败或未启动
)

echo [4/5] 检查Docker服务状态...
docker-compose ps | findstr "Up" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ Docker服务运行中
) else (
    echo ⚠️  部分Docker服务可能未启动
)

echo [5/5] 检查API文档...
curl -s -o nul -w "HTTP状态: %{http_code}" %BACKEND%/docs >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ API文档可访问
) else (
    echo ⚠️  API文档不可访问
)

echo.
echo ================================================
echo   健康检查完成
echo ================================================
echo.
echo 完整服务状态:
docker-compose ps

endlocal
pause
