#!/usr/bin/env bash
# Code-level mobile and mini-program smoke checks.
#
# This script does not prove real iOS/Android/WeChat device behavior. It is a
# repeatable local preflight for the mobile-device release evidence.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/mobile-device-smoke.sh [options]

Options:
  --out path                   Write a code-level smoke JSON artifact after all checks pass.
  --manual-template-out path   Write a redaction-safe manual device evidence template.
  --skip-mini-build            Skip "npm run build:weapp".
  --skip-wechat-devtools       Skip WeChat DevTools CLI project smoke.
  -h, --help                   Show this help.

Checks:
  - mobile Vitest suite
  - mobile TypeScript check
  - Expo config/dependency guard
  - Expo doctor compatibility check
  - mini-program TypeScript check
  - mini-program WeChat build unless skipped
  - WeChat DevTools CLI can open/trust the built mini-program project unless skipped
  - static guards against known fake mobile/mini fallback regressions
  - static guard that mobile investigation/knowledge submissions render in-page result surfaces
  - static guard against mini-program primary navigation dead ends
  - static guard against refresh-token network failures clearing auth state
  - static guard that mobile and mini-program privacy modes fail closed before data network I/O
  - static guard that mini-program page/config colors come from design tokens
EOF
}

SKIP_MINI_BUILD=0
SKIP_WECHAT_DEVTOOLS=0
OUT_PATH=""
MANUAL_TEMPLATE_OUT_PATH=""

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
    --manual-template-out)
      MANUAL_TEMPLATE_OUT_PATH="${2:-}"
      if [ -z "$MANUAL_TEMPLATE_OUT_PATH" ]; then
        usage
        echo "ERROR: --manual-template-out requires a path" >&2
        exit 2
      fi
      shift 2
      ;;
    --skip-mini-build)
      SKIP_MINI_BUILD=1
      shift
      ;;
    --skip-wechat-devtools)
      SKIP_WECHAT_DEVTOOLS=1
      shift
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

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

run_step "mobile Vitest suite" \
  bash -lc "cd mobile && npm test"

run_step "mobile TypeScript check" \
  bash -lc "cd mobile && npx tsc --noEmit --module esnext"

run_step "mobile result surface guard" \
  bash -lc '
    node - <<'"'"'NODE'"'"'
const fs = require("fs");

