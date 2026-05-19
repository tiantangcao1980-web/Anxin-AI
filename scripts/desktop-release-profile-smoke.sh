#!/usr/bin/env bash
# Supporting packaged-profile SQLCipher/keyring smoke for an existing desktop release .app.
#
# This exercises the release .app binary against an isolated local profile:
# plaintext SQLite migration to SQLCipher, real OS keyring storage, encrypted
# reopen, and ordinary sqlite3 plaintext read rejection. It remains supporting
# evidence until the package is signed/notarized.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/desktop-release-profile-smoke.sh [options]

Options:
  --app path   Release .app path. Defaults to desktop/target/release/bundle/macos/安心智能助手.app
  --out path   Write a structured JSON artifact.
  -h, --help   Show this help.

Checks:
  - release .app binary exists
  - seeds a plaintext local DB in a temp profile
  - runs the release binary once to migrate plaintext SQLite to SQLCipher and create a keyring key
  - runs the release binary again without an explicit DB key to prove keyring reopen
  - verifies ordinary sqlite3 cannot read the encrypted DB as plaintext
  - runs release SQLCipher 100 push / 500 pull performance smoke
EOF
}

APP_PATH="desktop/target/release/bundle/macos/安心智能助手.app"
OUT_PATH=""

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
BINARY_PATH="$APP_PATH/Contents/MacOS/anxin-ai-desktop"

command -v sqlite3 >/dev/null
command -v node >/dev/null

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/anxin-release-profile-smoke.XXXXXX")"
DB_PATH="$TMP_DIR/anxin_local.db"
FIRST_JSON="$TMP_DIR/first.json"
SECOND_JSON="$TMP_DIR/second.json"
PERFORMANCE_JSON="$TMP_DIR/performance.json"
PLAIN_READ_ERR="$TMP_DIR/plaintext-read.err"
SERVICE="com.anxin.legal.desktop.release-profile-smoke.$(date +%s).$$"
USER="sqlcipher-db-key-v1"

