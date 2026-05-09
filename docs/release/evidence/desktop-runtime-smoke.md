# Desktop Runtime Smoke Evidence

Status: pending
Owner: Desktop release owner TBD
Environment: Rust SQLCipher/keyring security gate complete; local installed-profile keyring reopen smoke complete; debug binary runtime smoke complete; debug macOS app bundle self-test/runtime startup/WebView page-load smoke complete after the 2026-05-09 `mktemp` portability fix; packaged-binary sync code smoke entrypoint complete in unsigned debug `.app`; unsigned release app+DMG build complete in unsandboxed macOS environment; unsigned release packaged runtime self-test/startup/WebView page-load/sync loopback smoke complete; unsigned release packaged-profile SQLCipher/keyring migration and SQLCipher 100/500 performance smoke complete; cross-device continuation code-level rehearsal complete; release package dry-run/preflight complete with hdiutil/DiskManagement probe; signed/notarized packaged release evidence pending
Date range: 2026-05-06 to 2026-05-09 local collection

> This is runtime evidence, not a substitute for `cargo check`, Vitest, or Tauri debug build. Do not mark complete until a packaged desktop app has exercised local SQLCipher, keyring reopen, and sync behavior end to end.

## Required Scope

| Area | Required evidence | Status | Artifact reference |
|---|---|---|---|
| SQLCipher migration | Packaged app opens `sqlcipher:anxin_local.db` and applies migration 1 | code-level pass; SQLite SQL smoke pass; SQLCipher service migration tests pass; local installed-profile plaintext migration smoke pass; unsigned release packaged-profile plaintext migration smoke pass; legacy `sync_log` startup compatibility pass; debug binary self-test/runtime smoke pass; debug `.app` bundle binary self-test/runtime startup/UI load pass after 2026-05-09 local rerun; signed/notarized packaged evidence pending | `bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` -> release binary plaintext-to-SQLCipher migration/keyring reopen pass; `bash scripts/desktop-runtime-smoke.sh --with-app-bundle --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260509-debug-local.log` -> debug bundle runtime startup and WebView page-load pass; `docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260509-debug-local.json`; `bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507-local.json`; `bash scripts/desktop-sqlite-security-gate.sh` -> exit `0` |
| Push | Seed local `sync_log` pending row, run sync, verify backend receives row | frontend bridge code-level pass; Rust IPC fallback code-level pass; packaged-binary sync code smoke pass; unsigned release packaged-binary loopback backend receives 2 push records with bearer header; shared staging backend pending | `frontend api-adapter.sync.test.ts`; `docs/release/evidence/artifacts/desktop-rust-ipc-sync-code-smoke-20260509.json`; `docs/release/evidence/artifacts/desktop-release-runtime-unsigned-smoke-20260509.json` -> `release_sync_loopback_smoke=passed`, `backend_received_records=2`, `auth_header_received=true` |
| Pull | Backend exposes remote update, run sync, verify local SQLite writeback | code-level pass; unsigned release packaged-binary loopback pull writes 1 remote document and advances cursor to 13; shared staging backend pending | `frontend api-adapter.sync.test.ts`: included in `12 passed`; `desktop-release-runtime-unsigned-smoke-20260509.json` -> `pull_records_written=1`, `cursor_advanced_to=13` |
| Conflict | Seed conflicting row, verify conflict UI lists it | code-level pass; unsigned release packaged-binary loopback marks 1 row conflicted; full packaged UI conflict review still pending | `frontend sync-conflict-utils.test.ts`: included in `12 passed`; `desktop-release-runtime-unsigned-smoke-20260509.json` -> `rows_conflicted=1` |
| Conflict resolution | Keep-local, keep-remote, and merge paths update local/remote state correctly | code-level pass; packaged runtime pending | `frontend sync-conflict-utils.test.ts`: included in `12 passed` |
| Retry/backoff | Failed row increments `retry_count`, sets `next_retry_at`, and avoids immediate retry | code-level pass; packaged-binary sync code and loopback retry-to-human gate pass; shared staging retry transcript pending | `frontend api-adapter.sync.test.ts`: included in `12 passed`; `desktop-release-runtime-unsigned-smoke-20260509.json` -> `retry_needs_human=true` |
| Human intervention | Exhausted retry marks `needs_human` and surfaces a user-visible state | code-level pass; packaged-binary sync code and loopback retry-to-human gate pass; packaged UI human intervention transcript pending | `frontend api-adapter.sync.test.ts`: included in `12 passed`; `desktop-release-runtime-unsigned-smoke-20260509.json` -> `retry_needs_human=true` |
| Encryption | Local database cannot expose messages/documents/contracts/cases as plaintext | code-level SQLCipher pass; local installed-profile plaintext-read rejection pass; unsigned release packaged-profile plaintext-read rejection pass; signed/notarized packaged evidence pending | `desktop-release-profile-unsigned-smoke-20260508.json` and `desktop-installed-profile-smoke-20260507.json` both report `plaintextOpenBlocked=true` |
| Keyring | App restarts and reopens encrypted DB through platform key store | local installed-profile keyring reopen pass; unsigned release packaged-profile keyring reopen pass; signed/notarized packaged evidence pending | release packaged-profile smoke and installed-profile smoke both run twice with an isolated real keyring service/user; reports have `keyringRoundTrip=true` and `encryptedReopen=true` on both launches |
| Performance | 100 push records P95 < 2s and 500 pull records P95 < 3s | code-level SQLite/SQLCipher path pass; debug bundle runtime/UI smoke pass; unsigned release packaged SQLCipher performance pass; signed/notarized packaged runtime performance pending | `desktop-release-profile-unsigned-smoke-20260508.json` -> 100 push rows P95 `3.5ms`, 500 pull rows P95 `1.8ms`; `desktop-runtime-code-smoke-20260509-debug-local.json` -> code-level 100 push rows P95 `14.0ms`, 500 pull rows P95 `17.8ms` |
| Cross-device | Desktop to web/mobile continuation succeeds without duplicate/lost rows | code-level pass; signed/shared staging device evidence pending | `bash scripts/cross-device-continuation-smoke.sh --out docs/release/evidence/artifacts/cross-device-continuation-code-smoke-20260509.json` -> backend SyncService desktop/web/mobile continuation `5 passed`, frontend desktop sync adapter `10 passed`, uni-app sync client contract `5 passed`; artifact has `release_evidence_complete=false` |

