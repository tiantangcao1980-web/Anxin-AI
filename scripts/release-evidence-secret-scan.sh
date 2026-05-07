#!/usr/bin/env bash
# High-confidence secret/PII scan for release evidence artifacts.
#
# This focuses on docs/release/evidence because those files may later include
# redacted provider logs, screenshots, callback excerpts, and JSON artifacts.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

TARGET="${1:-docs/release/evidence}"

if [ ! -e "$TARGET" ]; then
  echo "Release evidence secret scan: PASS (target missing: $TARGET)"
  exit 0
fi

patterns=(
  '-----BEGIN ([A-Z ]+ )?PRIVATE KEY-----'
  'sk-[A-Za-z0-9_-]{24,}'
  'AKIA[0-9A-Z]{16}'
  '(WECHAT_PAY_API_V3_KEY|ALIPAY_PRIVATE_KEY|ESIGN_BAO_APP_SECRET|FADADA_APP_SECRET|JWT_SECRET_KEY|ACCESS_TOKEN|REFRESH_TOKEN)\s*[:=]\s*["'\'']?[^"'\''<[:space:]][^"'\'']{7,}'
  '\b1[3-9][0-9]{9}\b'
  '\b[0-9]{17}[0-9Xx]\b'
)

tmp_file="$(mktemp "${TMPDIR:-/tmp}/anxin-evidence-secret-scan.XXXXXX")"
trap 'rm -f "$tmp_file"' EXIT

for pattern in "${patterns[@]}"; do
  rg -n --pcre2 --hidden --glob '!*.png' --glob '!*.jpg' --glob '!*.jpeg' --glob '!*.gif' \
    -- "$pattern" "$TARGET" >>"$tmp_file" || true
done

if [ -s "$tmp_file" ]; then
  echo "Release evidence secret scan: FAIL"
  cat "$tmp_file"
  exit 1
fi

echo "Release evidence secret scan: PASS"
