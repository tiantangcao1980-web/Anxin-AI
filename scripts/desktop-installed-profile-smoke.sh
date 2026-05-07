#!/usr/bin/env bash
# Installed-profile SQLCipher/keyring smoke for the desktop app.
#
# This uses an isolated keyring service/user so it exercises the real platform
# key store without touching the production desktop DB key.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/desktop-installed-profile-smoke.sh [--out path]

Checks:
  - builds the desktop debug binary
  - seeds a plaintext local DB in a temp profile
  - runs the binary once to migrate plaintext SQLite to SQLCipher and create a keyring key
  - runs the binary again without an explicit DB key to prove keyring reopen
  - verifies ordinary sqlite3 cannot read the encrypted DB as plaintext
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

command -v sqlite3 >/dev/null
command -v node >/dev/null

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/anxin-desktop-installed-profile.XXXXXX")"
db_path="$tmp_dir/anxin_local.db"
first_json="$tmp_dir/first.json"
second_json="$tmp_dir/second.json"
plain_read_err="$tmp_dir/plaintext-read.err"
service="com.anxin.legal.desktop.installed-smoke.$(date +%s).$$"
user="sqlcipher-db-key-v1"
bin="$PROJECT_ROOT/desktop/target/debug/anxin-legal-desktop"

cleanup() {
  if [ -x "$bin" ]; then
    env -u ANXIN_DESKTOP_SQLCIPHER_KEY_HEX \
      ANXIN_DESKTOP_KEYRING_SERVICE="$service" \
      ANXIN_DESKTOP_KEYRING_USER="$user" \
      "$bin" --secure-db-delete-smoke-key >/dev/null 2>&1 || true
  fi
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

run_step "desktop debug binary build" \
  bash -lc "cd desktop && cargo build"

echo ">>> seed plaintext profile DB"
sqlite3 "$db_path" < desktop/migrations/001_offline_queue.sql
sqlite3 "$db_path" \
  "INSERT INTO local_messages (id, conversation_id, content, role) VALUES ('pre-migration-plain', 'installed-profile-smoke', 'plaintext before SQLCipher migration', 'user');"

run_installed_profile_smoke() {
  env -u ANXIN_DESKTOP_SQLCIPHER_KEY_HEX \
    ANXIN_DESKTOP_DB_PATH="$db_path" \
    ANXIN_DESKTOP_KEYRING_SERVICE="$service" \
    ANXIN_DESKTOP_KEYRING_USER="$user" \
    "$bin" --secure-db-installed-profile-smoke
}

echo ">>> first launch plaintext-to-SQLCipher migration"
run_installed_profile_smoke > "$first_json"

echo ">>> second launch keyring reopen"
run_installed_profile_smoke > "$second_json"

echo ">>> ordinary sqlite3 plaintext read rejection"
if sqlite3 "$db_path" "SELECT content FROM local_messages WHERE id='installed-profile-smoke';" > /dev/null 2> "$plain_read_err"; then
  echo "ERROR: ordinary sqlite3 read unexpectedly succeeded" >&2
  exit 1
fi

run_step "installed-profile smoke report validation" \
  node - "$first_json" "$second_json" "$OUT_PATH" <<'NODE'
const fs = require("fs");

const first = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const second = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const outPath = process.argv[4];

function requireField(report, field, expected) {
  if (report[field] !== expected) {
    throw new Error(`${field} expected ${expected}, got ${report[field]}`);
  }
}

for (const report of [first, second]) {
  requireField(report, "keyringRoundTrip", true);
  requireField(report, "encryptedReopen", true);
  requireField(report, "plaintextOpenBlocked", true);
  if (report.sentinelContent !== "installed profile SQLCipher keyring reopen smoke") {
    throw new Error("unexpected sentinel content");
  }
}
requireField(first, "plaintextBackupPresent", true);
requireField(second, "plaintextBackupPresent", true);

const combined = {
  generated_at: new Date().toISOString(),
  mode: "desktop_installed_profile_smoke",
  status: "passed",
  release_evidence_complete: false,
  firstLaunch: first,
  secondLaunch: second,
  completion_note:
    "Supporting evidence only. Keep desktop runtime evidence pending until a signed/notarized package has signed packaged-profile migration and signed packaged runtime evidence.",
};
if (outPath) {
  fs.mkdirSync(require("path").dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(combined, null, 2) + "\n");
}

console.log(
  `installed-profile smoke ok: migrated=${first.plaintextBackupPresent}, keyring=${second.keyringRoundTrip}, encryptedReopen=${second.encryptedReopen}`
);
NODE

echo
echo "Desktop installed-profile SQLCipher/keyring smoke complete."
if [ -n "$OUT_PATH" ]; then
  echo "Wrote report: $OUT_PATH"
fi
