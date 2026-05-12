#!/usr/bin/env bash
# ============================================================================
# desktop-demo-package.sh — 对内 Demo 版桌面端打包
#
# 用途：5/15 对内演示用，跳过签名/公证，产出可分发的 DMG/exe/AppImage。
# 产物：
#   - macOS: desktop/target/release/bundle/dmg/*.dmg
#   - Windows: desktop/target/release/bundle/nsis/*.exe
#   - Linux: desktop/target/release/bundle/appimage/*.AppImage
#
# 用户安装时：
#   - macOS：右键 DMG → 打开 → 系统偏好设置"仍要打开"（首次绕过 Gatekeeper）
#   - Windows：双击 exe → Defender 警告 → "更多信息" → "仍要运行"
#
# 使用：
#   bash scripts/desktop-demo-package.sh            # 当前平台
#   bash scripts/desktop-demo-package.sh --skip-fe  # 跳过前端构建（已构建过）
#   bash scripts/desktop-demo-package.sh --out /tmp/demo-artifact.json
#
# 真实发布版请用 scripts/desktop-release-package.sh（签名 + 公证 + 门禁）
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SKIP_FRONTEND=0
OUT_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-fe|--skip-frontend)
      SKIP_FRONTEND=1
      shift
      ;;
    --out)
      OUT_PATH="${2:-}"
      shift 2
      ;;
    -h|--help)
      sed -n '2,/^$/p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "ERROR: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

echo "==> Anxin Desktop Demo Package (unsigned)"
echo "   Repo: $REPO_ROOT"
echo "   Platform: $(uname -s) $(uname -m)"
echo ""

# -------- Step 1: frontend build --------
if [ "$SKIP_FRONTEND" -eq 0 ]; then
  echo "==> [1/3] Building frontend (vite)..."
  cd "$REPO_ROOT/frontend"
  if [ ! -d node_modules ]; then
    echo "    Installing dependencies..."
    npm ci
  fi
  npm run build
  echo "    frontend/dist generated"
else
  echo "==> [1/3] Skipping frontend build (--skip-fe)"
  if [ ! -d "$REPO_ROOT/frontend/dist" ]; then
    echo "ERROR: frontend/dist not found. Run without --skip-fe first." >&2
    exit 1
  fi
fi
echo ""

# -------- Step 2: tauri build (unsigned) --------
echo "==> [2/3] Building desktop (cargo tauri build --no-bundle false, unsigned)..."
cd "$REPO_ROOT/desktop"

# 确保 tauri.conf.json 里 signingIdentity 保持 null（unsigned）
if ! grep -q '"signingIdentity": null' tauri.conf.json; then
  echo "WARNING: tauri.conf.json signingIdentity is not null. Demo build expects null." >&2
fi

# 强制 release profile + 所有默认 bundle 目标
cargo tauri build 2>&1 | tail -40
echo ""

# -------- Step 3: collect artifacts --------
echo "==> [3/3] Collecting artifacts..."
BUNDLE_DIR="$REPO_ROOT/desktop/target/release/bundle"

if [ ! -d "$BUNDLE_DIR" ]; then
  echo "ERROR: Bundle dir not found: $BUNDLE_DIR" >&2
  exit 1
fi

ARTIFACTS_JSON="{\"platform\":\"$(uname -s)\",\"arch\":\"$(uname -m)\",\"artifacts\":["
FIRST=1

for sub in dmg app nsis msi appimage deb; do
  if [ -d "$BUNDLE_DIR/$sub" ]; then
    for f in "$BUNDLE_DIR/$sub"/*; do
      if [ -f "$f" ]; then
        size=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
        size_mb=$((size / 1024 / 1024))
        if [ "$FIRST" -eq 0 ]; then ARTIFACTS_JSON="${ARTIFACTS_JSON},"; fi
        ARTIFACTS_JSON="${ARTIFACTS_JSON}{\"type\":\"$sub\",\"path\":\"$f\",\"size_mb\":$size_mb}"
        FIRST=0
        echo "    $sub: $(basename "$f") (${size_mb} MB)"
      fi
    done
  fi
done

ARTIFACTS_JSON="${ARTIFACTS_JSON}],\"signed\":false,\"demo_mode\":true,\"built_at\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"}"

if [ -n "$OUT_PATH" ]; then
  printf "%s\n" "$ARTIFACTS_JSON" > "$OUT_PATH"
  echo ""
  echo "==> Artifact manifest: $OUT_PATH"
fi

echo ""
echo "==> DONE. Demo artifacts ready in $BUNDLE_DIR"
echo ""
echo "分发提示："
echo "  macOS DMG:  用户首次打开需右键→打开，或系统偏好设置→安全性→\"仍要打开\""
echo "  Windows:    用户首次打开 Defender 警告时点\"更多信息\"→\"仍要运行\""
echo "  真实签名版请用 scripts/desktop-release-package.sh（需 Apple ID + Windows EV 证书）"
