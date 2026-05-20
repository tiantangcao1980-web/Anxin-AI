# TASK-11a Desktop MVP — Followups

## Remaining P0

- Produce signed/notarized macOS desktop runtime evidence for the main window, native traffic lights, drag region, quick-query window, TopSecret outbound guard, and packaged sync/profile behavior.
- Produce Windows 11 packaged runtime evidence for undecorated main window, minimize/maximize/close controls, double-click maximize/restore, quick-query shortcut, and file-drop feedback.
- Measure `Cmd/Ctrl+Shift+Space` shortcut-to-visible latency in packaged builds and keep P95 under 200 ms, or document the product decision if platform constraints require a different threshold.
- Verify platform tray-icon file drop directly. Until then, WebView file drop is the local code path and tray drop remains release evidence pending.
- Verify file-drop toast latency under 500 ms in a packaged build.
- Run a real local model smoke through the configurable quick-query local LLM path.
- Add a governed one-click model download/install flow after product signs off on supported Ollama model families and disk-space checks.
- Verify native notification permission prompts/system settings and delivery in signed macOS/Windows packaged builds, including tray/background-triggered case progress and risk alert notifications.
- Run a real approved MCP/Skills connector rehearsal from the desktop workstation using external credentials provided outside the repo.
- Run real mobile-to-desktop remote-control safe-probe with a signed desktop host and a real mobile device; do not enable high-risk desktop execution until separate approval, UI confirmation, and audit evidence exist.

## Evidence Owners

- User/external: Apple signing identity, notary credentials, Windows signing certificate, real macOS/Windows devices, real mobile device, payment/e-sign/LLM/MCP provider credentials.
- Local development: keep code-level gates green, keep fake/mock evidence out of `Status: complete`, keep TopSecret/local network boundaries fail-closed, and keep docs synchronized with code.

## Memory Notes Persisted

- Feature `feature-1778335460725`: `tauri-desktop-mvp-trio`, covering platform-specific Tauri chrome, dedicated Quick Query window routing, SQLCipher-backed desktop file-drop queueing, redacted toast events, workstation configuration controls, safe-probe remote-control host controls, and the `desktop-window-chrome` / `desktop-mvp` local gates.

## Release Risk

The desktop MVP is strong enough for continued internal development and controlled local demos. It is not yet strong enough for commercial launch because the remaining blockers are tied to signed packages, real devices, external providers, and measured runtime behavior. These must stay visible in release docs and cannot be replaced by unit tests or mocked artifacts.