function read(path) {
  return fs.readFileSync(path, "utf8");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const investigation = read("mobile/app/(tabs)/investigation.tsx");
const knowledge = read("mobile/app/(tabs)/knowledge.tsx");

assert(investigation.includes("latestResult"), "investigation tab must keep an in-page latestResult state");
assert(investigation.includes("resultCard"), "investigation tab must render an in-page resultCard");
assert(!investigation.includes("Alert.alert"), "investigation tab must not rely on Alert-only submission feedback");

assert(knowledge.includes("searchSummary"), "knowledge tab must keep an in-page searchSummary state");
assert(knowledge.includes("resultCard"), "knowledge tab must render an in-page resultCard");
assert(!knowledge.includes("Alert.alert"), "knowledge tab must not rely on Alert-only search feedback");

console.log("mobile result surface guard ok");
NODE
  '

run_step "mobile Expo config/dependency guard" \
  bash -lc '
    cd mobile
    node - <<'"'"'NODE'"'"'
const fs = require("fs");
const app = JSON.parse(fs.readFileSync("app.json", "utf8"));
const pkg = JSON.parse(fs.readFileSync("package.json", "utf8"));
const deps = { ...(pkg.dependencies || {}), ...(pkg.devDependencies || {}) };
const plugins = app.expo?.plugins || [];
const hasPlugin = (name) => plugins.some((plugin) => Array.isArray(plugin) ? plugin[0] === name : plugin === name);
for (const dependency of ["expo-notifications", "expo-device", "expo-font"]) {
  if (!deps[dependency]) {
    throw new Error(`Missing ${dependency}; mobile push/config plugin dependency drift`);
  }
}
if (!hasPlugin("expo-notifications")) {
  throw new Error("Missing expo-notifications plugin in mobile/app.json");
}
if (!hasPlugin("expo-font")) {
  throw new Error("Missing expo-font plugin in mobile/app.json");
}
NODE
    npx expo config --json --full >/tmp/anxin-mobile-expo-config.json
    test -s /tmp/anxin-mobile-expo-config.json
    npx expo install --check >/tmp/anxin-mobile-expo-install-check.log
    echo "mobile Expo config/dependency guard ok"
  '

run_step "mobile Expo doctor" \
  bash -lc "cd mobile && npx expo-doctor"

run_step "mobile npm audit security summary" \
  bash -lc '
    cd mobile
    npm audit --omit=dev --json >/tmp/anxin-mobile-npm-audit-prod.json || true
    python3 - <<'"'"'PY'"'"'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/anxin-mobile-npm-audit-prod.json").read_text(encoding="utf-8"))
vulnerabilities = payload.get("metadata", {}).get("vulnerabilities", {})
critical = int(vulnerabilities.get("critical") or 0)
high = int(vulnerabilities.get("high") or 0)
total = int(vulnerabilities.get("total") or 0)
names = set((payload.get("vulnerabilities") or {}).keys())
if critical:
    raise SystemExit("mobile npm audit has critical vulnerabilities")
if "@xmldom/xmldom" in names or "@expo/plist" in names:
    raise SystemExit("mobile npm audit still reports xmldom/plist vulnerability after override")
if total > 6 or high > 4:
    raise SystemExit(f"mobile npm audit regression: total={total}, high={high}")
print(f"mobile npm audit ok: total={total}, high={high}, critical={critical}")
PY
  '

run_step "mini-program TypeScript check" \
  bash -lc "cd mini-program && npx tsc --noEmit --skipLibCheck --noUnusedLocals false"

run_step "mini-program privacy boundary guard" \
  bash -lc "cd mini-program && npm run check-privacy-boundary"

run_step "mini-program navigation boundary guard" \
  bash -lc "cd mini-program && npm run check-navigation-boundary"

if [ "$SKIP_MINI_BUILD" -eq 0 ]; then
  run_step "mini-program WeChat build" \
    bash -lc "cd mini-program && npm run build:weapp"
else
  echo ">>> mini-program WeChat build skipped"
fi

run_step "mobile and mini fake fallback guard" \
  bash -lc '
    fail_if_found() {
      local pattern="$1"
      shift
      if rg -n "$pattern" "$@"; then
        echo "Forbidden fake fallback pattern found: $pattern" >&2
        exit 1
      fi
    }

    fail_if_found "fallbackMessages|fallbackTask|fallback-task|conversation_id: '\''fallback'\''" mobile/app mobile/src
    fail_if_found "mock_token|session_key" mini-program/src
    fail_if_found "假数据|体验模式|mock success|fake success" mobile/app mobile/src mini-program/src
    rg -n "wx.login|code2session" mini-program/src/pages/profile/index.tsx >/dev/null
    rg -n "暂无资讯|资讯加载失败" mini-program/src/pages/index/index.tsx >/dev/null
    echo "fake fallback guard ok"
  '

run_step "mobile and mini refresh auth guard" \
  bash -lc '
    rg -n "AuthExpiredError|RefreshUnavailableError" mobile/src/services/api.ts >/dev/null
    rg -n "MobilePrivacyNetworkBlockedError|X-Privacy-Mode" mobile/src/services/api.ts >/dev/null
    rg -n "fails closed before network I/O in local privacy mode" mobile/src/services/api.test.ts >/dev/null
    rg -n "MiniProgramAuthExpiredError|MiniProgramRefreshUnavailableError" mini-program/src/services/api.ts >/dev/null
    rg -n "MiniProgramPrivacyNetworkBlockedError|X-Privacy-Mode|assertMiniProgramDataNetworkAllowed" mini-program/src/services/api.ts >/dev/null
    rg -n "assertMiniProgramDataNetworkAllowed\\(currentMode\\)" mini-program/src/pages/profile/index.tsx >/dev/null
    rg -n "isMiniProgramPrivacyNetworkBlockedError" mini-program/src/pages/index/index.tsx mini-program/src/pages/chat/index.tsx >/dev/null
    if rg -n "catch \\{[[:space:]]*await clearAuth\\(\\)|catch \\(e\\) \\{[[:space:]]*Taro\\.removeStorageSync\\('\"'\"'token'\"'\"'\\)" mobile/src/services/api.ts mini-program/src/services/api.ts; then
      echo "Refresh-token transient failures must not clear auth state unconditionally" >&2
      exit 1
    fi
    echo "refresh auth and mobile/mini privacy network guards ok"
  '

run_step "mini-program design token guard" \
  bash -lc '
    raw_colors="$(
      rg -n "#[0-9a-fA-F]{3,8}|rgba\\(|linear-gradient" \
        mini-program/src --glob "*.scss" --glob "*.ts" \
        | rg -v "^mini-program/src/styles/design-tokens\\.(scss|ts):" || true
    )"
    if [ -n "$raw_colors" ]; then
      printf "%s\n" "$raw_colors"
      echo "Mini-program page/config colors must be referenced through src/styles/design-tokens.*" >&2
      exit 1
    fi
    echo "mini-program design token guard ok"
  '