## Verification Commands

```bash
bash scripts/desktop-runtime-smoke.sh
bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-YYYYMMDD.json
bash scripts/desktop-runtime-smoke.sh --with-app-bundle \
  --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-YYYYMMDD.json \
  --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-YYYYMMDD.log
bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json
bash scripts/desktop-release-package.sh --dry-run \
  --out docs/release/evidence/artifacts/desktop-release-package-dry-run-YYYYMMDD.json \
  --preflight-out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json
bash scripts/desktop-release-runtime-smoke.sh \
  --out docs/release/evidence/artifacts/desktop-release-runtime-unsigned-smoke-YYYYMMDD.json \
  --ui-log-out docs/release/evidence/artifacts/desktop-release-runtime-ui-smoke-unsigned-YYYYMMDD.log
desktop/target/debug/bundle/macos/安心法务.app/Contents/MacOS/anxin-legal-desktop --sync-code-smoke
desktop/target/release/bundle/macos/安心法务.app/Contents/MacOS/anxin-legal-desktop --sync-loopback-smoke
bash scripts/desktop-release-profile-smoke.sh \
  --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-YYYYMMDD.json
cd frontend && npm run test -- api-adapter.sync.test.ts sync-conflict-utils.test.ts
cd desktop && cargo test
cd desktop && cargo tauri build --debug --no-bundle --ci
cd desktop && cargo tauri build --debug --ci --bundles app --no-sign
cd desktop && ./target/debug/anxin-legal-desktop --self-test
cd desktop && ./target/debug/bundle/macos/安心法务.app/Contents/MacOS/anxin-legal-desktop --self-test
sqlite3 /tmp/anxin-smoke.db < desktop/migrations/001_offline_queue.sql
bash scripts/desktop-sqlite-security-gate.sh
bash scripts/cross-device-continuation-smoke.sh \
  --out docs/release/evidence/artifacts/cross-device-continuation-code-smoke-YYYYMMDD.json
```

## Latest Local Collection

Command:

```bash
bash scripts/desktop-runtime-smoke.sh --with-app-bundle \
  --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260509-debug-local.log
```

Result collected on 2026-05-09:

