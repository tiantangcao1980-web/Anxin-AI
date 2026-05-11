#!/usr/bin/env bash
# scripts/ci/run-smoke.sh
# 本地一键跑全部 5 端 smoke。需要：
#   - python3.12 + uv
#   - node 22 + npm
#   - rust toolchain（仅 desktop）
#
# 用法：
#   bash scripts/ci/run-smoke.sh           # 跑全部 5 端
#   bash scripts/ci/run-smoke.sh fast      # 跳过 desktop（cargo 慢）
#   bash scripts/ci/run-smoke.sh backend   # 单端

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-all}"
RESULTS=()

run_step() {
  local name="$1"; shift
  echo ""
  echo "=========================================="
  echo "[smoke] ${name}"
  echo "=========================================="
  if "$@"; then
    RESULTS+=("[OK]   ${name}")
    return 0
  else
    RESULTS+=("[FAIL] ${name}")
    return 1
  fi
}

smoke_backend() {
  cd "$ROOT/backend"
  uv sync --extra dev >/dev/null 2>&1 || pip install -e . >/dev/null 2>&1 || true
  uv run python -c "import src.api.main; print('backend_import_ok')" \
    && uv run pytest -q tests/test_advanced_features.py tests/test_traceability.py
}

smoke_frontend() {
  cd "$ROOT/frontend"
  npm ci --legacy-peer-deps --silent && npm run lint && npm run build
}

smoke_mobile() {
  cd "$ROOT/mobile"
  npm ci --legacy-peer-deps --silent && npm run typecheck
}

smoke_mini_program() {
  cd "$ROOT/mini-program"
  npm ci --legacy-peer-deps --silent && npm run build:weapp
}

smoke_desktop() {
  cd "$ROOT/desktop"
  cargo check --all-targets
}

case "$TARGET" in
  backend)      run_step "Backend"     smoke_backend ;;
  frontend)     run_step "Frontend"    smoke_frontend ;;
  mobile)       run_step "Mobile"      smoke_mobile ;;
  mini-program) run_step "Mini Program" smoke_mini_program ;;
  desktop)      run_step "Desktop"     smoke_desktop ;;
  fast)
    run_step "Backend"      smoke_backend     || true
    run_step "Frontend"     smoke_frontend    || true
    run_step "Mobile"       smoke_mobile      || true
    run_step "Mini Program" smoke_mini_program || true
    ;;
  all)
    run_step "Backend"      smoke_backend     || true
    run_step "Frontend"     smoke_frontend    || true
    run_step "Mobile"       smoke_mobile      || true
    run_step "Mini Program" smoke_mini_program || true
    run_step "Desktop"      smoke_desktop     || true
    ;;
  *)
    echo "未知 target: $TARGET"
    echo "合法：all/fast/backend/frontend/mobile/mini-program/desktop"
    exit 2
    ;;
esac

echo ""
echo "=========================================="
echo "[smoke] 汇总报告"
echo "=========================================="
fail_count=0
for r in "${RESULTS[@]}"; do
  echo "  $r"
  case "$r" in
    \[FAIL\]*) fail_count=$((fail_count + 1)) ;;
  esac
done

if [ "$fail_count" -gt 0 ]; then
  echo ""
  echo "[smoke] $fail_count 个端失败。请查看上方日志。"
  exit 1
fi

echo ""
echo "[smoke] 全部通过。"
