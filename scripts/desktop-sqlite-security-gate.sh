#!/usr/bin/env bash
# Desktop SQLite encryption/keyring release gate.
#
# This gate is intentionally narrow: it verifies whether the desktop build has
# moved away from plaintext tauri-plugin-sql SQLite and whether the Rust
# self-test contract still declares SQLCipher/keyring as non-release-blocking.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

failures=()

add_failure() {
  failures+=("$*")
}

require_file() {
  local path="$1"
  if [ ! -s "$path" ]; then
    add_failure "missing or empty file: $path"
  fi
}

require_file "desktop/Cargo.toml"
require_file "desktop/src/lib.rs"
require_file "desktop/src/commands/secure_db.rs"
require_file "desktop/src/services/secure_db.rs"
require_file "frontend/src/lib/api-adapter.ts"
require_file "docs/desktop/sqlite-encryption-strategy.md"

if rg -q 'tauri-plugin-sql\s*=\s*\{[^}]*features\s*=\s*\["sqlite"\]' desktop/Cargo.toml; then
  add_failure "desktop still uses plaintext tauri-plugin-sql sqlite feature"
fi

if ! rg -qi 'sqlcipher|tauri-plugin-stronghold|keyring|secret-service|windows-credentials|dpapi' \
  desktop/Cargo.toml; then
  add_failure "no SQLCipher/keyring/secure-store desktop dependency is configured"
fi

if rg -q 'encrypted:\s*false' desktop/src/lib.rs; then
  add_failure "desktop runtime self-test still reports encrypted=false"
fi

if rg -q 'keyring_backed:\s*false' desktop/src/lib.rs; then
  add_failure "desktop runtime self-test still reports keyring_backed=false"
fi

if rg -q 'release_blocking:\s*true' desktop/src/lib.rs; then
  add_failure "desktop runtime self-test still reports release_blocking=true"
fi

if ! rg -q 'pub const RESET_CONFIRMATION: &str = "ERASE LOCAL DATA"' desktop/src/services/secure_db.rs; then
  add_failure "desktop secure DB reset confirmation phrase is missing"
fi

for reset_surface in desktop/src/commands/secure_db.rs desktop/src/lib.rs frontend/src/lib/api-adapter.ts; do
  if ! rg -q 'secure_db_reset_local_data' "$reset_surface"; then
    add_failure "desktop lost-key erase-local-data command is missing from $reset_surface"
  fi
done

if [ "${#failures[@]}" -gt 0 ]; then
  echo "Desktop SQLite security gate: FAIL"
  for failure in "${failures[@]}"; do
    echo "  - $failure"
  done
  exit 1
fi

echo "Desktop SQLite security gate: PASS"
