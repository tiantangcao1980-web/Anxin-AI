#!/usr/bin/env bash
# ============================================================================
# 安心智能助手 V3 - 生产环境一键部署脚本
# ============================================================================
# 用途：阿里云 ECS 首次部署 + 后续更新
# 域名：anxinai.com（需提前配置 DNS A 记录指向服务器 IP）
#
# 使用：
#   bash scripts/deploy-prod.sh init      # 首次部署（含 HTTPS 证书申请）
#   bash scripts/deploy-prod.sh update    # 更新代码 + 重启服务
#   bash scripts/deploy-prod.sh restart   # 仅重启服务
#
# 环境要求：
#   - Docker 20.10+
#   - Docker Compose v2
#   - 域名已指向服务器 IP
#   - .env 文件已配置（POSTGRES_PASSWORD, JWT_SECRET, OPENAI_API_KEY）
# ============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

DOMAIN="${DOMAIN:-anxinai.com}"
EMAIL="${LETSENCRYPT_EMAIL:-admin@anxinai.com}"
COMPOSE_FILE="docker-compose.prod.yml"

usage() {
  cat <<EOF
用法:
  $0 init      首次部署（申请 HTTPS 证书 + 启动服务）
  $0 update    更新代码 + 重启服务
  $0 restart   仅重启服务
  $0 logs      查看日志
  $0 status    查看服务状态
EOF
}

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

check_env() {
  log_info "检查环境配置..."

  if [ ! -f .env ]; then
    log_error ".env 文件不存在！请先复制 .env.prod.example 并填写配置。"
    exit 1
  fi

  if ! grep -q "POSTGRES_PASSWORD=" .env || ! grep -q "JWT_SECRET=" .env; then
    log_error ".env 文件缺少必需配置（POSTGRES_PASSWORD, JWT_SECRET）"
    exit 1
  fi

  if ! command -v docker &> /dev/null; then
    log_error "Docker 未安装！请先安装 Docker。"
    exit 1
  fi

  if ! docker compose version &> /dev/null; then
    log_error "Docker Compose v2 未安装！"
    exit 1
  fi

  log_success "环境检查通过"
}

init_https() {
  log_info "初始化 HTTPS 证书（Let's Encrypt）..."

  mkdir -p certbot/conf certbot/www

  # 先启动 nginx（HTTP only）用于 ACME 验证
  log_info "临时启动 nginx 用于域名验证..."
  docker compose -f "$COMPOSE_FILE" up -d nginx

  sleep 5

  # 申请证书
  log_info "申请 Let's Encrypt 证书（域名: $DOMAIN）..."
  docker compose -f "$COMPOSE_FILE" run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

  if [ $? -eq 0 ]; then
    log_success "HTTPS 证书申请成功"
  else
    log_error "HTTPS 证书申请失败！请检查域名 DNS 是否正确指向服务器 IP。"
    exit 1
  fi

  # 重启 nginx 启用 HTTPS
  docker compose -f "$COMPOSE_FILE" restart nginx
}

build_frontend() {
  log_info "构建前端..."
  cd frontend
  if [ ! -d node_modules ]; then
    npm ci --legacy-peer-deps
  fi
  npm run build
  cd ..
  log_success "前端构建完成"
}

deploy_init() {
  log_info "========================================="
  log_info "  安心智能助手 V3 - 首次部署"
  log_info "  域名: $DOMAIN"
  log_info "========================================="

  check_env
  build_frontend

  log_info "启动基础设施（Postgres + Redis + Chroma）..."
  docker compose -f "$COMPOSE_FILE" up -d postgres redis chroma

  log_info "等待数据库就绪..."
  sleep 10

  log_info "构建并启动后端..."
  docker compose -f "$COMPOSE_FILE" up -d --build backend

  log_info "运行数据库迁移..."
  docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

  init_https

  log_info "启动 certbot 自动续期..."
  docker compose -f "$COMPOSE_FILE" up -d certbot

  log_success "========================================="
  log_success "  部署完成！"
  log_success "  访问: https://$DOMAIN"
  log_success "========================================="
}

deploy_update() {
  log_info "更新代码并重启服务..."

  check_env

  log_info "拉取最新代码..."
  git pull

  build_frontend

  log_info "重建并重启后端..."
  docker compose -f "$COMPOSE_FILE" up -d --build --no-deps backend

  log_info "运行数据库迁移..."
  docker compose -f "$COMPOSE_FILE" exec -T backend alembic upgrade head

  log_info "重启 nginx..."
  docker compose -f "$COMPOSE_FILE" restart nginx

  log_success "更新完成！"
}

deploy_restart() {
  log_info "重启所有服务..."
  docker compose -f "$COMPOSE_FILE" restart
  log_success "重启完成"
}

show_logs() {
  docker compose -f "$COMPOSE_FILE" logs -f --tail=100
}

show_status() {
  docker compose -f "$COMPOSE_FILE" ps
}

case "${1:-}" in
  init)
    deploy_init
    ;;
  update)
    deploy_update
    ;;
  restart)
    deploy_restart
    ;;
  logs)
    show_logs
    ;;
  status)
    show_status
    ;;
  *)
    usage
    exit 1
    ;;
esac
