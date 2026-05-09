#!/usr/bin/env bash
# Supporting runtime smoke for an existing unsigned/signed desktop release .app.
#
# This proves the packaged release binary can self-test, start, and complete a
# WebView page-load handshake. It is still supporting evidence only until the
# package is signed/notarized and packaged-profile/cross-device evidence exists.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/desktop-release-runtime-smoke.sh [options]

Options:
  --app path        Release .app path. Defaults to desktop/target/release/bundle/macos/安心法务.app
  --out path        Write a structured JSON artifact.
  --ui-log-out path Copy the runtime UI smoke log to this path.
  -h, --help        Show this help.
EOF
}

APP_PATH="desktop/target/release/bundle/macos/安心法务.app"
OUT_PATH=""
UI_LOG_OUT_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --app)
      APP_PATH="${2:-}"
      if [ -z "$APP_PATH" ]; then
        usage
        echo "ERROR: --app requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    --out)
      OUT_PATH="${2:-}"
      if [ -z "$OUT_PATH" ]; then
        usage
        echo "ERROR: --out requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    --ui-log-out)
      UI_LOG_OUT_PATH="${2:-}"
      if [ -z "$UI_LOG_OUT_PATH" ]; then
        usage
        echo "ERROR: --ui-log-out requires a path" >&2
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