find_wechat_devtools_cli() {
  if [ -n "${WECHAT_DEVTOOLS_CLI:-}" ] && [ -x "$WECHAT_DEVTOOLS_CLI" ]; then
    printf '%s' "$WECHAT_DEVTOOLS_CLI"
    return 0
  fi
  local candidates=(
    "/Applications/wechatwebdevtools.app/Contents/MacOS/cli"
    "/Applications/微信开发者工具.app/Contents/MacOS/cli"
    "$HOME/Applications/wechatwebdevtools.app/Contents/MacOS/cli"
    "$HOME/Applications/微信开发者工具.app/Contents/MacOS/cli"
  )
  local candidate
  for candidate in "${candidates[@]}"; do
    if [ -x "$candidate" ]; then
      printf '%s' "$candidate"
      return 0
    fi
  done
  return 1
}

WECHAT_DEVTOOLS_STATUS="passed"
WECHAT_DEVTOOLS_CLI_PATH=""
if [ "$SKIP_WECHAT_DEVTOOLS" -eq 0 ]; then
  WECHAT_DEVTOOLS_CLI_PATH="$(find_wechat_devtools_cli)" || {
    echo "WeChat DevTools CLI not found. Set WECHAT_DEVTOOLS_CLI or pass --skip-wechat-devtools for non-release local runs." >&2
    exit 1
  }
  run_step "mini-program WeChat DevTools CLI project smoke" \
    bash -lc '
      project_path="$(pwd)/mini-program"
      output="$("$0" auto --project "$project_path" --trust-project 2>&1)"
      printf "%s\n" "$output"
      if printf "%s\n" "$output" | rg "\\[error\\]|✖|project\\.config\\.json"; then
        echo "WeChat DevTools CLI could not trust/open the mini-program project" >&2
        exit 1
      fi
    ' "$WECHAT_DEVTOOLS_CLI_PATH"
else
  WECHAT_DEVTOOLS_STATUS="skipped"
  echo ">>> mini-program WeChat DevTools CLI project smoke skipped"
fi

