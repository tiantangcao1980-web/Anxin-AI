# Desktop Runtime Smoke Evidence

Status: pending
Owner: Desktop release owner TBD
Environment: Rust SQLCipher/keyring security gate complete; local installed-profile keyring reopen smoke complete; debug binary runtime smoke complete; debug macOS app bundle self-test complete; fresh local debug bundle runtime startup smoke currently fails before page-load evidence; unsigned release app+DMG build complete in unsandboxed macOS environment; unsigned release packaged runtime self-test/startup/WebView page-load smoke complete; unsigned release packaged-profile SQLCipher/keyring migration and SQLCipher 100/500 performance smoke complete; cross-device continuation code-level rehearsal complete; release package dry-run/preflight complete with hdiutil/DiskManagement probe; signed/notarized packaged release evidence pending
Date range: 2026-05-06 to 2026-05-09 local collection

> This is runtime evidence, not a substitute for `cargo check`, Vitest, or Tauri debug build. Do not mark complete until a packaged desktop app has exercised local SQLCipher, keyring reopen, and sync behavior end to end.

## Required Scope

| Area | Required evidence | Status | Artifact reference |
|---|---|---|---|
| SQLCipher migration | Packaged app opens `sqlcipher:anxin_local.db` and applies migration 1 | code-level pass; SQLite SQL smoke pass; SQLCipher service migration tests pass; local installed-profile plaintext migration smoke pass; unsigned release packaged-profile plaintext migration smoke pass; legacy `sync_log` startup compatibility pass; debug binary self-test/runtime smoke pass; debug `.app` bundle binary self-test pass; debug `.app` runtime startup/UI load currently blocked by bundle launch failure; signed/notarized packaged evidence pending | `bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` -> release binary plaintext-to-SQLCipher migration/keyring reopen pass; `bash scripts/desktop-runtime-smoke.sh --with-app-bundle --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507-local.log` currently fails after bundle self-test with `Abort trap: 6`; latest crash report: `~/Library/Logs/DiagnosticReports/anxin-legal-desktop-2026-05-07-201228.ips`; `bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507-local.json`; `bash scripts/desktop-sqlite-security-gate.sh` -> exit `0` |
| Push | Seed local `sync_log` pending row, run sync, verify backend receives row | code-level pass; packaged runtime pending | `frontend api-adapter.sync.test.ts`: included in `12 passed` |
| Pull | Backend exposes remote update, run sync, verify local SQLite writeback | code-level pass; packaged runtime pending | `frontend api-adapter.sync.test.ts`: included in `12 passed` |
| Conflict | Seed conflicting row, verify conflict UI lists it | code-level pass; packaged runtime pending | `frontend sync-conflict-utils.test.ts`: included in `12 passed` |
| Conflict resolution | Keep-local, keep-remote, and merge paths update local/remote state correctly | code-level pass; packaged runtime pending | `frontend sync-conflict-utils.test.ts`: included in `12 passed` |
| Retry/backoff | Failed row increments `retry_count`, sets `next_retry_at`, and avoids immediate retry | code-level pass; packaged runtime pending | `frontend api-adapter.sync.test.ts`: included in `12 passed` |
| Human intervention | Exhausted retry marks `needs_human` and surfaces a user-visible state | code-level pass; packaged runtime pending | `frontend api-adapter.sync.test.ts`: included in `12 passed` |
| Encryption | Local database cannot expose messages/documents/contracts/cases as plaintext | code-level SQLCipher pass; local installed-profile plaintext-read rejection pass; unsigned release packaged-profile plaintext-read rejection pass; signed/notarized packaged evidence pending | `desktop-release-profile-unsigned-smoke-20260508.json` and `desktop-installed-profile-smoke-20260507.json` both report `plaintextOpenBlocked=true` |
| Keyring | App restarts and reopens encrypted DB through platform key store | local installed-profile keyring reopen pass; unsigned release packaged-profile keyring reopen pass; signed/notarized packaged evidence pending | release packaged-profile smoke and installed-profile smoke both run twice with an isolated real keyring service/user; reports have `keyringRoundTrip=true` and `encryptedReopen=true` on both launches |
| Performance | 100 push records P95 < 2s and 500 pull records P95 < 3s | code-level SQLite/SQLCipher path pass; unsigned release packaged SQLCipher performance pass; signed/notarized packaged runtime performance pending | `desktop-release-profile-unsigned-smoke-20260508.json` -> 100 push rows P95 `3.5ms`, 500 pull rows P95 `1.8ms`; `bash scripts/desktop-runtime-smoke.sh --with-app-bundle --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507-local.log` -> code-level 100 push rows P95 `25.0ms`, 500 pull rows P95 `15.9ms` before debug bundle runtime startup aborts |
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
  --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507-local.json \
  --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507-local.log
