#!/usr/bin/env bash
# Collect a static-quality baseline for release readiness.
#
# The script records command exit codes and issue counts. It does not change
# source files and does not mark the release evidence complete by itself.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/static-quality-baseline.sh [options]

Options:
  --out <path>        Write a Markdown report to the given path.
  --quick            Skip backend ruff/mypy and full-repo secret/mock scans.
  -h, --help         Show this help.

Examples:
  bash scripts/static-quality-baseline.sh
  bash scripts/static-quality-baseline.sh --out /tmp/static-quality-baseline.md
EOF
}

OUT_PATH=""
QUICK=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --out)
      [ "$#" -ge 2 ] || { echo "ERROR: --out requires a path" >&2; exit 2; }
      OUT_PATH="$2"
      shift 2
      ;;
    --quick)
      QUICK=1
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

TMP_DIR="$(mktemp -d /tmp/anxin-static-quality.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

declare -a ROWS=()
declare -a NOTES=()

run_check() {
  local key="$1"
  local label="$2"
  shift 2

  local stdout_file stderr_file merged_file rc issue_count
  stdout_file="$TMP_DIR/${key}.stdout"
  stderr_file="$TMP_DIR/${key}.stderr"
  merged_file="$TMP_DIR/${key}.merged"

  echo ">>> $label"
  set +e
  "$@" >"$stdout_file" 2>"$stderr_file"
  rc=$?
  set -e
  cat "$stdout_file" "$stderr_file" >"$merged_file"

  issue_count="$(count_issues "$key" "$merged_file")"
  if [[ "$key" == "secret_scan" || "$key" == "mock_scan" ]]; then
    if [ "$issue_count" -eq 0 ]; then
      rc=0
    else
      rc=1
    fi
  fi
  ROWS+=("| ${label} | \`${rc}\` | ${issue_count} | ${key} |")
}

count_issues() {
  local key="$1"
  local file="$2"

  case "$key" in
    ruff)
      awk '/^[^:]+:[0-9]+:[0-9]+: [A-Z]+[0-9]+ / { n++ } END { print n + 0 }' "$file"
      ;;
    mypy)
      awk '/^[^:]+:[0-9]+(:[0-9]+)?: error: / { n++ } END { print n + 0 }' "$file"
      ;;
    secret_scan|mock_scan)
      awk 'NF { n++ } END { print n + 0 }' "$file"
      ;;
    release_evidence_secret_scan)
      if grep -q '^Release evidence secret scan: PASS$' "$file"; then
        echo "0"
      else
        awk 'NF && $0 !~ /^Release evidence secret scan: FAIL$/ { n++ } END { print n + 0 }' "$file"
      fi
      ;;
    *)
      if grep -q . "$file"; then
        awk 'NF { n++ } END { print n + 0 }' "$file"
      else
        echo "0"
      fi
      ;;
  esac
}

write_report() {
  local target="$1"
  {
    echo "# Static Quality Baseline Report"
    echo
    echo "Generated: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "Repository: $PROJECT_ROOT"
    echo "Commit: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
    echo
    echo "## Summary"
    echo
    echo "| Check | Exit code | Issue/output count | Log key |"
    echo "|---|---:|---:|---|"
    printf '%s\n' "${ROWS[@]}"
    echo
    echo "## Interpretation"
    echo
    echo "- Exit code 0 means the command passed."
    echo "- Non-zero exit codes in ruff/mypy can be accepted only as an explicitly reviewed baseline with owner approval and expiry."
    echo "- This generated report does not make \`docs/release/evidence/static-quality-baseline.md\` complete by itself."
    echo
    if [ "${#NOTES[@]}" -gt 0 ]; then
      echo "## Notes"
      echo
      printf '%s\n' "${NOTES[@]}"
      echo
    fi
    echo "## Raw Log Files"
    echo
    echo "Logs were collected in a temporary directory during this run and are summarized above. Re-run with shell redirection or CI artifact capture if raw logs must be retained."
  } >"$target"
}

require_backend_tool() {
  local tool="$1"
  local path="backend/.venv/bin/$tool"
  if [ ! -x "$path" ]; then
    NOTES+=("- Skipped backend ${tool}: ${path} is not executable.")
    return 1
  fi
  return 0
}

run_check diff_check "git diff --check" git diff --check

if [ "$QUICK" -eq 0 ]; then
  if require_backend_tool ruff; then
    run_check ruff "backend ruff check src tests" bash -lc "cd backend && ./.venv/bin/ruff check src tests --output-format concise"
  fi

  if require_backend_tool mypy; then
    run_check mypy "backend mypy src" bash -lc "cd backend && ./.venv/bin/mypy src"
    run_check mypy_baseline "backend mypy zero-baseline gate" bash scripts/mypy-baseline-check.sh
  fi
else
  NOTES+=("- Quick mode skipped backend ruff/mypy.")
fi

run_check frontend_lint "frontend lint" bash -lc "cd frontend && npm run lint"
run_check frontend_build "frontend build" bash -lc "cd frontend && npm run build"
run_check desktop_check "desktop cargo check" bash -lc "cd desktop && cargo check"
run_check desktop_test "desktop cargo test" bash -lc "cd desktop && cargo test"
run_check release_evidence_secret_scan "release evidence secret/PII scan" bash scripts/release-evidence-secret-scan.sh

if [ "$QUICK" -eq 0 ]; then
  run_check secret_scan "secret keyword scan" bash -lc "rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' --glob '!backend/.venv/**' --glob '!frontend/dist/**' 'sk-[A-Za-z0-9_-]{32,}|AKIA[0-9A-Z]{16}|BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY' .; rg -n --hidden --glob '!.git/**' --glob '!node_modules/**' --glob '!backend/.venv/**' --glob '!frontend/dist/**' '^(WECHAT_PAY_API_V3_KEY|ALIPAY_PRIVATE_KEY|ESIGN_BAO_APP_SECRET|FADADA_APP_SECRET|JWT_SECRET_KEY)=[^#[:space:]].+' . | rg -v 'your-|change-in-prod|请使用|32-byte|<[^>]+>|^.*=(dev|test|mock|example|placeholder|unused|TBD)(-|$)|^.*=$'"
  run_check mock_scan "release-blocking mock/fallback scan" rg -n 'mock_token_|登录成功（体验模式）|fallbackNews|假新闻|TODO.*真数据|@mock-data FALLBACK|fake success' backend/src frontend/src mobile/app mobile/src mini-program/src
else
  NOTES+=("- Quick mode skipped full-repo secret/mock scans.")
fi

echo
echo "Static quality baseline summary:"
echo "| Check | Exit code | Issue/output count | Log key |"
echo "|---|---:|---:|---|"
printf '%s\n' "${ROWS[@]}"

if [ "${#NOTES[@]}" -gt 0 ]; then
  echo
  echo "Notes:"
  printf '%s\n' "${NOTES[@]}"
fi

if [ -n "$OUT_PATH" ]; then
  mkdir -p "$(dirname "$OUT_PATH")"
  write_report "$OUT_PATH"
  echo
  echo "Wrote report: $OUT_PATH"
fi