resolve_path() {
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

APP_PATH="$(resolve_path "$APP_PATH")"
OUT_PATH="$(resolve_path "$OUT_PATH")"
UI_LOG_OUT_PATH="$(resolve_path "$UI_LOG_OUT_PATH")"
BINARY_PATH="$APP_PATH/Contents/MacOS/anxin-legal-desktop"
DMG_DIR="$PROJECT_ROOT/desktop/target/release/bundle/dmg"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/anxin-release-runtime-smoke.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
SELF_TEST_JSON="$TMP_DIR/self-test.json"
SYNC_CODE_SMOKE_JSON="$TMP_DIR/sync-code-smoke.json"
SYNC_LOOPBACK_SMOKE_JSON="$TMP_DIR/sync-loopback-smoke.json"
RUNTIME_LOG="$TMP_DIR/runtime.log"
UI_LOG="$TMP_DIR/ui.log"

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

run_with_watchdog() {
  local log_path="$1"
  local timeout_seconds="$2"
  shift 2
  "$@" >"$log_path" 2>&1 &
  local app_pid=$!
  (
    sleep "$timeout_seconds"
    if kill -0 "$app_pid" 2>/dev/null; then
      echo "desktop release runtime smoke timed out; terminating pid=$app_pid" >>"$log_path"
      kill "$app_pid" 2>/dev/null || true
    fi
  ) &
  local watchdog_pid=$!
  set +e
  wait "$app_pid"
  local app_status=$?
  set -e
  kill "$watchdog_pid" 2>/dev/null || true
  wait "$watchdog_pid" 2>/dev/null || true
  if [ "$app_status" -ne 0 ]; then
    cat "$log_path"
    exit "$app_status"
  fi
}
export -f run_with_watchdog

run_step "release app binary exists" test -x "$BINARY_PATH"

run_step "release app binary self-test" bash -lc '
  binary_path="$1"
  self_test_json="$2"
  "$binary_path" --self-test >"$self_test_json"
  python3 - "$self_test_json" <<'"'"'PY'"'"'
import json
import sys

report = json.loads(open(sys.argv[1], encoding="utf-8").read())
required = {
    "offline_tasks",
    "app_settings",
    "sync_log",
    "local_messages",
    "local_documents",
    "local_cases",
    "local_contracts",
    "local_artifacts",
}
present = set(report.get("required_tables_present") or [])
missing = sorted(required - present)
if report.get("app") != "anxin-legal-desktop":
    raise SystemExit("unexpected app id")
if report.get("local_db_url") != "sqlcipher:anxin_local.db":
    raise SystemExit("unexpected local db url")
if report.get("migration_count") != 1:
    raise SystemExit("unexpected migration count")
if missing:
    raise SystemExit("missing tables: " + ", ".join(missing))
security = report.get("sqlite_security") or {}
if security.get("encrypted") is not True:
    raise SystemExit("sqlite_security.encrypted must be true")
if security.get("keyring_backed") is not True:
    raise SystemExit("sqlite_security.keyring_backed must be true")
if security.get("release_blocking") is not False:
    raise SystemExit("sqlite_security.release_blocking must be false")
print("release self-test ok: {} tables, sqlite encrypted={}".format(len(present), security.get("encrypted")))
PY
' bash "$BINARY_PATH" "$SELF_TEST_JSON"

run_step "release app sync code smoke" bash -lc '
  binary_path="$1"
  sync_code_smoke_json="$2"
  "$binary_path" --sync-code-smoke >"$sync_code_smoke_json"
  python3 - "$sync_code_smoke_json" <<'"'"'PY'"'"'
import json
import sys

report = json.loads(open(sys.argv[1], encoding="utf-8").read())
if report.get("mode") != "desktop_sync_code_smoke":
    raise SystemExit("unexpected sync code smoke mode")
if report.get("status") != "passed":
    raise SystemExit("sync code smoke did not pass")
if report.get("release_evidence_complete") is not False:
    raise SystemExit("sync code smoke must remain supporting evidence")
checks = report.get("checks") or {}
expected = {
    "pending_rows_decoded": 2,
    "push_payload_records": 2,
    "accepted_after_conflict": 1,
    "conflict_rows": 1,
    "pull_records_decoded": 1,
}
for key, value in expected.items():
    if checks.get(key) != value:
        raise SystemExit(f"sync code smoke {key} expected {value}, got {checks.get(key)}")
if checks.get("sync_log_migration") != "passed":
    raise SystemExit("sync code smoke migration check did not pass")
if checks.get("retry_needs_human") is not True:
    raise SystemExit("sync code smoke retry gate did not reach needs_human")
print("release sync code smoke ok: " + json.dumps(checks, ensure_ascii=False, sort_keys=True))
PY
' bash "$BINARY_PATH" "$SYNC_CODE_SMOKE_JSON"

run_step "release app runtime startup smoke" bash -lc '
  binary_path="$1"
  runtime_log="$2"
  run_with_watchdog "$runtime_log" 15 "$binary_path" --runtime-smoke
  grep -q "desktop runtime smoke starting" "$runtime_log"
  grep -q "desktop runtime smoke exiting" "$runtime_log"
  cat "$runtime_log"
' bash "$BINARY_PATH" "$RUNTIME_LOG"

run_step "release app sync loopback smoke" bash -lc '
  binary_path="$1"
  sync_loopback_smoke_json="$2"
  "$binary_path" --sync-loopback-smoke >"$sync_loopback_smoke_json"
  python3 - "$sync_loopback_smoke_json" <<'"'"'PY'"'"'
import json
import sys

report = json.loads(open(sys.argv[1], encoding="utf-8").read())
if report.get("mode") != "desktop_sync_loopback_smoke":
    raise SystemExit("unexpected sync loopback smoke mode")
if report.get("status") != "passed":
    raise SystemExit("sync loopback smoke did not pass")
if report.get("release_evidence_complete") is not False:
    raise SystemExit("sync loopback smoke must remain supporting evidence")
checks = report.get("checks") or {}
expected = {
    "pending_rows_decoded": 2,
    "push_payload_records": 2,
    "backend_received_records": 2,
    "accepted_after_conflict": 1,
    "conflict_rows": 1,
    "rows_synced": 1,
    "rows_conflicted": 1,
    "pull_records_written": 1,
    "cursor_advanced_to": 13,
}
for key, value in expected.items():
    if checks.get(key) != value:
        raise SystemExit(f"sync loopback smoke {key} expected {value}, got {checks.get(key)}")
if checks.get("loopback_backend") != "passed":
    raise SystemExit("sync loopback backend did not pass")
if checks.get("auth_header_received") is not True:
    raise SystemExit("sync loopback auth header was not observed")
if checks.get("retry_needs_human") is not True:
    raise SystemExit("sync loopback retry gate did not reach needs_human")
print("release sync loopback smoke ok: " + json.dumps(checks, ensure_ascii=False, sort_keys=True))
PY
' bash "$BINARY_PATH" "$SYNC_LOOPBACK_SMOKE_JSON"

run_step "release app WebView UI load smoke" bash -lc '
  binary_path="$1"
  ui_log="$2"
  run_with_watchdog "$ui_log" 20 "$binary_path" --runtime-ui-smoke
  grep -q "desktop runtime UI smoke starting" "$ui_log"
  grep -q "desktop runtime UI smoke response:" "$ui_log"
  grep -q "desktop runtime UI smoke exiting: frontend response received" "$ui_log"
  python3 - "$ui_log" <<'"'"'PY'"'"'
import json
import sys

log = open(sys.argv[1], encoding="utf-8").read()
line = next(
    (entry for entry in log.splitlines() if entry.startswith("desktop runtime UI smoke response: ")),
    "",
)
if not line:
    raise SystemExit("UI smoke response line missing")
payload = json.loads(line.replace("desktop runtime UI smoke response: ", "", 1))
has_page_load = (
    payload.get("pageLoadFinished") is True
    and payload.get("webviewLabel") == "main"
    and payload.get("windowLabel") == "main"
    and bool(payload.get("url"))
)
has_rendered_root = (
    payload.get("hasRoot") is True
    and int(payload.get("rootChildCount") or 0) >= 1
    and str(payload.get("platform") or "").startswith("tauri-")
)
if not has_page_load and not has_rendered_root:
    raise SystemExit("neither Tauri page-load nor rendered root evidence was present")
print("release UI smoke ok: " + json.dumps(payload, ensure_ascii=False, sort_keys=True))
PY
  cat "$ui_log"
' bash "$BINARY_PATH" "$UI_LOG"

if [ -n "$UI_LOG_OUT_PATH" ]; then
  mkdir -p "$(dirname "$UI_LOG_OUT_PATH")"
  cp "$UI_LOG" "$UI_LOG_OUT_PATH"
fi

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" "$APP_PATH" "$BINARY_PATH" "$SELF_TEST_JSON" "$SYNC_CODE_SMOKE_JSON" "$SYNC_LOOPBACK_SMOKE_JSON" "$UI_LOG_OUT_PATH" "$DMG_DIR" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
app_path = sys.argv[2]
binary_path = sys.argv[3]
self_test_path = Path(sys.argv[4])
sync_code_smoke_path = Path(sys.argv[5])
sync_loopback_smoke_path = Path(sys.argv[6])
ui_log_path = sys.argv[7]
dmg_dir = Path(sys.argv[8])
self_test = json.loads(self_test_path.read_text(encoding="utf-8"))
sync_code_smoke = json.loads(sync_code_smoke_path.read_text(encoding="utf-8"))
sync_loopback_smoke = json.loads(sync_loopback_smoke_path.read_text(encoding="utf-8"))
dmg_files = sorted(str(path) for path in dmg_dir.glob("*.dmg")) if dmg_dir.exists() else []
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "desktop_release_runtime_unsigned_smoke",
    "status": "passed",
    "release_evidence_complete": False,
    "signed_or_notarized": False,
    "checks": {
        "release_app_exists": "passed",
        "release_dmg_exists": "passed" if dmg_files else "not_found",
        "release_binary_self_test": "passed",
        "release_sync_code_smoke": "passed",
        "release_sync_loopback_smoke": "passed",
        "release_runtime_startup": "passed",
        "release_webview_ui_load": "passed",
        "sync_code_smoke": sync_code_smoke["checks"],
        "sync_loopback_smoke": sync_loopback_smoke["checks"],
        "sqlite_security": {
            "status": "passed",
            "encrypted": self_test["sqlite_security"]["encrypted"],
            "keyring_backed": self_test["sqlite_security"]["keyring_backed"],
            "release_blocking": self_test["sqlite_security"]["release_blocking"],
        },
    },
    "artifacts": {
        "release_app": app_path,
        "release_binary": binary_path,
        "release_dmg": dmg_files[0] if dmg_files else "",
        "ui_log": ui_log_path,
    },
    "completion_note": (
        "Unsigned release packaged-runtime supporting evidence only. Keep desktop runtime evidence "
        "Status: pending until the package is signed/notarized and signed packaged-profile migration, "
        "signed packaged runtime performance, shared-staging sync, and cross-device continuation "
        "evidence are attached."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote desktop unsigned release runtime smoke artifact: {out_path}")
PY
fi

echo
echo "Desktop unsigned release runtime smoke complete."
