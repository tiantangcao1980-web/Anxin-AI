#!/usr/bin/env bash
# Guard the uni-app migration boundary:
# - legacy Expo/Taro clients stay frozen for new feature work
# - apps/uni-mobile keeps the shared API/auth/privacy/platform/token foundation
# - package scripts required by release smoke stay present

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

failures=()

add_failure() {
  failures+=("$1")
}

require_file() {
  local path="$1"
  if [ ! -f "$path" ]; then
    add_failure "missing required migration file: $path"
  fi
}

require_contains() {
  local path="$1"
  local pattern="$2"
  local label="$3"
  if [ ! -f "$path" ]; then
    add_failure "missing $label file: $path"
    return
  fi
  if ! rg -q "$pattern" "$path"; then
    add_failure "$label missing required text: $pattern"
  fi
}

require_contains "mobile/README.md" "Status: legacy" "legacy mobile README"
require_contains "mobile/README.md" "apps/uni-mobile/" "legacy mobile README"
require_contains "mobile/README.md" "limited to security fixes" "legacy mobile README"
require_contains "mini-program/README.md" "Status: legacy" "legacy mini-program README"
require_contains "mini-program/README.md" "apps/uni-mobile/" "legacy mini-program README"
require_contains "mini-program/README.md" "limited to security fixes" "legacy mini-program README"
require_contains "docs/mobile/uni-app-migration-plan.md" '旧 `mobile/` Expo 与 `mini-program/` Taro 保留为 legacy' "uni-app migration plan"
require_contains "docs/mobile/uni-app-migration-plan.md" '新功能写入 `apps/uni-mobile/`' "uni-app migration plan"

for path in \
  "apps/uni-mobile/src/services/api.ts" \
  "apps/uni-mobile/src/services/privacy.ts" \
  "apps/uni-mobile/src/services/sync.ts" \
  "apps/uni-mobile/src/stores/auth.ts" \
  "apps/uni-mobile/src/platform/wechat.ts" \
  "apps/uni-mobile/src/features/desktop-control/model.ts" \
  "apps/uni-mobile/src/styles/tokens.ts" \
  "apps/uni-mobile/src/styles/tokens.scss" \
  "apps/uni-mobile/src/pages/auth/login.vue" \
  "apps/uni-mobile/src/pages/approvals/index.vue" \
  "apps/uni-mobile/src/pages/desktop-control/index.vue"; do
  require_file "$path"
done

python3 - <<'PY' || exit_code=$?
import json
from pathlib import Path

package_path = Path("apps/uni-mobile/package.json")
package = json.loads(package_path.read_text(encoding="utf-8"))
scripts = package.get("scripts") or {}
required = {
    "typecheck",
    "test",
    "audit:prod",
    "build:h5",
    "build:mp-weixin",
}
missing = sorted(required - scripts.keys())
if missing:
    raise SystemExit("apps/uni-mobile/package.json missing scripts: " + ", ".join(missing))
PY
if [ "${exit_code:-0}" -ne 0 ]; then
  add_failure "apps/uni-mobile/package.json required smoke scripts are incomplete"
fi

if [ "${#failures[@]}" -gt 0 ]; then
  echo "uni-mobile migration guard: FAIL"
  for failure in "${failures[@]}"; do
    echo "  - $failure"
  done
  exit 1
fi

echo "uni-mobile migration guard: PASS"
