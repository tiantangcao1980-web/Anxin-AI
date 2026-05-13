@echo off
chcp 65001 >nul
echo ================================================
echo   AI法务智能体系统 - MCP Server
echo ================================================
echo.

cd /d "%~dp0"

echo Starting MCP Server (Stdio Mode)...
echo Press Ctrl+C to stop.
echo.

cd backend
uv run python -m src.mcp_server
pause
