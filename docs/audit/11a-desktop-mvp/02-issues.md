# TASK-11a Desktop MVP — Issues

| ID | Severity | Issue | Status |
|---|---|---|---|
| DSK-001 | P0 | Desktop window chrome lacked an auditable cross-platform contract | Code-level closed; signed macOS/Windows visual evidence open |
| DSK-002 | P0 | Global shortcut opened/toggled the wrong surface for quick legal questions | Code/browser-level closed; packaged shortcut performance and real local model smoke open |
| DSK-003 | P0 | File-drop analysis had no local encrypted queue and no safe visible feedback | Code-level WebView queue/toast closed; tray-icon drop gesture and 500 ms packaged latency open |
| DSK-004 | P0 | Titlebar controls and double-click maximize were not protected by a platform/interaction model | Code-level closed; Windows packaged runtime proof open |
| DSK-005 | P0 | Desktop runtime mode could drift from frontend business/privacy gates | Partial; secret-free runtime config and PrivacyContext mapping closed, fuller SQLite `sync_state` alignment and signed proof open |
| DSK-006 | P0 | Desktop had no main workstation entry for local model, knowledge base, Skills/MCP, sync, and remote control | Code/browser-level closed; real approved connector runtime open |
| DSK-007 | P0 | Mobile remote-control host was undefined and could become unsafe if high-risk execution appeared before governance | Safe-probe-only backend/desktop/mobile foundation closed; signed daemon, real cross-device callback, and high-risk executor open |
| DSK-008 | P0 | Workstation configuration was read-only and lacked local profile CRUD | Code/browser-level closed for secret-free mode/backend/profile data; provider credential CRUD and real connector evidence open |
| DSK-009 | P1 | TASK-11a required audit docs did not exist under `docs/audit/11a-desktop-mvp/` | Closed by this audit package and local gate check |

## Release Interpretation

Closed code-level issues may support local development and internal demo, but they do not support a commercial-ready claim by themselves. Any issue that still requires signed runtime, external provider, or true device evidence remains release-blocking until the corresponding artifact is produced and marked complete by the evidence validators.
