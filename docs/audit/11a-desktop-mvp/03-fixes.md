# TASK-11a Desktop MVP — Fixes

## Desktop Window Chrome

- Kept macOS Overlay/traffic-light behavior in `desktop/tauri.conf.json`.
- Applied non-macOS decoration removal in `desktop/src/lib.rs`.
- Added guarded non-macOS window controls in `frontend/src/components/desktop/TitleBar.tsx`.
- Added `titleBarModel.ts` and tests for platform gating and double-click maximize safety.
- Added `docs/desktop/window-styling.md` and `scripts/desktop-window-chrome-gate.sh` as a repeatable local governance gate.

## Quick Query

- Added a dedicated `quick-query` Tauri window contract in `desktop/src/commands/quick_query.rs`.
- Changed the global shortcut behavior to open/toggle `/desktop/quick-query` rather than hiding the main workstation.
- Added `frontend/src/pages/QuickQuery.tsx` and `quickQueryModel.ts` for concise quick legal questions, local-mode LLM preference, ESC/blur/auto-hide behavior, and cloud/web fallback.
- Added browser coverage in `frontend/e2e/quick-query.spec.ts`.
- Documented the flow in `docs/desktop/quick-query-flow.md`.

## File Drop Analysis Queue

- Added `desktop/src/commands/file_drop.rs` to classify supported file extensions, write encrypted local `offline_tasks`, and emit `desktop://file-queued` with redacted response data.
- Added typed Tauri bridge wrappers for queueing file paths, listening for queue events, and consuming WebView drag/drop events.
- Added `desktopFileDropEvents.ts` and tests to keep toast summaries stable and avoid leaking full local paths.
- Registered global desktop drop listeners in `frontend/src/App.tsx`.

## Desktop Workstation

- Added a visible desktop workstation panel with local model, knowledge base, Skills/MCP, sync, remote-control, and runtime configuration status.
- Added secret-free mode/backend URL writing and environment profile CRUD.
- Added secret-free default local model persistence and workstation UI controls so Quick Query and local-mode calls no longer depend on a hard-coded model name.
- Added a native notification bridge for case progress, risk alerts, system, and sync messages; the bridge sanitizes notification copy, exposes permission status/request IPC, sends through the local Tauri notification plugin, and keeps TopSecret notifications local-only.
- Kept non-desktop previews read-only for desktop-only actions.
- Preserved TopSecret/local fail-closed behavior for sync and remote-control actions.
- Added Playwright workstation coverage for direct/legacy routes, runtime mocks, profile CRUD, mode/backend editing, safe disabled states, and mobile width.

## Runtime Mode and Remote-Control Host

- Added `runtime-config.json` persistence for non-secret `mode` and `backendUrl`.
- Mapped desktop `top-secret` into frontend local business gating in `PrivacyContext`.
- Added DB-backed remote-control pairing/command/audit backend paths, desktop safe-probe host client, bounded polling, env-gated daemon foundation, and visible workstation host controls.
- Kept remote-control execution safe-probe-only; high-risk real execution remains intentionally absent.

## Governance

- Added this `docs/audit/11a-desktop-mvp/` audit package to close the missing TASK-11a documentation output.
- Extended `scripts/desktop-mvp-local-gate.sh` so the quick commercial gate fails if the audit package disappears or loses the core code/evidence vocabulary.
