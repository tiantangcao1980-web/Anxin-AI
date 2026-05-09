# TASK-11a Desktop MVP — Test Additions

## Local Gates

```bash
bash scripts/desktop-window-chrome-gate.sh
# Desktop window chrome gate: PASS

bash scripts/desktop-mvp-local-gate.sh
# Desktop MVP local gate: PASS
```

`desktop-mvp-local-gate.sh` now checks both code surfaces and the audit package:

- Quick Query window, local/cloud behavior model, browser route, and documentation.
- File-drop classification, encrypted queue command, WebView drop listener, toast summary, and release evidence.
- Desktop workstation panel, mode/backend/profile model, Playwright workstation coverage, and safe desktop/preview boundaries.
- Local model manager coverage for model-name normalization, secret-free default-model persistence, and workstation UI save flow.
- Native notification local-only bridge coverage for sanitized IPC payloads, TopSecret-safe readiness, and workstation test notification flow.
- `docs/audit/11a-desktop-mvp/00-prd-reality-gap.md` through `05-followups.md`.

## Existing Targeted Tests

```bash
cd desktop && cargo test quick_query
# 2 passed

cd desktop && cargo test file_drop
# 4 passed

cd desktop && cargo test app_mode
# 2 passed

cd desktop && cargo test runtime_config
# 5 passed

cd desktop && cargo test remote_control
# 14 passed in the last recorded host-cycle run

cd desktop && cargo test native_notification
# 5 passed; covers native notification local-only preview and payload sanitization
```

```bash
cd frontend && npm test -- quickQueryModel.test.ts
# 4 passed

cd frontend && npm test -- desktopFileDropEvents.test.ts
# 5 passed

cd frontend && npm test -- titleBarModel.test.ts
# 2 passed

cd frontend && npm test -- desktopWorkstationModel.test.ts
# 12 passed; includes native notification local-only readiness

cd frontend && npm test -- PrivacyContext.test.ts
# 3 passed
```

```bash
cd frontend && npx playwright test e2e/quick-query.spec.ts --project=chromium
# 1 passed

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium
# 7 passed, 1 skipped in the last recorded workstation run

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=mobile
# 8 passed in the last recorded workstation run
```

## Commercial Gate Coverage

`scripts/commercial-readiness-gate.sh --quick` runs the desktop window chrome gate and desktop MVP local gate before release. The gate is expected to keep failing overall until external/signed/device evidence is complete, but a drift in the desktop MVP local surfaces now fails earlier with a targeted message.

## Not Covered Locally

- Signed/notarized macOS and Windows packaged runtime proof.
- Real tray-icon drop gesture and 500 ms toast latency.
- Real packaged shortcut-to-visible latency under 200 ms.
- Real local model endpoint smoke.
- One-click model download/install flow.
- Real approved Skills/MCP connector runtime.
- Signed remote-control daemon, true cross-device host callback, and high-risk executor flow.
