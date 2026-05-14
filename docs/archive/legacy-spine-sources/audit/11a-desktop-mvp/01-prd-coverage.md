# TASK-11a Desktop MVP — PRD Coverage

| Requirement | Current Status | Evidence |
|---|---|---|
| P0-1 desktop window chrome | Code-level implemented; signed visual evidence open | `desktop/tauri.conf.json`, `desktop/src/lib.rs`, `frontend/src/components/Layout.tsx`, `docs/desktop/window-styling.md`, `scripts/desktop-window-chrome-gate.sh` |
| P0-2 quick query shortcut window | Code/browser-level implemented; packaged shortcut performance open | `desktop/src/commands/quick_query.rs`, `frontend/src/pages/QuickQuery.tsx`, `frontend/src/pages/quickQueryModel.ts`, `frontend/e2e/quick-query.spec.ts`, `docs/desktop/quick-query-flow.md` |
| P0-3 file drop analysis queue | Code-level WebView/drop queue and toast implemented; tray gesture/performance open | `desktop/src/commands/file_drop.rs`, `frontend/src/lib/tauri-bridge.ts`, `frontend/src/lib/desktopFileDropEvents.ts`, `frontend/src/App.tsx` |
| P0-4 self-drawn titlebar controls | Code-level implemented for non-macOS; real Windows visual proof open | `frontend/src/components/desktop/TitleBar.tsx`, `frontend/src/components/desktop/titleBarModel.ts`, `frontend/src/components/desktop/titleBarModel.test.ts`, `desktop/capabilities/default.json` |
| P0-5 startup mode and PrivacyContext alignment | Partial | `desktop/src/services/runtime_config.rs` persists secret-free `mode` and `backendUrl`; `frontend/src/context/PrivacyContext.tsx` maps `top-secret` to local business gating. Full SQLite `sync_state` alignment and signed runtime proof remain open |
| P0-6 desktop workstation entry | Code/browser-level implemented; real connector runtime open | `frontend/src/components/desktop/DesktopWorkstationPanel.tsx`, `desktopWorkstationModel.ts`, `frontend/e2e/settings-workstation.spec.ts`, LLM/knowledge/MCP probe wrappers, local default model persistence via `desktop/src/services/runtime_config.rs` and `desktop/src/commands/local_llm.rs` |
| P1-2 native notification bridge | Code/browser-level implemented, including local permission status/request; signed runtime delivery and service push open | `desktop/src/commands/native_notification.rs`, `desktop/src/lib.rs`, `frontend/src/lib/tauri-bridge.ts`, `DesktopWorkstationPanel.tsx`, `desktopWorkstationModel.ts`, `frontend/e2e/settings-workstation.spec.ts` |
| P0-7 mobile remote-control host | Safe-probe-only code/browser/backend path implemented; signed daemon and real device proof open | `backend/src/services/remote_control_service.py`, `desktop/src/services/remote_control_host.rs`, `desktop/src/commands/remote_control.rs`, `frontend/src/components/desktop/DesktopWorkstationPanel.tsx`, `mobile/app/desktop-control.tsx` |
| P0-8 workstation configuration write surface | Code/browser-level implemented; external provider and signed runtime evidence open | `DesktopWorkstationPanel.tsx`, `desktopWorkstationModel.ts`, `desktop/src/commands/app_mode.rs`, `frontend/src/lib/tauri-bridge.ts`, `frontend/e2e/settings-workstation.spec.ts` |
| Audit package | Closed by this change | `docs/audit/11a-desktop-mvp/00-prd-reality-gap.md` through `05-followups.md`; `scripts/desktop-mvp-local-gate.sh` validates the package exists |

## Product Impact

The desktop workstation is now the correct implementation focus for the commercial-readiness goal. Users can see and exercise the main local workstation surfaces in code and browser tests, but commercial launch must wait for signed desktop runtime, real device, real connector, and external evidence rather than treating the current local proof as release proof.
