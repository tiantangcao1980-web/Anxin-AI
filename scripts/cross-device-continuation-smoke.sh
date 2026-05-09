#!/usr/bin/env bash
# Code-level cross-device conversation continuation rehearsal.
#
# This proves the local sync contracts across backend, desktop web adapter, and
# the new uni-app base. It does not prove signed desktop packages, real mobile
# devices, WeChat DevTools interaction, DCloud cloud build/signing, or a shared
# staging account session.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/cross-device-continuation-smoke.sh [--out path]

Options:
  --out path   Write a structured JSON artifact after all checks pass.
  -h, --help   Show this help.

Checks:
  - backend SyncService cross-device no-lost/no-duplicate continuation test
  - frontend desktop sync adapter Vitest slice
  - uni-app sync client contract tests
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
cd "$PROJECT_ROOT"

resolve_artifact_path() {
  local value="$1"
  if [ -z "$value" ]; then
    return 0
  fi
  if [[ "$value" = /* ]]; then
    printf '%s\n' "$value"
  else
    printf '%s/%s\n' "$PROJECT_ROOT" "$value"
  fi
}

OUT_PATH="$(resolve_artifact_path "$OUT_PATH")"

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

run_step "backend cross-device SyncService continuation" \
  bash -lc "cd backend && ./.venv/bin/pytest -q tests/test_sync_log_service.py"

run_step "frontend desktop sync adapter" \
  bash -lc "cd frontend && npm test -- api-adapter.sync.test.ts"

run_step "uni-mobile sync client contract" \
  bash -lc "cd apps/uni-mobile && npm test -- src/services/sync.test.ts src/services/api.test.ts"

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "cross_device_continuation_code_smoke",
    "status": "passed",
    "release_evidence_complete": False,
    "runtime_evidence_complete": False,
    "checks": {
        "backend_sync_service_continuation": "passed",
        "frontend_desktop_sync_adapter": "passed",
        "uni_mobile_sync_client_contract": "passed",
    },
    "covered_flow": [
        "desktop pushes conversation and first message to backend SyncService",
        "web and mobile pull the same conversation/message set without duplicate entity ids",
        "uni-mobile pushes a reply against the latest server version",
        "desktop pulls the mobile reply incrementally without lost rows",
    ],
    "scope": {
        "backend": "backend/src/services/sync_service.py",
        "desktop": "frontend/src/lib/api-adapter.ts",
        "future_mobile": "apps/uni-mobile/src/services/sync.ts",
        "legacy_mobile": "mobile/ and mini-program/ remain reference-only until migration evidence closes",
        "evidence_level": "code_level_rehearsal",
    },
    "pending_external_evidence": [
        "signed_notarized_desktop_package",
        "real_ios_device_or_official_app_build",
        "real_android_device_or_official_app_build",
        "interactive_wechat_devtools_or_real_mini_program_device",
        "dcloud_app_cloud_build_and_signing",
        "shared_staging_account_cross_device_session",
    ],
    "completion_note": (
        "Supporting code-level rehearsal only. Keep desktop-runtime and mobile-device "
        "evidence Status: pending until signed desktop package, real/official mobile "
        "device runs, interactive WeChat/DCloud evidence, and a shared staging account "
        "cross-device continuation transcript are attached."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote cross-device continuation artifact: {out_path}")
PY
fi

echo
echo "cross-device continuation code-level smoke complete."