| Check | Result |
|---|---|
| frontend desktop sync Vitest slice | `2 files / 15 tests passed` |
| desktop cargo test | `50 passed` on direct 2026-05-09 rerun; prior bundled runtime script slice recorded `47 passed` |
| desktop cargo check | exit `0` |
| desktop strict Clippy | `cargo clippy --all-targets -- -D warnings` exit `0`; artifact `docs/release/evidence/artifacts/desktop-clippy-gate-20260509.json` |
| desktop SQLite migration SQL smoke | exit `0`; migration applies to a fresh temp SQLite DB, 8 required local/sync tables exist, `sync_log` retry row round-trips, legacy six-column `sync_log` startup path is preserved, frontend repair SQL fills `next_retry_at`/`needs_human`, `PRAGMA integrity_check` returns `ok` |
| desktop SQLite 100/500 sync performance smoke | exit `0`; 5-sample P95: 100 pending push rows `14.0ms`, 500 local pull writebacks `17.8ms` |
| desktop runtime code smoke JSON artifact | `docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260509-debug-local.json`; records debug bundle runtime startup and UI load as passed while keeping `release_evidence_complete=false` |
| desktop runtime UI smoke log artifact | `docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260509-debug-local.log`; WebView page-load payload contains `pageLoadFinished=true`, `webviewLabel=main`, `url=tauri://localhost` |
| desktop Tauri debug `.app` bundle build | exit `0`; built `desktop/target/debug/bundle/macos/安心法务.app` with `--debug --ci --bundles app --no-sign` |
| desktop debug `.app` bundle binary self-test | exit `0`; validates `sqlcipher:anxin_local.db`, migration `1`, 8 required local/sync tables, retry schema, and `sqlite_security.encrypted=true`, `keyring_backed=true`, `release_blocking=false` |
| desktop debug `.app` packaged-binary sync code smoke | exit `0`; `scripts/desktop-release-runtime-smoke.sh --app desktop/target/debug/bundle/macos/安心法务.app --ui-log-out /tmp/anxin-debug-release-runtime-sync-code-smoke.log` calls the app binary `--sync-code-smoke` and verifies migration, pending/deferred/conflict/needs_human counts, two push payload records, one accepted row after conflict filtering, retry-to-human gate, and pull response decode; supporting evidence only, no real backend or signed runtime |
| desktop debug `.app` runtime startup smoke | exit `0`; bundle binary prints `desktop runtime smoke starting: exit_after_ms=1500` and `desktop runtime smoke exiting: exit_after_ms=1500` |
| desktop debug `.app` WebView page-load smoke | exit `0`; page-load handshake returns `pageLoadFinished=true`, `webviewLabel=main`, `windowLabel=main`, `url=tauri://localhost` |
| desktop Rust IPC offline/sync status guard | exit `0`; `submit_offline_task`, `get_queue_stats`, `flush_offline_queue`, `trigger_sync`, `get_sync_status`, and `get_pending_sync_count` now read local queue/sync tables and return explicit blocked/deferred/conflict counts instead of reporting empty-payload success |
| desktop Rust IPC sync fallback code smoke | `cargo test sync_engine` -> `6 passed`; `cargo test sync` -> `7 passed`; `trigger_sync` fallback now reads SQLCipher retryable rows, pushes `/sync/push`, marks accepted/conflict/failed rows, pulls `/sync/pull`, writes supported local entity tables, and updates `sync.last_server_version`; artifact keeps `release_evidence_complete=false` |
| desktop release package dry-run | exit `0`; redacted artifact reports `hdiutil` / DiskManagement probe pass, unsigned release `.app` and DMG exist, and remaining blockers are Developer ID signing identity, notarization credentials, Tauri signing identity, keychain codesign identity, code-sign verification, and signature authority | `docs/release/evidence/artifacts/desktop-release-package-dry-run-20260507.json` |
| desktop signed/notarized release preflight | exit `0`; redacted artifact reports `release_ready=false` with blockers `tauri.signing_identity`, `codesign.identities`, `notary.credentials`, `release.app.codesign_verify`, `release.app.signature_authority`; `command.hdiutil=pass`, `dmg.hdiutil_create_probe=pass`, `release.app.exists=pass`, `release.dmg.exists=pass`, and `tauri.entitlements.aps_environment=pass`; supporting debug `.app`, runtime transcript, and installed-profile report are present | `docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` |
| desktop unsigned release app+DMG build | exit `0` in unsandboxed macOS environment; unsigned release `.app` and `desktop/target/release/bundle/dmg/安心法务_1.0.0_aarch64.dmg` were built; earlier sandbox failure is attributed to blocked `hdiutil` / DiskManagement access, not product packaging logic | `docs/release/evidence/artifacts/desktop-release-unsigned-local-build-20260507.json` |
| desktop unsigned release `.app`/DMG preflight | exit `0`; release `.app` and DMG exist, but `release_ready=false` remains blocked by missing signing identity, codesign identity, notarization credentials, code-sign verification, and signature authority | `docs/release/evidence/artifacts/desktop-release-preflight-unsigned-20260507.json` |
| desktop unsigned release packaged runtime smoke | exit `0`; release bundle binary self-test validates 8 local/sync tables plus SQLCipher/keyring security, packaged sync code smoke validates migration/pending/conflict/retry/pull decode, packaged sync loopback smoke starts a local HTTP backend and proves bearer-auth push of 2 records, 1 accepted row, 1 conflict row, 1 pull writeback and cursor advance to 13, runtime startup exits cleanly, and WebView page-load handshake returns `pageLoadFinished=true`, `webviewLabel=main`, `url=tauri://localhost`; artifact has `signed_or_notarized=false`, `release_sync_code_smoke=passed`, `release_sync_loopback_smoke=passed`, and `release_evidence_complete=false` | `docs/release/evidence/artifacts/desktop-release-runtime-unsigned-smoke-20260509.json`; UI transcript `docs/release/evidence/artifacts/desktop-release-runtime-ui-smoke-unsigned-20260509.log` |
| desktop unsigned release packaged-profile/performance smoke | exit `0` in unsandboxed macOS Keychain context; release bundle binary migrates a seeded plaintext profile DB to SQLCipher, creates an isolated real keyring key, reopens without `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX`, ordinary `sqlite3` cannot read the encrypted DB, and SQLCipher 100 push / 500 pull performance passes with P95 `3.5ms` / `1.8ms`; artifact has `signed_or_notarized=false` and `release_evidence_complete=false` | `docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` |
| desktop SQLite security gate | exit `0`; confirms Rust SQLCipher/keyring dependencies are present, frontend `@tauri-apps/plugin-sql` package is absent, stale Tauri SQL capability is removed, and Rust self-test reports encrypted/keyring-backed/non-release-blocking |
| desktop installed-profile SQLCipher/keyring smoke | exit `0`; first launch migrates a seeded plaintext DB to SQLCipher, creates an isolated platform keyring key, and ordinary `sqlite3` cannot read the encrypted DB; second launch reopens the same DB via keyring without `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX`; report written to `docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` with `mode=desktop_installed_profile_smoke`, `status=passed`, `release_evidence_complete=false`, `keyringRoundTrip=true`, `encryptedReopen=true`, `plaintextBackupPresent=true`, `plaintextOpenBlocked=true` |
| cross-device continuation code smoke | exit `0`; backend `SyncService` verifies desktop push -> web/mobile pull -> uni-mobile reply -> desktop incremental pull without duplicate/lost rows; frontend desktop sync adapter and uni-app sync client contracts pass; report written to `docs/release/evidence/artifacts/cross-device-continuation-code-smoke-20260509.json` with `release_evidence_complete=false` |

