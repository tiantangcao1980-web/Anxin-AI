# ============================================================
# 安心法务 - 私有化部署管理
# ============================================================
# 使用方式: make <目标>
# 查看帮助: make help
# ============================================================

.PHONY: help up down restart logs status health backup restore init seed clean migrate build dev verify verify-frontend verify-backend verify-backend-full sync-backend-dev reconcile-backend-db tauri-dev tauri-build

# 默认 Docker Compose 文件
COMPOSE := docker compose
COMPOSE_DEV := docker compose -f docker-compose.dev.yml
BACKEND_SMOKE_TESTS := tests/test_advanced_features.py tests/test_traceability.py tests/test_oa_integration.py tests/test_business_agents.py

# 备份目录
BACKUP_DIR ?= ./backups/$(shell date +%Y-%m-%d_%H-%M)

help: ## 显示所有可用命令
	@echo ""
	@echo "  安心法务 - 部署管理命令"
	@echo "  ========================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

up: ## 启动所有服务（后台运行）
	@echo ">>> 启动所有服务..."
	$(COMPOSE) --profile app up -d
	@echo ">>> 服务已启动，使用 'make logs' 查看日志"

down: ## 停止所有服务
	@echo ">>> 停止所有服务..."
	$(COMPOSE) --profile app down
	@echo ">>> 服务已停止"

restart: ## 重启所有服务
	@echo ">>> 重启所有服务..."
	$(COMPOSE) --profile app restart
	@echo ">>> 服务已重启"

logs: ## 查看服务日志（实时跟踪）
	$(COMPOSE) logs -f --tail=100

status: ## 查看服务运行状态
	@echo ">>> 服务状态："
	$(COMPOSE) ps -a

health: ## 执行健康检查
	@echo ">>> 执行健康检查..."
	@curl -sf http://localhost:$${BACKEND_PORT:-8001}/health | python3 -m json.tool 2>/dev/null || echo "后端服务不可达"

backup: ## 备份数据库和 Redis（自动清理 7 天前备份）
	@echo ">>> 开始备份..."
	@bash scripts/backup.sh

restore: ## 从备份恢复（用法: make restore BACKUP_DIR=./backups/2026-01-01_12-00）
	@if [ -z "$(BACKUP_DIR)" ]; then \
		echo "错误: 请指定备份目录，用法: make restore BACKUP_DIR=./backups/xxx"; \
		exit 1; \
	fi
	@bash scripts/restore.sh $(BACKUP_DIR)

init: ## 首次初始化（复制配置 + 启动服务 + 运行迁移）
	@echo ">>> 首次初始化..."
	@if [ ! -f .env ]; then \
		cp .env.template .env; \
		echo ">>> 已创建 .env 文件，请编辑后重新运行 make init"; \
		exit 0; \
	fi
	@echo ">>> 启动基础设施服务..."
	$(COMPOSE) up -d postgres redis qdrant neo4j minio
	@echo ">>> 等待服务就绪..."
	@sleep 10
	@echo ">>> 运行数据库迁移..."
	$(COMPOSE) --profile app run --rm backend alembic upgrade head || echo "迁移跳过（可能尚未配置）"
	@echo ">>> 启动应用服务..."
	$(COMPOSE) --profile app up -d
	@echo ">>> 初始化完成！访问 http://localhost:$${FRONTEND_PORT:-80}"

seed: ## 填充测试数据
	@echo ">>> 填充测试数据..."
	$(COMPOSE) --profile app exec backend python -m backend.scripts.seed_all || \
	$(COMPOSE) --profile app exec backend python scripts/seed_all.py || \
	echo "测试数据填充跳过（脚本未找到）"

clean: ## 清理所有容器和数据卷（危险操作！）
	@echo ">>> 警告: 此操作将删除所有数据！"
	@read -p "请输入 'DELETE-ALL' 确认: " confirm && [ "$$confirm" = "DELETE-ALL" ] || (echo "已取消" && exit 1)
	$(COMPOSE) --profile app down -v
	@docker image prune -f
	@echo ">>> 清理完成"

migrate: ## 运行数据库迁移
	@echo ">>> 运行数据库迁移..."
	$(COMPOSE) --profile app exec backend alembic upgrade head
	@echo ">>> 迁移完成"

build: ## 重新构建镜像
	@echo ">>> 构建镜像..."
	$(COMPOSE) --profile app build
	@echo ">>> 构建完成"

dev: ## 启动开发环境（使用 docker-compose.dev.yml）
	@echo ">>> 启动开发环境..."
	$(COMPOSE_DEV) up -d
	@echo ">>> 开发环境已启动"

sync-backend-dev: ## 同步后端开发依赖（pytest/ruff 等）
	@echo ">>> 同步后端开发依赖..."
	cd backend && UV_CACHE_DIR=/tmp/uv-cache uv sync --frozen --extra dev
	@echo ">>> 后端开发依赖已同步"

verify-frontend: ## 验证前端（lint + build）
	@echo ">>> 验证前端..."
	cd frontend && npm run lint
	cd frontend && npm run build
	@echo ">>> 前端验证通过"

verify-backend: ## 验证后端 smoke 基线（导入 + smoke tests）
	@echo ">>> 验证后端..."
	@test -x backend/.venv/bin/python || (echo "错误: 后端虚拟环境未就绪，请先运行 'make sync-backend-dev'" && exit 1)
	@test -x backend/.venv/bin/pytest || (echo "错误: pytest 未安装，请先运行 'make sync-backend-dev'" && exit 1)
	cd backend && ./.venv/bin/python -c "import src.api.main; print('backend_import_ok')"
	cd backend && ./.venv/bin/pytest -q $(BACKEND_SMOKE_TESTS)
	@echo ">>> 后端验证通过"

verify-backend-full: ## 运行后端全量检查（当前可能失败，供排查用）
	@echo ">>> 运行后端全量检查..."
	@test -x backend/.venv/bin/python || (echo "错误: 后端虚拟环境未就绪，请先运行 'make sync-backend-dev'" && exit 1)
	@test -x backend/.venv/bin/pytest || (echo "错误: pytest 未安装，请先运行 'make sync-backend-dev'" && exit 1)
	@test -x backend/.venv/bin/ruff || (echo "错误: ruff 未安装，请先运行 'make sync-backend-dev'" && exit 1)
	cd backend && ./.venv/bin/ruff check src tests
	cd backend && ./.venv/bin/pytest -q

reconcile-backend-db: ## 对齐开发库 schema 与 Alembic 版本状态
	@echo ">>> 检查并对齐后端开发数据库..."
	@test -x backend/.venv/bin/python || (echo "错误: 后端虚拟环境未就绪，请先运行 'make sync-backend-dev'" && exit 1)
	cd backend && ./.venv/bin/python scripts/reconcile_alembic_dev.py --apply
	@echo ">>> 后端开发数据库已对齐"

verify: ## 执行前后端最小校验
	@$(MAKE) verify-frontend
	@$(MAKE) verify-backend

# ==================== Tauri 桌面端 ====================

tauri-dev: ## 启动 Tauri 开发环境
	@echo "🖥️  启动安心法务桌面客户端..."
	cd desktop && cargo tauri dev

tauri-build: ## 构建桌面应用安装包
	@echo "📦 构建桌面应用..."
	cd desktop && cargo tauri build
	@echo "✅ 构建完成，安装包位于 desktop/target/release/bundle/"
