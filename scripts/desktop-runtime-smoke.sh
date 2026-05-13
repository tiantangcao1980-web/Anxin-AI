#!/usr/bin/env bash
# Code-level desktop sync smoke checks.
#
# This script is a repeatable preflight for the desktop runtime evidence. It
# proves the code-level SQLCipher/keyring contract plus a debug app-bundle
# webview UI load handshake when --with-app-bundle is set, but it does not prove
# signed/notarized packaged UI interaction, installed-profile behavior, or cross-device continuation.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/desktop-runtime-smoke.sh [options]

Options:
  --skip-tauri-build   Skip "cargo tauri build --debug --no-bundle --ci".
  --with-app-bundle    Build a debug macOS .app bundle with "--bundles app --no-sign"
                       and run the bundle binary self-test, runtime startup smoke,
                       and webview UI load handshake smoke.
  --out path           Write a code-level desktop smoke JSON artifact after all checks pass.
  --ui-log-out path    Copy the debug app-bundle UI smoke log to this path.
  -h, --help           Show this help.

Checks:
  - frontend sync Vitest slice
  - desktop cargo test
  - desktop cargo check
  - desktop SQLite migration SQL smoke
  - desktop SQLite 100/500 sync performance smoke
  - desktop Tauri debug build unless skipped
  - built desktop binary or app bundle binary --self-test unless Tauri build is skipped
  - app bundle runtime startup and UI load handshake smoke when --with-app-bundle is set
EOF
}

SKIP_TAURI_BUILD=0
WITH_APP_BUNDLE=0
OUT_PATH=""
UI_LOG_OUT_PATH=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --skip-tauri-build)
      SKIP_TAURI_BUILD=1
      shift
      ;;
    --with-app-bundle)
      WITH_APP_BUNDLE=1
      shift
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
UI_LOG_OUT_PATH="$(resolve_artifact_path "$UI_LOG_OUT_PATH")"
export DESKTOP_RUNTIME_UI_LOG_OUT="$UI_LOG_OUT_PATH"

TMP_DESKTOP_RUNTIME_DIR="$(mktemp -d "${TMPDIR:-/tmp}/anxin-desktop-runtime-artifacts.XXXXXX")"
trap 'rm -rf "$TMP_DESKTOP_RUNTIME_DIR"' EXIT
DESKTOP_RUNTIME_PERF_REPORT="$TMP_DESKTOP_RUNTIME_DIR/sqlite-performance.json"
export DESKTOP_RUNTIME_PERF_REPORT

run_step() {
  local label="$1"
  shift
  echo ">>> ${label}"
  "$@"
}

latest_desktop_crash_report() {
  ls -t "${HOME}/Library/Logs/DiagnosticReports"/anxin-legal-desktop-*.ips 2>/dev/null | head -n 1 || true
}

persist_failure_log() {
  local source_log="$1"
  local destination_path="$2"
  if [ -z "$destination_path" ]; then
    return 0
  fi
  mkdir -p "$(dirname "$destination_path")"
  cp "$source_log" "$destination_path"
  echo "desktop smoke failure log copied to: $destination_path"
}

export -f latest_desktop_crash_report persist_failure_log

