# TASK-11a Desktop MVP — PRD Reality Gap

> Date: 2026-05-09
> Scope: Desktop workstation MVP, with the current goal contract requiring desktop-first local execution before mobile and mini-program work.

## PRD Promise

- P0-1: Desktop window chrome is platform-native enough for commercial use: macOS keeps traffic lights in place, Windows removes the default frame, and the app owns a consistent top drag/title surface.
- P0-2: `Cmd/Ctrl+Shift+Space` opens a compact quick-query assistant window instead of disturbing the main workspace.
- P0-3: Desktop file drop routes contracts and documents into the local analysis queue with visible feedback.
- P0-4: The self-drawn titlebar behaves consistently across macOS, Windows, and Linux.
- P0-5: Desktop startup restores privacy mode from local runtime state and keeps frontend business gates aligned with that mode.
- P0-6: The desktop shell exposes a main workstation entry for local model, knowledge base, Skills/MCP, sync, and remote-control status.
- P0-7: Desktop can act as a mobile remote-control host, but only through scoped pairing, route token, audit, and safe-probe boundaries until high-risk execution is separately approved.
- P0-8: Desktop users can locally edit secret-free workstation runtime configuration and reusable environment profiles.

## Code Reality

- Window chrome has a code-level contract: `desktop/tauri.conf.json` keeps macOS `titleBarStyle: "Overlay"` and traffic light positioning, `desktop/src/lib.rs` disables decorations on Windows/Linux, and `frontend/src/components/desktop/TitleBar.tsx` plus `frontend/src/components/desktop/titleBarModel.ts` provide guarded non-macOS controls and double-click maximize behavior.
- Quick Query has a code-level end-to-end path: `desktop/src/commands/quick_query.rs` defines the `quick-query` window, the desktop shortcut toggles `/desktop/quick-query`, and `frontend/src/pages/QuickQuery.tsx` chooses local LLM in `top-secret`/`hybrid` desktop modes while keeping cloud/web fallback on the existing chat API.
- File drop has a local data path: `desktop/src/commands/file_drop.rs` classifies `.pdf/.doc/.docx` as `contract_review`, `.txt/.md` as `document_summary`, writes supported files into Rust SQLCipher/keyring-owned `offline_tasks`, and emits `desktop://file-queued` without exposing full local paths.
- WebView drop and toast feedback exist through `frontend/src/lib/tauri-bridge.ts`, `frontend/src/lib/desktopFileDropEvents.ts`, and `frontend/src/App.tsx`; platform tray-icon drop is still not proven.
- Desktop workstation entry and configuration have code-level coverage: `DesktopWorkstationPanel.tsx`, `desktopWorkstationModel.ts`, Tauri bridge wrappers, Settings routing, and Playwright workstation tests cover status probes, mode/backend URL writing, secret-free profile CRUD, and safe disabled states.
- Desktop native notification has code-level coverage: `desktop/src/commands/native_notification.rs` sanitizes local payloads, `frontend/src/lib/tauri-bridge.ts` exposes typed IPC wrappers, and the workstation panel can send a local-only test notification without external push infrastructure.
- Runtime mode persistence and frontend gate alignment exist through `desktop/src/services/runtime_config.rs`, `desktop/src/commands/app_mode.rs`, `frontend/src/context/PrivacyContext.tsx`, and related tests.
- Remote-control host is visible and bounded: backend host lifecycle APIs, desktop IPC clients, env-gated safe-probe daemon foundation, workstation UI, mobile status/safe-probe surfaces, and route-token policy are implemented for safe-probe only.

## Remaining Reality Gap

The desktop MVP is no longer an empty shell, but it is still not a commercial release proof. The local code and browser-level gates cover the main workstation, window chrome, quick query, file-drop queueing, native notification bridge, and remote-control safe-probe UI. The blockers are release-evidence blockers:

- macOS and Windows signed packaged runtime screenshots/videos for titlebar, window controls, and drag regions.
- A measured packaged shortcut-to-visible baseline under 200 ms on macOS and Windows.
- Platform-level tray-icon file-drop gesture and toast latency under 500 ms.
- Signed/notarized runtime smoke, signed packaged-profile migration, and signed runtime top-secret outbound fail-closed proof.
- Real local model smoke and real approved Skills/MCP connector runtime evidence.
- Real cross-device remote-control host callback, signed daemon runtime, and future high-risk executor governance.

## Conclusion

TASK-11a is code-level and governance-level advanced, not commercially complete. This audit package closes the missing prompt-to-artifact documentation gap and keeps the remaining blockers explicit instead of marking release evidence complete prematurely.
