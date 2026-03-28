#!/usr/bin/env bash
# ============================================================
# AI法务智能体系统 - 本地开发环境一键配置
# ============================================================
# 用法: bash scripts/dev-setup.sh
#
# 功能:
#   1. 检查依赖（Docker, Node.js, Python）
#   2. 创建 .env 配置
#   3. 安装前后端依赖
#   4. 启动基础设施（PostgreSQL + Redis）
#   5. 初始化数据库
# ============================================================

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[信息]${NC} $1"; }
ok()    { echo -e "${GREEN}[完成]${NC} $1"; }
warn()  { echo -e "${YELLOW}[警告]${NC} $1"; }
fail()  { echo -e "${RED}[错误]${NC} $1"; exit 1; }

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "  ╔════════════════════════════════════════╗"
echo "  ║   AI法务智能体系统 - 开发环境配置      ║"
echo "  ╚════════════════════════════════════════╝"
echo ""

# ==================== 1. 检查依赖 ====================
info "检查系统依赖..."

# Docker
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    ok "Docker $DOCKER_VER"
else
    fail "未安装 Docker。请安装 Docker Desktop: https://www.docker.com/products/docker-desktop"
fi

# Docker Compose
if docker compose version &>/dev/null; then
    COMPOSE_VER=$(docker compose version --short 2>/dev/null || echo "v2+")
    ok "Docker Compose $COMPOSE_VER"
else
    fail "Docker Compose 不可用，请确保 Docker Desktop 已安装最新版本"
fi

# Docker daemon
if ! docker info &>/dev/null; then
    warn "Docker 未运行，正在启动..."
    open -a Docker 2>/dev/null || true
    for i in $(seq 1 30); do
        docker info &>/dev/null && break
        sleep 2
    done
    docker info &>/dev/null || fail "Docker 启动超时，请手动打开 Docker Desktop"
    ok "Docker 已启动"
fi

# Node.js
if command -v node &>/dev/null; then
    NODE_VER=$(node --version)
    ok "Node.js $NODE_VER"
else
    fail "未安装 Node.js。推荐使用 nvm 安装: https://github.com/nvm-sh/nvm"
fi

# Python
if command -v python3 &>/dev/null; then
    PY_VER=$(python3 --version | awk '{print $2}')
    ok "Python $PY_VER"
else
    fail "未安装 Python3。请安装 Python 3.11+: https://www.python.org/downloads/"
fi

# ==================== 2. 环境配置 ====================
info "检查环境配置文件..."

if [ ! -f ".env" ]; then
    warn ".env 不存在，从 .env.example 创建..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        ok "已创建 .env（请编辑填写 API 密钥）"
    else
        fail ".env.example 不存在"
    fi
else
    ok ".env 已存在"
fi

if [ ! -f "backend/.env" ]; then
    warn "backend/.env 不存在，创建开发配置..."
    cat > backend/.env << 'ENVEOF'
DEBUG=true
DEV_MODE=true
ADMIN_INITIAL_PASSWORD=admin123
BACKEND_PORT=8005
FRONTEND_PORT=3001
DATABASE_URL=postgresql://postgres:password@localhost:5433/legal_agent_db
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=admin
MINIO_SECRET_KEY=password
JWT_SECRET_KEY=dev-secret-key-change-in-prod
ENVEOF
    ok "已创建 backend/.env"
else
    ok "backend/.env 已存在"
fi

if [ ! -f "frontend/.env" ]; then
    cat > frontend/.env << 'ENVEOF'
VITE_API_BASE_URL=/api/v1
VITE_API_TARGET_URL=http://127.0.0.1:8005
ENVEOF
    ok "已创建 frontend/.env"
else
    ok "frontend/.env 已存在"
fi

# ==================== 3. 安装依赖 ====================
info "安装前端依赖..."
cd frontend
if [ -d "node_modules" ]; then
    ok "前端依赖已安装"
else
    npm ci --silent
    ok "前端依赖安装完成"
fi
cd "$PROJECT_ROOT"

info "安装后端依赖..."
cd backend
if python3 -c "import fastapi" &>/dev/null; then
    ok "后端依赖已安装"
else
    pip install -e . --quiet
    ok "后端依赖安装完成"
fi
cd "$PROJECT_ROOT"

# ==================== 4. 启动基础设施 ====================
info "启动数据库基础设施..."
docker compose -f docker-compose.dev.yml up -d postgres redis

# 等待 PostgreSQL 就绪
info "等待 PostgreSQL 就绪..."
for i in $(seq 1 30); do
    if docker exec ailegalagent-postgres-1 pg_isready -U postgres &>/dev/null 2>&1; then
        break
    fi
    sleep 1
done
ok "PostgreSQL 已就绪 (端口 5433)"
ok "Redis 已就绪 (端口 6379)"

# ==================== 5. 完成 ====================
echo ""
echo "  ╔════════════════════════════════════════════════╗"
echo "  ║           开发环境配置完成！                   ║"
echo "  ╠════════════════════════════════════════════════╣"
echo "  ║                                                ║"
echo "  ║  方式一: Docker 全容器化开发                   ║"
echo "  ║    make dev                                    ║"
echo "  ║                                                ║"
echo "  ║  方式二: 本地开发（推荐）                      ║"
echo "  ║    终端1: make backend                         ║"
echo "  ║    终端2: make frontend                        ║"
echo "  ║                                                ║"
echo "  ║  访问地址:                                     ║"
echo "  ║    前端: http://localhost:3001                  ║"
echo "  ║    后端: http://localhost:8005                  ║"
echo "  ║    API:  http://localhost:8005/docs             ║"
echo "  ║                                                ║"
echo "  ║  登录账号: admin@example.com / admin123        ║"
echo "  ║                                                ║"
echo "  ╚════════════════════════════════════════════════╝"
echo ""