This is useful code-level, local installed-profile, debug bundle runtime/UI, unsigned release packaged-runtime, unsigned release packaged-profile/performance, Rust IPC fallback sync, packaged-binary sync loopback, and cross-device continuation rehearsal evidence. The 2026-05-09 local rerun fixed the debug smoke script's macOS `mktemp` portability issue and proves the debug `.app` can self-test, start, and complete a WebView page-load handshake. The unsigned release app+DMG build proves the release `.app` can be produced without signing when `hdiutil` / DiskManagement is available, and the unsigned release packaged runtime/profile paths can self-test, start, complete a WebView page-load handshake, migrate plaintext SQLite to SQLCipher, reopen via platform keyring, satisfy the SQLCipher 100/500 performance threshold, and exercise a local loopback backend push/pull/conflict/retry flow from the packaged binary. The release package dry-run/preflight and unsigned release preflight still verify the production APNs entitlement and the remaining signing/notarization/signature gaps. This file remains `Status: pending` because it does not yet prove a working signed/notarized packaged runtime, signed packaged-profile migration, signed packaged-runtime performance, shared-staging backend sync, or a signed/shared-staging cross-device continuation transcript.

## Completion Notes

- Record OS version, app bundle/build hash, and backend environment.
- Store screenshots or logs with secrets redacted.
- Link to the packaged runtime smoke transcript.
