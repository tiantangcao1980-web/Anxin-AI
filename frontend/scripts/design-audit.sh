#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC_DIR="$ROOT_DIR/src"
STRICT="${1:-}"

echo "== Anxin Frontend Design Audit =="
echo "workspace: $ROOT_DIR"
echo

echo "-- Hardcoded colors (sample) --"
rg -n "#[0-9A-Fa-f]{3,8}|rgb\\(|rgba\\(|hsl\\(" "$SRC_DIR" \
  --glob '!**/*.test.*' \
  --glob '!**/assets/**' \
  --glob '!**/vite-env.d.ts' \
  --glob '!**/lib/design-tokens.ts' \
  --glob '!**/index.css' \
  | sed -n '1,80p' || true
echo

echo "-- Icon drift (direct imports / emoji / text-as-icon sample) --"
{
  rg -n "from 'lucide-react'|from \"lucide-react\"|from '@heroicons/react'|from \"@heroicons/react\"" "$SRC_DIR" \
    --glob '!**/components/ui/**' \
    --glob '!**/lib/icons.ts' || true
  rg -n "🔍|⚖️|📄|💡|🏢|❤️|⭐|🎙️" "$SRC_DIR" || true
} | sed -n '1,80p'
echo

echo "-- focus-visible coverage (sample) --"
rg -n "focus-visible|focus:ring|focus:border|disabled:opacity|disabled:pointer-events-none" "$SRC_DIR" \
  | sed -n '1,80p' || true
echo

echo "-- Typography drift (font-bold / tracking-wide sample) --"
rg -n "font-bold|tracking-wide|tracking-wider|tracking-\\[" "$SRC_DIR" \
  | sed -n '1,80p' || true
echo

echo "-- Shadow drift (custom shadow sample) --"
rg -n "shadow-\\[|box-shadow:" "$SRC_DIR" \
  | sed -n '1,80p' || true
echo

echo "-- Radius drift summary --"
rg -o "rounded(-[trbl]{1,2})?-(none|sm|md|lg|xl|2xl|3xl|full)|rounded\\b" "$SRC_DIR" \
  | sed 's/.*://' \
  | sort | uniq -c | sort -nr | sed -n '1,40p' || true
echo

echo "-- Spacing drift summary --"
rg -o "\\b(p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|gap|space-x|space-y)-([0-9]+(\\.5)?|\\[[^]]+\\])" "$SRC_DIR" \
  | sed 's/.*-//' \
  | sort | uniq -c | sort -nr | sed -n '1,40p' || true
echo

if [[ "$STRICT" == "--strict" ]]; then
  HARD_CODED_COUNT="$(rg -n "#[0-9A-Fa-f]{3,8}|rgb\\(|rgba\\(|hsl\\(" "$SRC_DIR" \
    --glob '!**/*.test.*' \
    --glob '!**/assets/**' \
    --glob '!**/vite-env.d.ts' \
    | wc -l | tr -d ' ')"
  if [[ "${HARD_CODED_COUNT}" != "0" ]]; then
    echo "STRICT MODE FAILED: found ${HARD_CODED_COUNT} hardcoded color references."
    exit 1
  fi
fi

echo "Audit complete."
