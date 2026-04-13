#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_DIR="$ROOT_DIR/src"

echo "== Anxin Frontend Cleanup Audit =="
echo "workspace: $ROOT_DIR"
echo

echo "-- Candidate dormant pages --"
for file in \
  "$SRC_DIR/pages/Dashboard.tsx" \
  "$SRC_DIR/pages/Experts.tsx" \
  "$SRC_DIR/pages/Knowledge.tsx" \
  "$SRC_DIR/pages/Search.tsx" \
  "$SRC_DIR/pages/News.tsx" \
  "$SRC_DIR/pages/AgentWorkflow.tsx" \
  "$SRC_DIR/pages/ConversationInsights.tsx"
do
  if [[ -f "$file" ]]; then
    echo "$file"
  fi
done
echo

echo "-- Asset reference counts --"
find "$SRC_DIR/assets" -type f | while read -r f; do
  base="$(basename "$f")"
  refs="$(rg -l --fixed-strings "$base" "$SRC_DIR" | wc -l | tr -d ' ')"
  echo "$refs $f"
done | sort -n
echo

echo "-- Direct lucide-react imports outside icons.ts --"
rg -n "from 'lucide-react'|from \"lucide-react\"" "$SRC_DIR" \
  | grep -v "/lib/icons.ts:" \
  | sed -n '1,120p' || true
echo

echo "-- Potential legacy redirects / replaced routes in App.tsx --"
rg -n "Navigate to=|v2.0 版本启用|旧路由兼容重定向" "$SRC_DIR/App.tsx" | sed -n '1,120p' || true
echo

echo "-- Heavy legacy styling hotspots (sample) --"
rg -n "shadow-\\[|rounded-3xl|font-bold|tracking-wide|tracking-wider|#[0-9A-Fa-f]{3,8}" "$SRC_DIR" \
  | sed -n '1,120p' || true
echo

echo "Cleanup audit complete."
