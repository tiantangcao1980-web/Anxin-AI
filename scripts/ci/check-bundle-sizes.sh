#!/usr/bin/env bash
# scripts/ci/check-bundle-sizes.sh
# 5 端 dist size 限额校验。failure exit 1。
#
# 用法：
#   bash scripts/ci/check-bundle-sizes.sh                # 所有端
#   bash scripts/ci/check-bundle-sizes.sh frontend       # 仅 frontend
#   bash scripts/ci/check-bundle-sizes.sh mini-program   # 仅 mini-program
#
# 限额（KB）：
#   frontend dist 主 chunk         < 1024 KB (1 MB)
#   frontend dist 总               < 5120 KB (5 MB)
#   mini-program weapp 主包        < 1536 KB (1.5 MB)
#   mini-program weapp 总          < 8192 KB (8 MB)
#   mini-program h5 entrypoint     < 430 KB（沿用 mini-program/scripts/check-bundle-size.js）
#   mobile bundle (expo export)    < 6144 KB (6 MB) — 仅在 dist 存在时检查
#   desktop bundle (tauri release) — 不在 CI 检查（platform-specific binary）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET="${1:-all}"
EXIT_CODE=0

# bytes -> KB（向上取整）
to_kb() { echo $(( ($1 + 1023) / 1024 )); }

check_size_limit() {
  local name="$1" actual="$2" limit_kb="$3"
  local actual_kb
  actual_kb=$(to_kb "$actual")
  if [ "$actual_kb" -gt "$limit_kb" ]; then
    echo "  [FAIL] ${name}: ${actual_kb} KB > limit ${limit_kb} KB"
    EXIT_CODE=1
  else
    echo "  [OK]   ${name}: ${actual_kb} KB <= ${limit_kb} KB"
  fi
}

dir_size_bytes() {
  local d="$1"
  if [ -d "$d" ]; then
    # macOS / linux 兼容
    if du -sb "$d" >/dev/null 2>&1; then
      du -sb "$d" | awk '{print $1}'
    else
      # macOS BSD du 没 -b，用 -k * 1024
      du -sk "$d" | awk '{print $1*1024}'
    fi
  else
    echo 0
  fi
}

check_frontend() {
  echo "[frontend] 检查 dist 大小..."
  local dist="$ROOT/frontend/dist"
  if [ ! -d "$dist" ]; then
    echo "  [SKIP] $dist 不存在（先 npm run build）"
    return
  fi

  # 主 chunk：assets/index-*.js 中最大者
  local main_js
  main_js=$(find "$dist/assets" -maxdepth 1 -name 'index-*.js' -type f 2>/dev/null | head -1 || true)
  if [ -n "$main_js" ] && [ -f "$main_js" ]; then
    local main_bytes
    main_bytes=$(wc -c <"$main_js" | tr -d ' ')
    check_size_limit "frontend main chunk ($(basename "$main_js"))" "$main_bytes" 1024
  else
    echo "  [WARN] 未找到 frontend/dist/assets/index-*.js"
  fi

  # 总 dist
  local total
  total=$(dir_size_bytes "$dist")
  check_size_limit "frontend dist 总" "$total" 5120
}

check_mini_program() {
  echo "[mini-program] 检查 weapp 主包/总包大小..."
  local dist="$ROOT/mini-program/dist"
  if [ ! -d "$dist" ]; then
    echo "  [SKIP] $dist 不存在（先 npm run build:weapp）"
    return
  fi

  # 主包：dist 根下 app.js + 主页 JS。Taro weapp 主包是 dist 根目录非 subpackages 部分。
  local main_pkg_bytes=0
  for f in "$dist"/*.js "$dist"/*.wxss "$dist"/*.json "$dist"/*.wxml; do
    [ -f "$f" ] || continue
    local s
    s=$(wc -c <"$f" | tr -d ' ')
    main_pkg_bytes=$((main_pkg_bytes + s))
  done
  # 加上 pages 主目录（非 subpackages）
  if [ -d "$dist/pages" ]; then
    main_pkg_bytes=$((main_pkg_bytes + $(dir_size_bytes "$dist/pages")))
  fi
  check_size_limit "mini-program 主包" "$main_pkg_bytes" 1536

  # 总包
  local total
  total=$(dir_size_bytes "$dist")
  check_size_limit "mini-program 总包" "$total" 8192
}

check_mobile() {
  echo "[mobile] 检查 expo bundle 大小..."
  local dist="$ROOT/mobile/dist"
  if [ ! -d "$dist" ]; then
    echo "  [SKIP] $dist 不存在（CI 不强制 export）"
    return
  fi
  local total
  total=$(dir_size_bytes "$dist")
  check_size_limit "mobile dist 总" "$total" 6144
}

case "$TARGET" in
  frontend)     check_frontend ;;
  mini-program) check_mini_program ;;
  mobile)       check_mobile ;;
  all)
    check_frontend
    check_mini_program
    check_mobile
    ;;
  *)
    echo "未知 target: $TARGET（合法：all/frontend/mini-program/mobile）"
    exit 2
    ;;
esac

if [ "$EXIT_CODE" -ne 0 ]; then
  echo ""
  echo "[bundle-size] 校验失败，请检查 dist 大小或调整限额。"
  exit 1
fi

echo ""
echo "[bundle-size] 全部通过。"
