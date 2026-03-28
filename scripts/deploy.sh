#!/bin/bash
# ============================================================
# AI法务智能体系统 - 服务器手动快速部署脚本
# ============================================================
# 当 GitHub Actions 自动部署失败时，可在服务器上手动执行此脚本
#
# 用法:
#   ./scripts/deploy.sh                    # 拉代码 + 重建全部
#   ./scripts/deploy.sh backend            # 仅重建后端
#   ./scripts/deploy.sh frontend           # 仅重建前端
#   ./scripts/deploy.sh backend frontend   # 重建后端和前端
# ============================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

SERVICES=("$@")
if [ ${#SERVICES[@]} -eq 0 ]; then
    SERVICES=("backend" "frontend")
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  AI法务智能体 - 手动部署${NC}"
echo -e "${GREEN}  服务: ${SERVICES[*]}${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 拉取最新代码
echo -e "${YELLOW}[1/4] 拉取最新代码...${NC}"
git pull
echo "当前版本: $(git log -1 --format='%h %s')"

# 构建
echo ""
echo -e "${YELLOW}[2/4] 构建镜像...${NC}"
DOCKER_BUILDKIT=1 COMPOSE_DOCKER_CLI_BUILD=1 docker compose build "${SERVICES[@]}"

# 重启 (不影响基础设施)
echo ""
echo -e "${YELLOW}[3/4] 重启服务...${NC}"
docker compose up -d --no-deps --force-recreate "${SERVICES[@]}"

# 检查
echo ""
echo -e "${YELLOW}[4/4] 检查状态...${NC}"
sleep 5
docker compose ps

echo ""
echo -e "${GREEN}✅ 部署完成! $(date '+%Y-%m-%d %H:%M:%S')${NC}"
