# TASK-11b Sync Engine — Fixes

## Backend Durable Sync Log

Implemented:

- Added `SyncLog` SQLAlchemy model with user/device/entity/action/payload/version/client timestamp fields.
- Added migration `038_add_sync_log.py` with indexes for `(user_id, version)`, `(user_id, entity_type, entity_id)`, and `(user_id, device_id)`.
- Replaced process-local `SyncService` storage with database-backed append-only logs.
- Updated `/api/v1/sync/*` routes to instantiate `SyncService(db)` per request.
- Preserved current API response shape for `push`, `pull`, `status`, `resolve`, `full-sync`, and artifact sync.

## Desktop Tauri SQLite Path

Implemented:

- Extended `frontend/src/lib/api-adapter.ts` local SQLite schema to include `sync_version`, `data_json`, `error_message`, `retry_count`, `offline_tasks`, `local_artifacts`, `local_cases`, and `local_contracts` compatibility tables/columns.
- `saveLocalMessage` and `saveLocalConversation` now write payload-bearing `sync_log` rows instead of entity ids only.
- Added `triggerLocalSync()` to read pending/failed `sync_log` rows, hydrate payloads from local tables, POST `/api/v1/sync/push`, mark accepted rows synced, persist conflict rows, GET `/api/v1/sync/pull`, and apply remote records to local SQLite.
- Added `runLocalSyncWithDependencies()` so the same desktop sync orchestration can be exercised with injected SQLite/API dependencies in Vitest without requiring a packaged Tauri app.
- Added `listLocalSyncConflicts()` and `resolveLocalSyncConflict()` so desktop code can inspect conflict rows and resolve by keeping remote, keeping local via backend merge, or submitting merged data.
- Added `sync.last_server_version`, `sync.last_sync_time`, and `sync.device_id` settings so incremental pull can resume from the last durable server version.
- Added failed-row exponential backoff with `next_retry_at`, `needs_human`, and a bounded retry ceiling so desktop sync does not immediately replay the same failed records forever.
- Added `getDesktopSQLiteSecurityStatus()` as an explicit security contract for the Rust-owned SQLCipher/keyring configuration.
- Added `/sync-conflicts` dedicated conflict-management page with local/cloud JSON comparison, editable merge draft, keep-local, keep-cloud, and submit-merge actions.
- `resolveLocalSyncConflict()` now writes merged data back into local SQLite after backend merge resolution instead of only marking the conflict as synced.
- Documented the encrypted SQLite/keyring strategy in `docs/desktop/sqlite-encryption-strategy.md`.
- Added `desktop/migrations/001_offline_queue.sql` and moved the desktop local database owner to Rust SQLCipher commands, so the desktop schema is applied through `desktop/src/services/secure_db.rs` instead of frontend-owned Tauri SQL writes.
- Aligned Rust `desktop/src/services/local_db.rs` initialization/migration SQL with frontend sync schema for `next_retry_at`, `needs_human`, and `local_conversations.sync_version`; `idx_sync_retry_due` remains in the frontend best-effort repair path so old local `sync_log` tables can start without a missing-column migration panic.
- Fixed `desktop/tauri.conf.json` `beforeBuildCommand` from `cd ../frontend` to `cd frontend` because Tauri CLI executes the command from the repository root in this workspace.
- Updated `frontend/src/lib/tauri-bridge.ts` so `triggerSync()` and `getPendingSyncCount()` prefer the real local SQLite path before Rust IPC fallback.
- Exposed bridge-level `getSyncConflicts()` and `resolveSyncConflict()` for a later conflict-management UI.
- Added a minimal `SyncStatus` conflict dialog that lists conflicts and lets the user keep the cloud or local version.
- Updated `desktop/src/commands/sync.rs` so the fallback no longer sends empty records or reports a false successful sync.
- 2026-05-09: promoted that Rust IPC fallback into a real code-level SQLCipher data path: it reads retryable `sync_log` rows, hydrates entity payloads, creates/persists `sync.device_id`, POSTs `/api/v1/sync/push`, marks accepted rows synced, persists conflicts/needs-human rows, applies `/api/v1/sync/pull` records back to local message/document/conversation/case/contract/setting/harness artifact tables, and updates `sync.last_server_version` / `sync.last_sync_time`.
- Added Rust unit coverage for pending row decoding, push payload construction without leaking local `sync_log.id`, accepted-vs-conflict row selection, and bounded retry-to-human-gate behavior.
- Updated `frontend/src/components/mode-switcher/SyncStatus.tsx` to reflect manual sync success/failure and last sync time in the UI state.
- Added `scripts/desktop-sqlite-security-gate.sh` to keep the SQLCipher/keyring dependency, frontend package removal, stale capability removal, and Rust self-test contract aligned.
- Added `scripts/desktop-installed-profile-smoke.sh` to prove a local plaintext DB can migrate to SQLCipher, round-trip through an isolated real keyring service/user, reopen on a second launch without `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX`, and reject ordinary sqlite3 plaintext reads.

## Code Touchpoints

- `backend/src/models/sync.py`
- `backend/src/models/__init__.py`
- `backend/alembic/versions/038_add_sync_log.py`
- `backend/src/services/sync_service.py`
- `backend/src/api/routes/sync.py`
- `backend/tests/conftest.py`
- `backend/tests/test_sync_log_service.py`
- `backend/tests/test_sync_api_security.py`
- `frontend/src/lib/api-adapter.ts`
- `frontend/src/lib/tauri-bridge.ts`
- `frontend/src/components/mode-switcher/SyncStatus.tsx`
- `frontend/src/lib/api-adapter.sync.test.ts`
- `frontend/src/lib/sync-conflict-utils.ts`
- `frontend/src/lib/sync-conflict-utils.test.ts`
- `frontend/src/pages/SyncConflicts.tsx`
- `frontend/src/App.tsx`
- `docs/desktop/sqlite-encryption-strategy.md`
- `desktop/migrations/001_offline_queue.sql`
- `desktop/src/services/secure_db.rs`
- `desktop/src/commands/secure_db.rs`
- `desktop/src/commands/sync.rs`
- `desktop/src/lib.rs`
- `desktop/src/services/local_db.rs`
- `desktop/src/services/sync_engine.rs`
- `desktop/tauri.conf.json`
- `scripts/desktop-sqlite-security-gate.sh`
- `scripts/desktop-installed-profile-smoke.sh`

## Remaining Work

Unsigned packaged-binary sync loopback now covers a local HTTP backend push/pull/conflict/retry transcript. Real interactive Tauri UI conflict/human-intervention smoke, signed/notarized packaged-profile migration proof, shared-staging backend/cross-device continuation, and signed packaged-runtime performance baselines remain open.