desktop_sqlite_performance_smoke() {
  command -v sqlite3 >/dev/null
  command -v node >/dev/null
  local tmp_dir db_path
  tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/anxin-desktop-sqlite-perf.XXXXXX")"
  trap "rm -rf \"$tmp_dir\"" RETURN
  db_path="$tmp_dir/anxin_local_perf.db"

  sqlite3 "$db_path" < desktop/migrations/001_offline_queue.sql

  node - "$db_path" <<'NODE'
const { execFileSync } = require("child_process");
const fs = require("fs");

const dbPath = process.argv[2];
const perfReportPath = process.env.DESKTOP_RUNTIME_PERF_REPORT || "";

function runSql(sql) {
  execFileSync("sqlite3", [dbPath], {
    input: sql,
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
}

function scalar(sql) {
  return execFileSync("sqlite3", [dbPath, sql], {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  }).trim();
}

function quote(value) {
  return "'" + String(value).replace(/'/g, "''") + "'";
}

function timed(fn) {
  const started = process.hrtime.bigint();
  fn();
  const elapsed = process.hrtime.bigint() - started;
  return Number(elapsed) / 1_000_000;
}

function percentile(values, pct) {
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.ceil((pct / 100) * sorted.length) - 1);
  return sorted[index];
}

function pushSql(round) {
  const rows = [];
  for (let index = 0; index < 100; index += 1) {
    const entityId = "perf-push-" + round + "-" + index;
    const payload = JSON.stringify({ index, title: "Desktop push perf " + index });
    rows.push(
      "INSERT INTO sync_log (entity_type, entity_id, action, data_json, status, retry_count, needs_human) VALUES (" +
        quote("document") + "," +
        quote(entityId) + "," +
        quote("push") + "," +
        quote(payload) + "," +
        quote("pending") + ",0,0);"
    );
  }
  return "BEGIN;\nDELETE FROM sync_log WHERE entity_id LIKE 'perf-push-%';\n" + rows.join("\n") + "\nCOMMIT;\n";
}

function pullSql(round) {
  const rows = [];
  for (let index = 0; index < 500; index += 1) {
    const id = "perf-pull-" + round + "-" + index;
    rows.push(
      "INSERT OR REPLACE INTO local_documents (id, title, content, file_size, mime_type, category, synced, sync_version) VALUES (" +
        quote(id) + "," +
        quote("Pulled document " + index) + "," +
        quote("Local pull performance content " + index) + ",128," +
        quote("text/plain") + "," +
        quote("perf") + ",1," + round + ");"
    );
  }
  return "BEGIN;\nDELETE FROM local_documents WHERE id LIKE 'perf-pull-%';\n" + rows.join("\n") + "\nCOMMIT;\n";
}

const pushSamples = [];
const pullSamples = [];
for (let round = 1; round <= 5; round += 1) {
  pushSamples.push(timed(() => runSql(pushSql(round))));
  const pushCount = Number(scalar("SELECT COUNT(*) FROM sync_log WHERE entity_id LIKE 'perf-push-" + round + "-%';"));
  if (pushCount !== 100) {
    throw new Error("expected 100 push rows, got " + pushCount);
  }

  pullSamples.push(timed(() => runSql(pullSql(round))));
  const pullCount = Number(scalar("SELECT COUNT(*) FROM local_documents WHERE id LIKE 'perf-pull-" + round + "-%';"));
  if (pullCount !== 500) {
    throw new Error("expected 500 pull rows, got " + pullCount);
  }
}

const pushP95 = percentile(pushSamples, 95);
const pullP95 = percentile(pullSamples, 95);
if (pushP95 >= 2000) {
  throw new Error("100-row push SQLite P95 exceeded 2s: " + pushP95.toFixed(1) + "ms");
}
if (pullP95 >= 3000) {
  throw new Error("500-row pull SQLite P95 exceeded 3s: " + pullP95.toFixed(1) + "ms");
}

console.log(
  "sqlite perf ok: 100 push rows P95=" + pushP95.toFixed(1) +
    "ms, 500 pull rows P95=" + pullP95.toFixed(1) + "ms"
);
if (perfReportPath) {
  fs.writeFileSync(
    perfReportPath,
    JSON.stringify(
      {
        status: "passed",
        push_100_rows_p95_ms: Number(pushP95.toFixed(1)),
        pull_500_rows_p95_ms: Number(pullP95.toFixed(1)),
        push_threshold_ms: 2000,
        pull_threshold_ms: 3000,
      },
      null,
      2,
    ) + "\n",
    "utf8",
  );
}
NODE
  trap - RETURN
  rm -rf "$tmp_dir"
}

run_step "frontend desktop sync Vitest slice" \
  bash -lc "cd frontend && npm run test -- api-adapter.sync.test.ts sync-conflict-utils.test.ts"

run_step "desktop cargo test" \
  bash -lc "cd desktop && cargo test"

run_step "desktop cargo check" \
  bash -lc "cd desktop && cargo check"

run_step "desktop SQLite migration SQL smoke" \
  bash -lc '
    command -v sqlite3 >/dev/null
    tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/anxin-desktop-sqlite-smoke.XXXXXX")"
    trap "rm -rf \"$tmp_dir\"" EXIT
    db_path="$tmp_dir/anxin_local.db"

    sqlite3 "$db_path" < desktop/migrations/001_offline_queue.sql

    for table in offline_tasks app_settings sync_log local_messages local_documents local_cases local_contracts local_artifacts; do
      sqlite3 "$db_path" "SELECT name FROM sqlite_master WHERE type='\''table'\'' AND name='\''${table}'\'';" | grep -qx "$table"
    done

    sqlite3 "$db_path" "PRAGMA table_info(sync_log);" | grep -q "|next_retry_at|DATETIME|"
    sqlite3 "$db_path" "PRAGMA table_info(sync_log);" | grep -q "|needs_human|BOOLEAN|"
    sqlite3 "$db_path" "INSERT INTO sync_log (entity_type, entity_id, action, status, retry_count, needs_human) VALUES ('\''document'\'', '\''smoke-doc'\'', '\''push'\'', '\''failed'\'', 1, 1);"
    result="$(sqlite3 "$db_path" "SELECT status || '\''|'\'' || retry_count || '\''|'\'' || needs_human FROM sync_log WHERE entity_id='\''smoke-doc'\'';")"
    [ "$result" = "failed|1|1" ]
    [ "$(sqlite3 "$db_path" "PRAGMA integrity_check;")" = "ok" ]

    legacy_db_path="$tmp_dir/anxin_legacy_local.db"
    sqlite3 "$legacy_db_path" "
      CREATE TABLE sync_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        action TEXT NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT '\''pending'\''
      );
      INSERT INTO sync_log (entity_type, entity_id, action, status)
      VALUES ('\''document'\'', '\''legacy-doc'\'', '\''push'\'', '\''pending'\'');
    "
    sqlite3 "$legacy_db_path" < desktop/migrations/001_offline_queue.sql
    legacy_result="$(sqlite3 "$legacy_db_path" "SELECT entity_type || '\''|'\'' || entity_id || '\''|'\'' || status FROM sync_log WHERE entity_id='\''legacy-doc'\'';")"
    [ "$legacy_result" = "document|legacy-doc|pending" ]
    for table in offline_tasks app_settings sync_log local_messages local_documents local_cases local_contracts local_artifacts; do
      sqlite3 "$legacy_db_path" "SELECT name FROM sqlite_master WHERE type='\''table'\'' AND name='\''${table}'\'';" | grep -qx "$table"
    done
    for sql in \
      "ALTER TABLE sync_log ADD COLUMN data_json TEXT" \
      "ALTER TABLE sync_log ADD COLUMN error_message TEXT" \
      "ALTER TABLE sync_log ADD COLUMN retry_count INTEGER DEFAULT 0" \
      "ALTER TABLE sync_log ADD COLUMN next_retry_at DATETIME" \
      "ALTER TABLE sync_log ADD COLUMN needs_human BOOLEAN DEFAULT 0" \
      "CREATE INDEX IF NOT EXISTS idx_sync_retry_due ON sync_log(status, next_retry_at)"; do
      sqlite3 "$legacy_db_path" "$sql" 2>/dev/null || true
    done
    sqlite3 "$legacy_db_path" "PRAGMA table_info(sync_log);" | grep -q "|next_retry_at|DATETIME|"
    sqlite3 "$legacy_db_path" "PRAGMA table_info(sync_log);" | grep -q "|needs_human|BOOLEAN|"
    [ "$(sqlite3 "$legacy_db_path" "PRAGMA integrity_check;")" = "ok" ]

    echo "sqlite smoke ok: fresh migration applied, legacy sync_log startup path preserved, frontend repair SQL fills retry schema"
  '

run_step "desktop SQLite 100/500 sync performance smoke" desktop_sqlite_performance_smoke

if [ "$SKIP_TAURI_BUILD" -eq 0 ]; then
  if [ "$WITH_APP_BUNDLE" -eq 1 ]; then
    run_step "desktop Tauri debug macOS app bundle build" \
      bash -lc "cd desktop && cargo tauri build --debug --ci --bundles app --no-sign"

    run_step "desktop app bundle binary self-test" \
      bash -lc '
        cd desktop
        bundle_bin="target/debug/bundle/macos/安心智能助手.app/Contents/MacOS/anxin-legal-desktop"
        [ -x "$bundle_bin" ]
        "$bundle_bin" --self-test | node -e '\''
          let input = "";
          process.stdin.on("data", (chunk) => { input += chunk; });
          process.stdin.on("end", () => {
            const report = JSON.parse(input);
            const requiredTables = [
              "offline_tasks",
              "app_settings",
              "sync_log",
              "local_messages",
              "local_documents",
              "local_cases",
              "local_contracts",
              "local_artifacts",
            ];
            const missing = requiredTables.filter((table) => !report.required_tables_present.includes(table));
            if (report.app !== "anxin-legal-desktop") throw new Error("unexpected app id");
            if (report.local_db_url !== "sqlcipher:anxin_local.db") throw new Error("unexpected local db url");
            if (report.migration_count !== 1) throw new Error("unexpected migration count");
            if (!report.sync_retry_schema_present) throw new Error("sync retry schema missing");
            if (missing.length) throw new Error(`missing tables: ${missing.join(", ")}`);
            if (!report.sqlite_security.encrypted) throw new Error("SQLite security self-test must report encrypted=true");
            if (!report.sqlite_security.keyring_backed) throw new Error("SQLite security self-test must report keyring_backed=true");
            if (report.sqlite_security.release_blocking) throw new Error("SQLite security gate should not remain release-blocking after SQLCipher/keyring lands");
            console.log(`app bundle self-test ok: ${report.required_tables_present.length} tables, sqlite encrypted=${report.sqlite_security.encrypted}`);
          });
        '\''
      '

    run_step "desktop app bundle runtime startup smoke" \
      bash -lc '
        cd desktop
        bundle_bin="target/debug/bundle/macos/安心智能助手.app/Contents/MacOS/anxin-legal-desktop"
        [ -x "$bundle_bin" ]
        runtime_log="$(mktemp "${TMPDIR:-/tmp}/anxin-desktop-runtime-smoke.XXXXXX")"
        "$bundle_bin" --runtime-smoke >"$runtime_log" 2>&1 &
        app_pid=$!
        (
          sleep 15
          if kill -0 "$app_pid" 2>/dev/null; then
            echo "desktop runtime smoke timed out; terminating pid=$app_pid" >>"$runtime_log"
            kill "$app_pid" 2>/dev/null || true
          fi
        ) &
        watchdog_pid=$!
        set +e
        wait "$app_pid"
        app_status=$?
        set -e
        kill "$watchdog_pid" 2>/dev/null || true
        wait "$watchdog_pid" 2>/dev/null || true
        if [ "$app_status" -ne 0 ]; then
          persist_failure_log "$runtime_log" "${DESKTOP_RUNTIME_UI_LOG_OUT:-}"
          crash_report="$(latest_desktop_crash_report)"
          if [ -n "$crash_report" ]; then
            echo "desktop runtime smoke crash report: $crash_report"
          fi
          cat "$runtime_log"
          rm -f "$runtime_log"
          exit "$app_status"
        fi
        grep -q "desktop runtime smoke starting" "$runtime_log"
        grep -q "desktop runtime smoke exiting" "$runtime_log"
        cat "$runtime_log"
        rm -f "$runtime_log"
      '

    run_step "desktop app bundle UI load smoke" \
      bash -lc '
        cd desktop
        bundle_bin="target/debug/bundle/macos/安心智能助手.app/Contents/MacOS/anxin-legal-desktop"
        [ -x "$bundle_bin" ]
        ui_log="$(mktemp "${TMPDIR:-/tmp}/anxin-desktop-ui-smoke.XXXXXX")"
        "$bundle_bin" --runtime-ui-smoke >"$ui_log" 2>&1 &
        app_pid=$!
        (
          sleep 20
          if kill -0 "$app_pid" 2>/dev/null; then
            echo "desktop runtime UI smoke shell watchdog timed out; terminating pid=$app_pid" >>"$ui_log"
            kill "$app_pid" 2>/dev/null || true
          fi
        ) &
        watchdog_pid=$!
        set +e
        wait "$app_pid"
        app_status=$?
        set -e
        kill "$watchdog_pid" 2>/dev/null || true
        wait "$watchdog_pid" 2>/dev/null || true
        if [ "$app_status" -ne 0 ]; then
          persist_failure_log "$ui_log" "${DESKTOP_RUNTIME_UI_LOG_OUT:-}"
          crash_report="$(latest_desktop_crash_report)"
          if [ -n "$crash_report" ]; then
            echo "desktop runtime UI smoke crash report: $crash_report"
          fi
          cat "$ui_log"
          rm -f "$ui_log"
          exit "$app_status"
        fi
        grep -q "desktop runtime UI smoke starting" "$ui_log"
        grep -q "desktop runtime UI smoke response:" "$ui_log"
        grep -q "desktop runtime UI smoke exiting: frontend response received" "$ui_log"
        node - "$ui_log" <<'\''NODE'\''
const fs = require("fs");
const logPath = process.argv[2];
const log = fs.readFileSync(logPath, "utf8");
const line = log.split(/\r?\n/).find((entry) => entry.startsWith("desktop runtime UI smoke response: "));
if (!line) throw new Error("UI smoke response line missing");
const payload = JSON.parse(line.replace("desktop runtime UI smoke response: ", ""));
const hasRenderedRoot =
  payload.hasRoot &&
  payload.rootChildCount >= 1 &&
  String(payload.platform || "").startsWith("tauri-") &&
  payload.title;
const hasPageLoad =
  payload.pageLoadFinished === true &&
  payload.webviewLabel === "main" &&
  payload.windowLabel === "main" &&
  Boolean(payload.url);
if (!hasRenderedRoot && !hasPageLoad) {
  throw new Error("neither rendered React root nor Tauri page-load payload was present");
}
        if (hasRenderedRoot) {
  console.log(
    `desktop UI smoke ok: rootChildren=${payload.rootChildCount}, platform=${payload.platform}, title=${payload.title}`
  );
} else {
  console.log(
    `desktop UI smoke ok: pageLoadFinished=${payload.pageLoadFinished}, webview=${payload.webviewLabel}, url=${payload.url}`
  );
}
NODE
        cat "$ui_log"
        if [ -n "${DESKTOP_RUNTIME_UI_LOG_OUT:-}" ]; then
          mkdir -p "$(dirname "$DESKTOP_RUNTIME_UI_LOG_OUT")"
          cp "$ui_log" "$DESKTOP_RUNTIME_UI_LOG_OUT"
          echo "desktop UI smoke log copied to: $DESKTOP_RUNTIME_UI_LOG_OUT"
        fi
        rm -f "$ui_log"
      '
  else
    run_step "desktop Tauri debug no-bundle build" \
      bash -lc "cd desktop && cargo tauri build --debug --no-bundle --ci"

    run_step "desktop debug binary self-test" \
      bash -lc '
        cd desktop
        ./target/debug/anxin-legal-desktop --self-test | node -e '\''
        let input = "";
        process.stdin.on("data", (chunk) => { input += chunk; });
        process.stdin.on("end", () => {
          const report = JSON.parse(input);
          const requiredTables = [
            "offline_tasks",
            "app_settings",
            "sync_log",
            "local_messages",
            "local_documents",
            "local_cases",
            "local_contracts",
            "local_artifacts",
          ];
          const missing = requiredTables.filter((table) => !report.required_tables_present.includes(table));
          if (report.app !== "anxin-legal-desktop") throw new Error("unexpected app id");
          if (report.local_db_url !== "sqlcipher:anxin_local.db") throw new Error("unexpected local db url");
          if (report.migration_count !== 1) throw new Error("unexpected migration count");
          if (!report.sync_retry_schema_present) throw new Error("sync retry schema missing");
          if (missing.length) throw new Error(`missing tables: ${missing.join(", ")}`);
          if (!report.sqlite_security.encrypted) throw new Error("SQLite security self-test must report encrypted=true");
          if (!report.sqlite_security.keyring_backed) throw new Error("SQLite security self-test must report keyring_backed=true");
          if (report.sqlite_security.release_blocking) throw new Error("SQLite security gate should not remain release-blocking after SQLCipher/keyring lands");
          console.log(`self-test ok: ${report.required_tables_present.length} tables, sqlite encrypted=${report.sqlite_security.encrypted}`);
        });
      '\''
      '
  fi
else
  echo ">>> desktop Tauri debug build skipped"
  echo ">>> desktop binary self-test skipped"
fi

echo
echo "Desktop code-level smoke complete."
echo "Remaining release evidence still requires signed/notarized packaged UI interaction, signed packaged-profile migration evidence, signed packaged-runtime performance, and cross-device continuation."

if [ -n "$OUT_PATH" ]; then
  python3 - "$OUT_PATH" "$SKIP_TAURI_BUILD" "$WITH_APP_BUNDLE" "$DESKTOP_RUNTIME_PERF_REPORT" "$UI_LOG_OUT_PATH" <<'PY'
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

out_path = Path(sys.argv[1])
skip_tauri_build = sys.argv[2] == "1"
with_app_bundle = sys.argv[3] == "1"
perf_report_path = Path(sys.argv[4])
ui_log_out = sys.argv[5]
perf_report = {}
if perf_report_path.exists():
    perf_report = json.loads(perf_report_path.read_text(encoding="utf-8"))

bundle_path = "desktop/target/debug/bundle/macos/安心智能助手.app"
report = {
    "generated_at": datetime.now(UTC).isoformat(),
    "mode": "desktop_runtime_code_smoke",
    "status": "passed",
    "release_evidence_complete": False,
    "checks": {
        "frontend_desktop_sync_vitest": "passed",
        "desktop_cargo_test": "passed",
        "desktop_cargo_check": "passed",
        "sqlite_migration_sql_smoke": "passed",
        "sqlite_sync_performance_smoke": perf_report or "passed",
        "tauri_debug_build": "skipped" if skip_tauri_build else "passed",
        "debug_binary_or_bundle_self_test": "skipped" if skip_tauri_build else "passed",
        "debug_app_bundle_runtime_startup": "passed" if with_app_bundle else "not_requested",
        "debug_app_bundle_ui_load": "passed" if with_app_bundle else "not_requested",
    },
    "artifacts": {
        "debug_app_bundle": bundle_path if with_app_bundle and not skip_tauri_build else "",
        "ui_log": ui_log_out,
    },
    "completion_note": (
        "Code-level supporting evidence only. Keep desktop runtime evidence "
        "Status: pending until a signed/notarized package has packaged UI interaction, "
        "signed packaged-profile migration, signed packaged runtime performance, and cross-device continuation evidence."
    ),
}
out_path.parent.mkdir(parents=True, exist_ok=True)
out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote desktop code-level smoke artifact: {out_path}")
PY
fi