```

Result collected on 2026-05-07:

| Check | Result |
|---|---|
| frontend desktop sync Vitest slice | `2 files / 12 tests passed` |
| desktop cargo test | `16 passed` |
| desktop cargo check | exit `0` |
| desktop SQLite migration SQL smoke | exit `0`; migration applies to a fresh temp SQLite DB, 8 required local/sync tables exist, `sync_log` retry row round-trips, legacy six-column `sync_log` startup path is preserved, frontend repair SQL fills `next_retry_at`/`needs_human`, `PRAGMA integrity_check` returns `ok` |
| desktop SQLite 100/500 sync performance smoke | exit `0`; 5-sample P95: 100 pending push rows `25.0ms`, 500 local pull writebacks `15.9ms` |
| desktop runtime code smoke JSON artifact | not written on fresh local run because the script exits non-zero once the bundle runtime startup smoke aborts |
| desktop runtime UI smoke log artifact | failure log copied to `docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507-local.log`; no WebView page-load evidence was emitted before abort |
| desktop Tauri debug `.app` bundle build | exit `0`; built `desktop/target/debug/bundle/macos/安心法务.app` with `--debug --ci --bundles app --no-sign` |
| desktop debug `.app` bundle binary self-test | exit `0`; validates `sqlcipher:anxin_local.db`, migration `1`, 8 required local/sync tables, retry schema, and `sqlite_security.encrypted=true`, `keyring_backed=true`, `release_blocking=false` |
| desktop debug `.app` runtime startup smoke | exit `134`; bundle binary prints `desktop runtime smoke starting: exit_after_ms=1500` and aborts during AppKit registration (`Abort trap: 6`); crash report captured at `~/Library/Logs/DiagnosticReports/anxin-legal-desktop-2026-05-07-201228.ips` |
| desktop debug `.app` WebView page-load smoke | not reached on fresh local run because bundle runtime startup aborts first |
| desktop Rust IPC offline/sync status guard | exit `0`; `submit_offline_task`, `get_queue_stats`, `flush_offline_queue`, `trigger_sync`, `get_sync_status`, and `get_pending_sync_count` now read local queue/sync tables and return explicit blocked/deferred/conflict counts instead of reporting empty-payload success |
| desktop release package dry-run | exit `0`; redacted artifact reports `hdiutil` / DiskManagement probe pass, unsigned release `.app` and DMG exist, and remaining blockers are Developer ID signing identity, notarization credentials, Tauri signing identity, keychain codesign identity, code-sign verification, and signature authority | `docs/release/evidence/artifacts/desktop-release-package-dry-run-20260507.json` |
| desktop signed/notarized release preflight | exit `0`; redacted artifact reports `release_ready=false` with blockers `tauri.signing_identity`, `codesign.identities`, `notary.credentials`, `release.app.codesign_verify`, `release.app.signature_authority`; `command.hdiutil=pass`, `dmg.hdiutil_create_probe=pass`, `release.app.exists=pass`, `release.dmg.exists=pass`, and `tauri.entitlements.aps_environment=pass`; supporting debug `.app`, runtime transcript, and installed-profile report are present | `docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` |
| desktop unsigned release app+DMG build | exit `0` in unsandboxed macOS environment; unsigned release `.app` and `desktop/target/release/bundle/dmg/安心法务_1.0.0_aarch64.dmg` were built; earlier sandbox failure is attributed to blocked `hdiutil` / DiskManagement access, not product packaging logic | `docs/release/evidence/artifacts/desktop-release-unsigned-local-build-20260507.json` |
| desktop unsigned release `.app`/DMG preflight | exit `0`; release `.app` and DMG exist, but `release_ready=false` remains blocked by missing signing identity, codesign identity, notarization credentials, code-sign verification, and signature authority | `docs/release/evidence/artifacts/desktop-release-preflight-unsigned-20260507.json` |
| desktop unsigned release packaged runtime smoke | exit `0`; release bundle binary self-test validates 8 local/sync tables plus SQLCipher/keyring security, runtime startup exits cleanly, and WebView page-load handshake returns `pageLoadFinished=true`, `webviewLabel=main`, `url=tauri://localhost`; artifact has `signed_or_notarized=false` and `release_evidence_complete=false` | `docs/release/evidence/artifacts/desktop-release-runtime-unsigned-smoke-20260507.json`; UI transcript `docs/release/evidence/artifacts/desktop-release-runtime-ui-smoke-unsigned-20260507.log` |
| desktop unsigned release packaged-profile/performance smoke | exit `0` in unsandboxed macOS Keychain context; release bundle binary migrates a seeded plaintext profile DB to SQLCipher, creates an isolated real keyring key, reopens without `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX`, ordinary `sqlite3` cannot read the encrypted DB, and SQLCipher 100 push / 500 pull performance passes with P95 `3.5ms` / `1.8ms`; artifact has `signed_or_notarized=false` and `release_evidence_complete=false` | `docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` |
| desktop SQLite security gate | exit `0`; confirms Rust SQLCipher/keyring dependencies are present, frontend `@tauri-apps/plugin-sql` package is absent, stale Tauri SQL capability is removed, and Rust self-test reports encrypted/keyring-backed/non-release-blocking |
| desktop installed-profile SQLCipher/keyring smoke | exit `0`; first launch migrates a seeded plaintext DB to SQLCipher, creates an isolated platform keyring key, and ordinary `sqlite3` cannot read the encrypted DB; second launch reopens the same DB via keyring without `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX`; report written to `docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` with `mode=desktop_installed_profile_smoke`, `status=passed`, `release_evidence_complete=false`, `keyringRoundTrip=true`, `encryptedReopen=true`, `plaintextBackupPresent=true`, `plaintextOpenBlocked=true` |
| cross-device continuation code smoke | exit `0`; backend `SyncService` verifies desktop push -> web/mobile pull -> uni-mobile reply -> desktop incremental pull without duplicate/lost rows; frontend desktop sync adapter and uni-app sync client contracts pass; report written to `docs/release/evidence/artifacts/cross-device-continuation-code-smoke-20260509.json` with `release_evidence_complete=false` |

This is useful code-level, local installed-profile, unsigned release packaged-runtime, unsigned release packaged-profile/performance, and cross-device continuation rehearsal evidence, but the fresh local unsigned debug `.app` bundle runtime smoke no longer qualifies as passing evidence because startup aborts before page-load. The unsigned release app+DMG build now proves the release `.app` and DMG can be produced without signing when `hdiutil` / DiskManagement is available, and the unsigned release packaged runtime/profile paths can self-test, start, complete a WebView page-load handshake, migrate plaintext SQLite to SQLCipher, reopen via platform keyring, and satisfy the SQLCipher 100/500 performance threshold. The release package dry-run/preflight and unsigned release preflight still verify the production APNs entitlement and the remaining signing/notarization/signature gaps. This file remains `Status: pending` because it does not yet prove a working signed/notarized packaged runtime, signed packaged-profile migration, signed packaged-runtime performance, or a signed/shared-staging cross-device continuation transcript.

## Completion Notes

- Record OS version, app bundle/build hash, and backend environment.
- Store screenshots or logs with secrets redacted.
- Link to the packaged runtime smoke transcript.
