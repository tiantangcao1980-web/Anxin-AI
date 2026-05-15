#!/usr/bin/env bash
# 安心智能助手 · Managed Agent 一键部署
#
# 用法：
#   bash scripts/deploy-managed-agent.sh regulation-monitor
#   bash scripts/deploy-managed-agent.sh contract-renewal-watcher --local
#
# --local : 注册到本地 Celery beat（默认是上传到 Anthropic Managed Agents API）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COOKBOOK="${1:?usage: $0 <cookbook-name> [--local]}"
shift || true
MODE="api"
for arg in "$@"; do
  case "$arg" in
    --local) MODE="local" ;;
    *) echo "未知参数：$arg" >&2; exit 2 ;;
  esac
done

CB_DIR="${REPO_ROOT}/managed-agent-cookbooks/${COOKBOOK}"
[ -d "$CB_DIR" ] || { echo "找不到 cookbook：$CB_DIR" >&2; exit 1; }

echo "→ 校验 $COOKBOOK"
python3 "$REPO_ROOT/scripts/claude-plugin-validate.py" "managed-agent-cookbooks/$COOKBOOK"

if [ "$MODE" = "local" ]; then
  TARGET="$REPO_ROOT/backend/src/services/task_orchestrator/managed_agents/$(echo "$COOKBOOK" | tr '-' '_').py"
  if [ ! -f "$TARGET" ]; then
    echo "⚠  本地 Celery 任务模块未注册：$TARGET" >&2
    echo "   请按 backend/src/services/task_orchestrator/managed_agents/README.md 添加 task 入口。" >&2
    exit 3
  fi
  echo "→ 本地 Celery 任务已存在：$TARGET"
  echo "→ 重启 Celery worker + beat 即可生效："
  echo "    cd backend && celery -A src.services.task_orchestrator.celery_app:celery_app worker -l info -Q agent_tasks"
  echo "    cd backend && celery -A src.services.task_orchestrator.celery_app:celery_app beat -l info"
  exit 0
fi

# Cloud — Anthropic Managed Agents API
: "${ANTHROPIC_API_KEY:?需要环境变量 ANTHROPIC_API_KEY}"
echo "→ 上传 agent.yaml 到 Anthropic Managed Agents API"
curl -sS -X POST https://api.anthropic.com/v1/agents \
  -H "x-api-key: ${ANTHROPIC_API_KEY}" \
  -H "anthropic-version: 2025-10-01" \
  -H "content-type: application/yaml" \
  --data-binary "@$CB_DIR/agent.yaml" \
  | tee /tmp/anxin-managed-agent-$COOKBOOK.json

echo
echo "✅ 部署完成。响应已保存到 /tmp/anxin-managed-agent-$COOKBOOK.json"
