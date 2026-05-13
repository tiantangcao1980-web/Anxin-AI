@echo off
chcp 65001 >nul
setlocal

echo ================================================
echo   AI法务智能体系统 - 环境初始化脚本
echo ================================================
echo.

cd /d %~dp0

:: 1. 检查 Python 环境
echo [1/5] 检查 Python 环境...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未找到 Python。请安装 Python 3.11 或更高版本。
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)
echo Python 已安装。

:: 2. 检查 Node.js 环境
echo [2/5] 检查 Node.js 环境...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 未找到 Node.js。前端服务将无法运行。
    echo 请安装 Node.js 18 或更高版本。
    echo 下载地址: https://nodejs.org/
) else (
    echo Node.js 已安装。
)

:: 3. 初始化后端配置
echo [3/5] 初始化后端配置 (.env)...
cd backend
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo 已从 .env.example 创建 .env
    ) else (
        if exist ..\env.example.txt (
            copy ..\env.example.txt .env >nul
            echo 已从 env.example.txt 创建 .env
        )
    )
    
    :: 修正数据库端口 (5432 -> 5433) 以匹配 docker-compose 映射
    powershell -Command "(Get-Content .env) -replace 'localhost:5432', 'localhost:5433' | Set-Content .env"
    echo 已修正 .env 中的数据库端口为 5433 (匹配 Docker 映射)
) else (
    echo .env 已存在，跳过创建。
    echo [提示] 请确保 .env 中 DATABASE_URL 指向 localhost:5433 (如果使用 Docker 启动数据库)
)

:: 4. 安装后端依赖
echo [4/5] 安装后端依赖...
:: 清理可能损坏的 venv
if exist .venv (
    echo 检测到现有 .venv，尝试清理以避免路径错误...
    rmdir /s /q .venv
)

:: 使用 python venv 创建虚拟环境
echo 创建虚拟环境...
python -m venv .venv

:: 激活并安装依赖
echo 安装依赖 (这可能需要几分钟)...
call .venv\Scripts\activate
:: 升级 pip
python -m pip install --upgrade pip
:: 手动安装 tiktoken 最新版 (解决 Python 3.13 兼容性问题)
pip install "tiktoken>=0.12.0"
:: 安装 uv 以加速后续安装 (可选，这里直接用 pip 安装 uv)
pip install uv
:: 使用 uv 安装依赖
uv pip install -r pyproject.toml --system
if %errorlevel% neq 0 (
    echo [警告] uv 安装失败，尝试使用 pip 直接安装...
    pip install -e .
)

echo 后端依赖安装完成。
deactivate
cd ..

:: 5. 安装前端依赖
echo [5/5] 安装前端依赖...
cd frontend
if exist package.json (
    call npm install
    if %errorlevel% neq 0 (
        echo [错误] 前端依赖安装失败。
    ) else (
        echo 前端依赖安装完成。
    )
) else (
    echo [警告] 未找到 package.json，跳过前端依赖安装。
)
cd ..

echo.
echo ================================================
echo   初始化完成！
echo ================================================
echo.
echo 请按任意键退出...
pause >nul
