#!/usr/bin/env bash
# Supporting iOS Simulator app-run smoke for the Expo mobile app.
#
# This proves the local Expo app can boot Metro, install/open Expo Go on an
# iOS Simulator, and complete an iOS JS bundle. It is not production device
# evidence and must not mark mobile-device release evidence complete.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/mobile-ios-simulator-smoke.sh --out path --log-out path [options]

Options:
  --out path             Write a structured JSON artifact.
  --log-out path         Write the Metro / Expo transcript.
  --device-name name     Simulator name to boot. Default: iPhone 17.
  --port number          Metro port. Default: 19001.
  --timeout seconds      Wait for iOS bundle completion. Default: 90.
  -h, --help             Show this help.

Environment:
  IOS_SIMULATOR_UDID     Use an explicit simulator UDID instead of resolving by name.
EOF
}

OUT_PATH=""
LOG_OUT_PATH=""
DEVICE_NAME="iPhone 17"
PORT="19001"
TIMEOUT_SECONDS="90"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --out)
      OUT_PATH="${2:-}"
      shift 2
      ;;
    --log-out)
      LOG_OUT_PATH="${2:-}"
      shift 2
      ;;
    --device-name)
      DEVICE_NAME="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --timeout)
      TIMEOUT_SECONDS="${2:-}"
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

if [ -z "$OUT_PATH" ] || [ -z "$LOG_OUT_PATH" ]; then
  usage
  echo "ERROR: --out and --log-out are required" >&2
  exit 2
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MOBILE_DIR="$PROJECT_ROOT/mobile"
mkdir -p "$(dirname "$OUT_PATH")" "$(dirname "$LOG_OUT_PATH")"

if [ -n "${IOS_SIMULATOR_UDID:-}" ]; then
  DEVICE_UDID="$IOS_SIMULATOR_UDID"
else
  DEVICE_UDID="$(
    xcrun simctl list devices available \
      | awk -F '[()]' -v name="$DEVICE_NAME" '$0 ~ name " \\(" {print $2; exit}'
  )"
fi

if [ -z "$DEVICE_UDID" ]; then
  echo "ERROR: no available iOS Simulator matched '$DEVICE_NAME'" >&2
  exit 1
fi

TSCONFIG_BACKUP="$(mktemp)"
cp "$MOBILE_DIR/tsconfig.json" "$TSCONFIG_BACKUP"
EXPO_PID=""

cleanup() {
  if [ -n "$EXPO_PID" ] && kill -0 "$EXPO_PID" 2>/dev/null; then
    kill "$EXPO_PID" 2>/dev/null || true
    wait "$EXPO_PID" 2>/dev/null || true
    sleep 1
    kill -9 "$EXPO_PID" 2>/dev/null || true
  fi
  if ! cmp -s "$TSCONFIG_BACKUP" "$MOBILE_DIR/tsconfig.json"; then
    cp "$TSCONFIG_BACKUP" "$MOBILE_DIR/tsconfig.json"
  fi
  rm -f "$TSCONFIG_BACKUP"
}
trap cleanup EXIT

echo ">>> boot iOS Simulator: $DEVICE_NAME ($DEVICE_UDID)"
xcrun simctl boot "$DEVICE_UDID" >/tmp/anxin-mobile-ios-simulator-boot.log 2>&1 || true
xcrun simctl bootstatus "$DEVICE_UDID" -b

echo ">>> verify Expo Metro can resolve expo-asset"
(
  cd "$MOBILE_DIR"
  node - <<'NODE'
require.resolve("expo-asset/package.json");
const { getDefaultConfig } = require("expo/metro-config");
const config = getDefaultConfig(process.cwd());
if (!config || !config.resolver) {
  throw new Error("Expo Metro config did not instantiate");
}
NODE
)

echo ">>> start Expo on iOS Simulator"
: >"$LOG_OUT_PATH"
(
  cd "$MOBILE_DIR"
  npx expo start --localhost --port "$PORT" --go --ios
) >"$LOG_OUT_PATH" 2>&1 &
EXPO_PID="$!"

