#!/usr/bin/env bash
# Fail closed on desktop native/WebView data-network surfaces that must stay
# narrow before a commercial desktop release.

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
    add_failure "missing or empty required file: $path"
  fi
}

required_files=(
  "desktop/Cargo.toml"
  "desktop/src/lib.rs"
  "desktop/capabilities/default.json"
  "desktop/gen/schemas/capabilities.json"
  "desktop/tauri.conf.json"
  "frontend/package.json"
  "frontend/package-lock.json"
)

for file in "${required_files[@]}"; do
  require_file "$file"
done

if [ "${#failures[@]}" -eq 0 ]; then
  if rg -n -F "tauri-plugin-http" desktop/Cargo.toml >/tmp/anxin-desktop-network-rg.out; then
    while IFS= read -r line; do
      add_failure "desktop Rust HTTP plugin dependency is enabled: $line"
    done </tmp/anxin-desktop-network-rg.out
  fi

  if rg -n -F "tauri_plugin_http" desktop/src/lib.rs >/tmp/anxin-desktop-network-rg.out; then
    while IFS= read -r line; do
      add_failure "desktop Rust HTTP plugin is registered: $line"
    done </tmp/anxin-desktop-network-rg.out
  fi

  if rg -n -F "@tauri-apps/plugin-http" frontend/package.json frontend/package-lock.json >/tmp/anxin-desktop-network-rg.out; then
    while IFS= read -r line; do
      add_failure "frontend HTTP plugin package remains installable: $line"
    done </tmp/anxin-desktop-network-rg.out
  fi

  if ! node <<'NODE'
const fs = require("fs");

function fail(message) {
  console.error(message);
  process.exitCode = 1;
}

function readJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function checkCapabilityFile(path, permissions) {
  const httpPermissions = permissions.filter(
    (value) => typeof value === "string" && value.startsWith("http:")
  );
  if (httpPermissions.length > 0) {
    fail(`${path} enables active HTTP capability permissions: ${httpPermissions.join(", ")}`);
  }
}

const capability = readJson("desktop/capabilities/default.json");
checkCapabilityFile("desktop/capabilities/default.json", capability.permissions || []);

const generatedCapabilities = readJson("desktop/gen/schemas/capabilities.json");
const generatedDefault = generatedCapabilities.default || {};
checkCapabilityFile(
  "desktop/gen/schemas/capabilities.json",
  generatedDefault.permissions || []
);

const tauriConfig = readJson("desktop/tauri.conf.json");
const csp = tauriConfig?.app?.security?.csp || "";
const directives = new Map(
  csp
    .split(";")
    .map((entry) => entry.trim().split(/\s+/).filter(Boolean))
    .filter((parts) => parts.length > 0)
    .map(([name, ...tokens]) => [name, tokens])
);
if (!/\bconnect-src\b/.test(csp)) {
  fail("desktop/tauri.conf.json CSP must include connect-src");
}
if ((directives.get("script-src") || []).includes("'unsafe-eval'")) {
  fail("desktop/tauri.conf.json CSP must not allow script-src 'unsafe-eval'");
}
if ((directives.get("img-src") || []).includes("https://*")) {
  fail("desktop/tauri.conf.json CSP must not allow broad img-src https://*");
}
NODE
  then
    add_failure "desktop network surface JSON/CSP checks failed"
  fi
fi

rm -f /tmp/anxin-desktop-network-rg.out

if [ "${#failures[@]}" -gt 0 ]; then
  echo "Desktop network surface gate: FAIL"
  for failure in "${failures[@]}"; do
    echo "  - $failure"
  done
  exit 1
fi

echo "Desktop network surface gate: PASS"
