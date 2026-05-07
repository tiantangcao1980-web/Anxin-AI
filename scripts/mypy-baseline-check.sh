#!/usr/bin/env bash
# Enforce the current backend mypy baseline as a no-regression gate.
#
# The default baseline is now zero; override only for explicit emergency
# rollback windows with a dated release-owner note.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

BASELINE_MAX_ERRORS="${MYPY_BASELINE_MAX_ERRORS:-0}"

if ! [[ "$BASELINE_MAX_ERRORS" =~ ^[0-9]+$ ]]; then
  echo "ERROR: MYPY_BASELINE_MAX_ERRORS must be an integer" >&2
  exit 2
fi

if [ ! -x backend/.venv/bin/mypy ]; then
  echo "ERROR: backend/.venv/bin/mypy is not executable" >&2
  exit 2
fi

TMP_OUTPUT="$(mktemp /tmp/anxin-mypy-baseline.XXXXXX)"
trap 'rm -f "$TMP_OUTPUT"' EXIT

set +e
(
  cd backend
  ./.venv/bin/mypy src --show-error-codes --no-error-summary --no-pretty
) >"$TMP_OUTPUT" 2>&1
MYPY_RC=$?
set -e

ERROR_COUNT="$(awk '/^[^:]+:[0-9]+(:[0-9]+)?: error: / { n++ } END { print n + 0 }' "$TMP_OUTPUT")"

echo "backend mypy errors: ${ERROR_COUNT} (baseline max: ${BASELINE_MAX_ERRORS})"

if [ "$ERROR_COUNT" -gt "$BASELINE_MAX_ERRORS" ]; then
  echo "mypy baseline regression detected" >&2
  echo >&2
  echo "Top error codes:" >&2
  awk '
    /^[^:]+:[0-9]+(:[0-9]+)?: error: / {
      if (match($0, /\[[^]]+\]$/)) {
        code = substr($0, RSTART + 1, RLENGTH - 2)
        counts[code]++
      }
    }
    END {
      for (code in counts) print counts[code], code
    }
  ' "$TMP_OUTPUT" | sort -nr | head -20 >&2
  exit 1
fi

if [ "$MYPY_RC" -eq 0 ]; then
  echo "mypy is fully clean"
elif [ "$BASELINE_MAX_ERRORS" -gt 0 ]; then
  echo "mypy remains non-zero but is within the approved emergency baseline"
else
  echo "mypy returned non-zero while zero baseline is required" >&2
  exit 1
fi