cleanup() {
  if [ -x "$BINARY_PATH" ]; then
    env -u ANXIN_DESKTOP_SQLCIPHER_KEY_HEX \
      ANXIN_DESKTOP_KEYRING_SERVICE="$SERVICE" \
      ANXIN_DESKTOP_KEYRING_USER="$USER" \
      "$BINARY_PATH" --secure-db-delete-smoke-key >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

run_step "release app binary exists" test -x "$BINARY_PATH"

echo ">>> seed plaintext packaged profile DB"
sqlite3 "$DB_PATH" < desktop/migrations/001_offline_queue.sql
sqlite3 "$DB_PATH" \
  "INSERT INTO local_messages (id, conversation_id, content, role) VALUES ('pre-migration-release-plain', 'release-profile-smoke', 'plaintext before release SQLCipher migration', 'user');"

run_release_profile_smoke() {
  env -u ANXIN_DESKTOP_SQLCIPHER_KEY_HEX \
    ANXIN_DESKTOP_DB_PATH="$DB_PATH" \
    ANXIN_DESKTOP_KEYRING_SERVICE="$SERVICE" \
    ANXIN_DESKTOP_KEYRING_USER="$USER" \
    "$BINARY_PATH" --secure-db-installed-profile-smoke
}

echo ">>> first release launch plaintext-to-SQLCipher migration"
run_release_profile_smoke > "$FIRST_JSON"

echo ">>> second release launch keyring reopen"
run_release_profile_smoke > "$SECOND_JSON"

run_release_performance_smoke() {
  env -u ANXIN_DESKTOP_SQLCIPHER_KEY_HEX \
    ANXIN_DESKTOP_DB_PATH="$DB_PATH" \
    ANXIN_DESKTOP_KEYRING_SERVICE="$SERVICE" \
    ANXIN_DESKTOP_KEYRING_USER="$USER" \
    "$BINARY_PATH" --secure-db-performance-smoke
}

echo ">>> release SQLCipher 100/500 performance smoke"
run_release_performance_smoke > "$PERFORMANCE_JSON"

echo ">>> ordinary sqlite3 plaintext read rejection"
if sqlite3 "$DB_PATH" "SELECT content FROM local_messages WHERE id='installed-profile-smoke';" > /dev/null 2> "$PLAIN_READ_ERR"; then
  echo "ERROR: ordinary sqlite3 read unexpectedly succeeded" >&2
  exit 1
fi

run_step "release packaged-profile smoke report validation" \
  node - "$FIRST_JSON" "$SECOND_JSON" "$PERFORMANCE_JSON" "$OUT_PATH" "$APP_PATH" "$BINARY_PATH" <<'NODE'
const fs = require("fs");
const path = require("path");

const first = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const second = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const performance = JSON.parse(fs.readFileSync(process.argv[4], "utf8"));
const outPath = process.argv[5];
const appPath = process.argv[6];
const binaryPath = process.argv[7];

function requireField(report, field, expected) {
  if (report[field] !== expected) {
    throw new Error(`${field} expected ${expected}, got ${report[field]}`);
  }
}

for (const report of [first, second]) {
  requireField(report, "keyringRoundTrip", true);
  requireField(report, "encryptedReopen", true);
  requireField(report, "plaintextBackupPresent", true);
  requireField(report, "plaintextOpenBlocked", true);
  if (report.sentinelContent !== "installed profile SQLCipher keyring reopen smoke") {
    throw new Error("unexpected sentinel content");
  }
}
requireField(performance, "status", "passed");
requireField(performance, "keyringRoundTrip", true);
requireField(performance, "encryptedReopen", true);
if (typeof performance.push100RowsP95Ms !== "number" || typeof performance.pushThresholdMs !== "number") {
  throw new Error("performance push P95/threshold must be numeric");
}
if (typeof performance.pull500RowsP95Ms !== "number" || typeof performance.pullThresholdMs !== "number") {
  throw new Error("performance pull P95/threshold must be numeric");
}
if (performance.push100RowsP95Ms >= performance.pushThresholdMs) {
  throw new Error("release SQLCipher push P95 exceeded threshold");
}
if (performance.pull500RowsP95Ms >= performance.pullThresholdMs) {
  throw new Error("release SQLCipher pull P95 exceeded threshold");
}

const combined = {
  generated_at: new Date().toISOString(),
  mode: "desktop_release_packaged_profile_smoke",
  status: "passed",
  release_evidence_complete: false,
  signed_or_notarized: false,
  checks: {
    release_app_exists: "passed",
    release_binary_exists: "passed",
    plaintext_profile_seeded: "passed",
    first_launch_plaintext_to_sqlcipher_migration: "passed",
    second_launch_keyring_reopen: "passed",
    release_sqlcipher_performance: "passed",
    ordinary_sqlite_plaintext_read_blocked: "passed",
  },
  artifacts: {
    release_app: appPath,
    release_binary: binaryPath,
  },
  firstLaunch: first,
  secondLaunch: second,
  performance,
  completion_note:
    "Unsigned release packaged-profile/performance supporting evidence only. Keep desktop runtime evidence Status: pending until the package is signed/notarized and signed packaged-profile, signed packaged runtime performance, and cross-device evidence are attached.",
};

if (outPath) {
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(combined, null, 2) + "\n");
}

console.log(
  `release packaged-profile smoke ok: migrated=${first.plaintextBackupPresent}, keyring=${second.keyringRoundTrip}, encryptedReopen=${second.encryptedReopen}, pushP95=${performance.push100RowsP95Ms}ms, pullP95=${performance.pull500RowsP95Ms}ms`
);
NODE

echo
echo "Desktop unsigned release packaged-profile/performance smoke complete."
if [ -n "$OUT_PATH" ]; then
  echo "Wrote report: $OUT_PATH"
fi