STATUS="failed"
FAIL_REASON="timeout_waiting_for_ios_bundle"
deadline=$((SECONDS + TIMEOUT_SECONDS))
last_open_attempt=0
while [ "$SECONDS" -lt "$deadline" ]; do
  if rg -q "Waiting on|Opening exp://" "$LOG_OUT_PATH"; then
    if [ $((SECONDS - last_open_attempt)) -ge 8 ]; then
      xcrun simctl openurl "$DEVICE_UDID" "exp://127.0.0.1:${PORT}" >/dev/null 2>&1 || true
      xcrun simctl openurl "$DEVICE_UDID" "exp://localhost:${PORT}" >/dev/null 2>&1 || true
      xcrun simctl openurl "$DEVICE_UDID" "http://localhost:${PORT}" >/dev/null 2>&1 || true
      last_open_attempt="$SECONDS"
    fi
  fi
  if rg -q "iOS Bundled" "$LOG_OUT_PATH"; then
    STATUS="passed"
    FAIL_REASON=""
    break
  fi
  if rg -q "Error:|CommandError|Input is required" "$LOG_OUT_PATH"; then
    FAIL_REASON="$(rg "Error:|CommandError|Input is required" "$LOG_OUT_PATH" | head -1)"
    break
  fi
  if ! kill -0 "$EXPO_PID" 2>/dev/null; then
    FAIL_REASON="expo_process_exited_before_ios_bundle"
    break
  fi
  sleep 2
done

if [ -n "$EXPO_PID" ] && kill -0 "$EXPO_PID" 2>/dev/null; then
  kill "$EXPO_PID" 2>/dev/null || true
  wait "$EXPO_PID" 2>/dev/null || true
  EXPO_PID=""
fi

EXPO_GO_CONTAINER="$(xcrun simctl get_app_container "$DEVICE_UDID" host.exp.Exponent 2>/dev/null || true)"
EXPO_GO_STATUS="missing"
if [ -n "$EXPO_GO_CONTAINER" ]; then
  EXPO_GO_STATUS="present"
fi

python3 - "$OUT_PATH" "$LOG_OUT_PATH" "$DEVICE_NAME" "$DEVICE_UDID" "$PORT" "$STATUS" "$FAIL_REASON" "$EXPO_GO_STATUS" "$EXPO_GO_CONTAINER" "$PROJECT_ROOT" <<'PY'
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
log_path = Path(sys.argv[2])
device_name = sys.argv[3]
device_udid = sys.argv[4]
port = sys.argv[5]
status = sys.argv[6]
fail_reason = sys.argv[7]
expo_go_status = sys.argv[8]
_expo_go_container = sys.argv[9]
project_root = sys.argv[10]

ansi_re = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
raw_lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines() if log_path.exists() else []
noise_fragments = (
    "Warning: The 'NO_COLOR' env is ignored due to the 'FORCE_COLOR' env being set.",
    "Use `node --trace-warnings ...` to show where the warning was created",
    "Web Bundling failed",
    'Unable to resolve "react-native-web/dist/index"',
)
raw_lines = [line for line in raw_lines if not any(fragment in line for fragment in noise_fragments)]
lines = [
    "".join(
        ch
        for ch in ansi_re.sub("", line)
        .replace(project_root, "<repo>")
        .encode("ascii", "ignore")
        .decode("ascii")
        if ch == "\t" or ord(ch) >= 32
    ).rstrip()
    for line in raw_lines
]
if log_path.exists():
    log_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
excerpt = [line for line in lines if line.strip()][-40:]
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "mobile_ios_simulator_expo_go_smoke",
    "status": status,
    "release_evidence_complete": False,
    "device": {
        "platform": "ios_simulator",
        "name": device_name,
        "udid": device_udid,
    },
    "checks": {
        "simulator_boot": "passed",
        "expo_asset_resolvable": "passed",
        "expo_metro_config": "passed",
        "expo_go_container": expo_go_status,
        "ios_bundle": "passed" if status == "passed" else "failed",
    },
    "command": f"cd mobile && npx expo start --localhost --port {port} --go --ios",
    "artifacts": {
        "log": str(log_path),
    },
    "transcript_excerpt": excerpt,
    "failure_reason": fail_reason,
    "notes": [
        "Supporting iOS Simulator + Expo Go evidence only; this is not signed App Store/TestFlight or physical-device evidence.",
        "Keep mobile-device smoke evidence Status: pending until iOS, Android, interactive WeChat DevTools or real-device runs and cross-device continuation are recorded.",
    ],
}
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote iOS simulator smoke artifact: {out_path}")
PY

if [ "$STATUS" != "passed" ]; then
  echo "iOS Simulator smoke failed: $FAIL_REASON" >&2
  exit 1
fi

echo "iOS Simulator smoke passed."
