#!/usr/bin/env bash
# scripts/ci/upload-artifacts.sh
# 收集 5 端构建产物到一个目录，可选 dry-run 上传到 GH Releases。
#
# 用法：
#   bash scripts/ci/upload-artifacts.sh                  # dry-run（只收集）
#   bash scripts/ci/upload-artifacts.sh --tag v3.0.0     # 上传到指定 tag（需 gh + GH_TOKEN）
#
# 默认 dry-run，只把 5 端产物拷贝到 ./_artifacts/
# 收集内容：
#   backend/         - dist (FastAPI not packaged，跳过；只收 README + pyproject)
#   frontend/dist    - vite 产物
#   mobile/dist      - expo export（如有）
#   mini-program/dist - taro weapp + h5
#   desktop/target   - tauri release bundle（如有）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT="${ROOT}/_artifacts"
TAG=""
DRY_RUN=true

while [ $# -gt 0 ]; do
  case "$1" in
    --tag)   TAG="$2"; DRY_RUN=false; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -h|--help)
      sed -n '2,16p' "$0"
      exit 0
      ;;
    *) echo "未知参数: $1"; exit 2 ;;
  esac
done

rm -rf "$OUT"
mkdir -p "$OUT"

collect() {
  local label="$1" src="$2" dst="$3"
  if [ -e "$src" ]; then
    echo "[collect] ${label}: ${src} -> ${dst}"
    mkdir -p "$(dirname "$dst")"
    cp -R "$src" "$dst"
  else
    echo "[skip]    ${label}: ${src} 不存在"
  fi
}

collect "backend (manifest)" "$ROOT/backend/pyproject.toml"             "$OUT/backend/pyproject.toml"
collect "backend (README)"   "$ROOT/backend/README.md"                  "$OUT/backend/README.md"
collect "frontend dist"      "$ROOT/frontend/dist"                      "$OUT/frontend"
collect "mobile dist"        "$ROOT/mobile/dist"                        "$OUT/mobile"
collect "mini-program weapp" "$ROOT/mini-program/dist"                  "$OUT/mini-program"

# Tauri bundle 路径平台不同，扫所有 release/bundle/
if [ -d "$ROOT/desktop/target" ]; then
  while IFS= read -r f; do
    rel="${f#$ROOT/desktop/target/}"
    mkdir -p "$OUT/desktop/$(dirname "$rel")"
    cp "$f" "$OUT/desktop/$rel"
  done < <(find "$ROOT/desktop/target" -type f \( -name '*.dmg' -o -name '*.msi' -o -name '*.AppImage' -o -name '*.deb' -o -name '*.exe' -o -name '*.apk' \) 2>/dev/null || true)
fi

echo ""
echo "[collect] 汇总（${OUT}）："
du -sh "$OUT"/* 2>/dev/null || echo "  (空)"

if [ "$DRY_RUN" = "true" ]; then
  echo ""
  echo "[dry-run] 完成。如需上传到 GH Releases："
  echo "  bash scripts/ci/upload-artifacts.sh --tag v3.0.0"
  exit 0
fi

if [ -z "$TAG" ]; then
  echo "[error] --tag 不能为空"
  exit 2
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "[error] gh CLI 未安装，无法上传"
  exit 2
fi

echo ""
echo "[upload] 上传 ${OUT} 到 release ${TAG}（dry-run 后请手动确认）..."
echo "  gh release upload \"${TAG}\" ${OUT}/* --clobber"
echo ""
echo "[upload] 出于安全考虑此脚本不自动执行 gh release upload。"
echo "         如确认上传，复制上述命令手动执行。"
