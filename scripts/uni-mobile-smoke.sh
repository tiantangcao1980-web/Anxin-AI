#!/usr/bin/env bash
# Code-level uni-app base smoke checks.
#
# This verifies the new apps/uni-mobile base can typecheck, run contract tests,
# build H5, build WeChat Mini Program output, and keep production npm audit clean.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/uni-mobile-smoke.sh [--out path]

Options:
  --out path   Write a structured JSON artifact.
  -h, --help   Show this help.
EOF
}

OUT_PATH=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --out)
      OUT_PATH="${2:-}"
      if [ -z "$OUT_PATH" ]; then
        usage
        echo "ERROR: --out requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage
      echo "ERROR: unknown option: $1" >&2
      exit 2
      ;;
  esac
done

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$PROJECT_ROOT/apps/uni-mobile"

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

if [ ! -d "$APP_DIR/node_modules" ]; then
  run_step "uni-mobile dependency install" bash -lc "cd '$APP_DIR' && npm install"
fi

run_step "uni-mobile typecheck" bash -lc "cd '$APP_DIR' && npm run typecheck"
run_step "uni-mobile contract tests" bash -lc "cd '$APP_DIR' && npm test"
run_step "uni-mobile production npm audit" bash -lc "cd '$APP_DIR' && npm run audit:prod"
run_step "uni-mobile H5 build" bash -lc "cd '$APP_DIR' && npm run build:h5"
run_step "uni-mobile WeChat Mini Program build" bash -lc "cd '$APP_DIR' && npm run build:mp-weixin"

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "uni_mobile_base_smoke",
    "status": "passed",
    "release_evidence_complete": False,
    "checks": {
        "typecheck": "passed",
        "contract_tests": "passed",
        "production_npm_audit": "passed",
        "build_h5": "passed",
        "build_mp_weixin": "passed",
    },
    "scope": {
        "base": "apps/uni-mobile",
        "legacy_mobile": "mobile/",
        "legacy_mini_program": "mini-program/",
    },
    "completion_note": (
        "Code-level uni-app base evidence only. Keep mobile-device smoke evidence "
        "Status: pending until real iOS, Android, WeChat DevTools/device, DCloud "
        "App build, and cross-device continuation evidence are attached."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote uni-mobile smoke artifact: {out_path}")
PY
fi

echo
echo "uni-mobile code-level smoke complete."