echo
echo "Mobile and mini-program code-level smoke complete."
echo "Remaining release evidence still requires iOS, Android, WeChat DevTools or real-device runs, plus cross-device continuation."

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" "$SKIP_MINI_BUILD" "$WECHAT_DEVTOOLS_STATUS" "$WECHAT_DEVTOOLS_CLI_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
skip_mini_build = sys.argv[2] == "1"
wechat_devtools_status = sys.argv[3]
wechat_devtools_cli_path = sys.argv[4]
audit_path = Path("/tmp/anxin-mobile-npm-audit-prod.json")
audit_payload = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
audit_counts = audit_payload.get("metadata", {}).get("vulnerabilities", {})
audit_vulnerabilities = audit_payload.get("vulnerabilities") or {}
audit_status = "passed" if int(audit_counts.get("total") or 0) == 0 else "residual_known"
remaining_note = (
    "No production npm audit vulnerabilities remain after targeted Expo SDK 52 "
    "toolchain overrides. The tar override crosses Expo CLI's declared semver "
    "range, so expo-doctor and real device smoke should remain part of release "
    "verification."
    if audit_status == "passed"
    else (
        "Residual findings are in the Expo CLI/Metro build-tool chain; npm reports "
        "only a breaking --force remediation path, so release needs an official "
        "Expo SDK/CLI fix or a security exception before Go."
    )
)
mobile_npm_audit = {
    "status": audit_status,
    "command": "cd mobile && npm audit --omit=dev --json",
    "critical": int(audit_counts.get("critical") or 0),
    "high": int(audit_counts.get("high") or 0),
    "moderate": int(audit_counts.get("moderate") or 0),
    "total": int(audit_counts.get("total") or 0),
    "residual_vulnerabilities": sorted(audit_vulnerabilities.keys()),
    "remediated_by_override": [
        "@xmldom/xmldom@0.8.13",
        "@expo/cli -> tar@7.5.14",
        "@expo/metro-config -> postcss@8.5.14",
        "cacache -> tar@7.5.14",
    ],
    "remaining_note": remaining_note,
}
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "mobile_mini_code_smoke",
    "status": "passed",
    "release_evidence_complete": False,
    "checks": {
        "mobile_vitest": "passed",
        "mobile_typescript": "passed",
        "mobile_result_surface_guard": "passed",
        "mobile_expo_config_guard": "passed",
        "mobile_expo_doctor": "passed",
        "mini_program_typescript": "passed",
        "mini_program_privacy_boundary_guard": "passed",
        "mini_program_navigation_boundary_guard": "passed",
        "mini_program_wechat_build": "skipped" if skip_mini_build else "passed",
        "mini_program_wechat_devtools_cli": wechat_devtools_status,
        "mobile_refresh_auth_guard": "passed",
        "mini_program_refresh_auth_guard": "passed",
        "mobile_mini_privacy_network_guard": "passed",
        "fake_fallback_guard": "passed",
        "mini_program_design_token_guard": "passed",
    },
    "tooling": {
        "wechat_devtools_cli": wechat_devtools_cli_path,
    },
    "mobile_npm_audit": mobile_npm_audit,
    "completion_note": (
        "Code-level supporting evidence only. Keep mobile-device smoke evidence "
        "Status: pending until iOS, Android, WeChat DevTools or real-device runs "
        "and cross-device continuation are recorded."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote mobile/mini code-level smoke artifact: {out_path}")
PY
fi

if [ -n "$MANUAL_TEMPLATE_OUT_PATH" ]; then
  python3 - "$MANUAL_TEMPLATE_OUT_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
platforms = [
    {
        "platform": "ios",
        "device_model": "",
        "os_version": "",
        "build_hash": "",
        "backend_environment": "",
        "tester_role": "",
        "tested_at": "",
    },
    {
        "platform": "android",
        "device_model": "",
        "os_version": "",
        "build_hash": "",
        "backend_environment": "",
        "tester_role": "",
        "tested_at": "",
    },
    {
        "platform": "wechat_mini_program",
        "device_model": "",
        "os_version": "",
        "build_hash": "",
        "backend_environment": "",
        "tester_role": "",
        "tested_at": "",
    },
]
scenario_ids = [
    "login",
    "approval_detail",
    "message_detail",
    "task_detail",
    "chat_continuation",
    "settings_error_state",
    "mini_program_wx_login_code2session",
    "mini_program_no_fake_fallback",
    "cross_device_continuation",
    "explicit_error_semantics",
]
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "mobile_device_manual_template",
    "status": "template",
    "release_evidence_complete": False,
    "redaction_required": True,
    "platforms": platforms,
    "scenarios": [
        {
            "id": scenario_id,
            "status": "pending",
            "screenshot_refs": [],
            "log_refs": [],
            "notes": "",
        }
        for scenario_id in scenario_ids
    ],
    "cross_device_result": {
        "status": "pending",
        "web_session_ref": "",
        "desktop_session_ref": "",
        "mobile_session_ref": "",
        "notes": "",
    },
    "completion_note": (
        "Template only. Keep mobile-device smoke evidence Status: pending until "
        "real iOS, Android, WeChat DevTools or device runs fill device/build "
        "metadata plus redacted screenshot/log references."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote mobile/mini manual device evidence template: {out_path}")
PY
fi
