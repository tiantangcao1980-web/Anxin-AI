#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 - <<'PY'
import json
from pathlib import Path

root = Path(".")
failures: list[str] = []

config = json.loads((root / "desktop/tauri.conf.json").read_text())
main_window = next(
    (window for window in config.get("app", {}).get("windows", []) if window.get("label") == "main"),
    None,
)
if main_window is None:
    failures.append("desktop/tauri.conf.json: missing main window")
else:
    if main_window.get("titleBarStyle") != "Overlay":
        failures.append("desktop/tauri.conf.json: main window must keep titleBarStyle=Overlay")
    if main_window.get("hiddenTitle") is not True:
        failures.append("desktop/tauri.conf.json: main window must keep hiddenTitle=true")
    if not isinstance(main_window.get("trafficLightPosition"), dict):
        failures.append("desktop/tauri.conf.json: main window must keep trafficLightPosition for macOS")

capabilities = json.loads((root / "desktop/capabilities/default.json").read_text())
permissions = set(capabilities.get("permissions", []))
for permission in [
    "core:window:allow-close",
    "core:window:allow-minimize",
    "core:window:allow-maximize",
    "core:window:allow-toggle-maximize",
]:
    if permission not in permissions:
        failures.append(f"desktop/capabilities/default.json: missing {permission}")

checks = {
    "desktop/src/lib.rs": [
        "set_decorations(false)",
        "apply_platform_window_chrome",
        'target_os = "windows"',
    ],
    "frontend/src/components/Layout.tsx": [
        "data-tauri-drag-region",
        "handleDesktopTitleBarDoubleClick",
        "onDoubleClick",
    ],
    "frontend/src/components/desktop/TitleBar.tsx": [
        "DesktopTitleBarControls",
        "shouldHandleDesktopTitleBarDoubleClick",
        "toggleMaximizeCurrentWindow",
        "data-titlebar-control",
    ],
    "frontend/src/components/desktop/titleBarModel.ts": [
        "shouldRenderDesktopTitleBarControls",
        "shouldToggleMaximizeFromTitleBarDoubleClick",
        "tauri-macos",
    ],
    "frontend/src/components/desktop/titleBarModel.test.ts": [
        "tauri-windows",
        "tauri-macos",
        "hasInteractiveAncestor",
    ],
    "docs/desktop/window-styling.md": [
        "Desktop Window Styling",
        "Pending Release Evidence",
        "Signed/notarized",
    ],
}

for relative, required_fragments in checks.items():
    path = root / relative
    if not path.exists():
        failures.append(f"{relative}: missing")
        continue
    text = path.read_text()
    for fragment in required_fragments:
        if fragment not in text:
            failures.append(f"{relative}: missing fragment {fragment!r}")

if failures:
    for failure in failures:
        print(f"Desktop window chrome gate: FAIL: {failure}")
    raise SystemExit(1)

print("Desktop window chrome gate: PASS")
PY
