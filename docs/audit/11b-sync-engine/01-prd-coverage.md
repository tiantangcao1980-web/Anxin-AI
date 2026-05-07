# TASK-11b Sync Engine — PRD Coverage

| Requirement | Current Status | Evidence |
|---|---|---|
| P0-1 desktop offline queue schema | Code-level closed; packaged UI runtime smoke open | `desktop/migrations/001_offline_queue.sql` defines `offline_tasks`, `sync_log`, `local_artifacts`, local business tables, settings, and indexes; `desktop/src/services/local_db.rs::sqlite_migrations()` exposes the schema contract for `sqlcipher:anxin_local.db`; `desktop/src/services/secure_db.rs` applies it through Rust-owned SQLCipher; `scripts/desktop-runtime-smoke.sh` and `scripts/desktop-installed-profile-smoke.sh` cover migration code paths; packaged UI runtime migration smoke still missing |
| P0-2 desktop push reads pending SQLite rows | Code-level closed; runtime smoke open | `frontend/src/lib/api-adapter.ts::runLocalSyncWithDependencies` / `triggerLocalSync` read pending/failed `sync_log` rows and post `/sync/push`; `api-adapter.sync.test.ts` now runs an injected SQLite + mocked backend push cycle; packaged Tauri smoke still missing |
| P0-3 desktop pull writes local SQLite tables | Code-level closed; runtime smoke open | `runLocalSyncWithDependencies` / `triggerLocalSync` pull `/sync/pull`, write messages/documents/conversations/cases/contracts/settings/artifacts locally, and advance `sync.last_server_version`; injected SQLite + mocked backend pull test now verifies local writeback; packaged Tauri smoke still missing |
| P0-4 conflict resolver and conflicts table | Partial | conflict rows are persisted as `sync_log.status='conflict'`; `/sync-conflicts` provides keep-local/keep-remote/merge editing; real Tauri runtime smoke still missing |
| P0-5 backend device/user/version incremental sync | Partial closed | `backend/src/models/sync.py`, `backend/src/services/sync_service.py`, `backend/alembic/versions/038_add_sync_log.py`, `tests/test_sync_log_service.py` |
| P0-6 retry loop | Code-level closed; runtime smoke open | failed rows write `retry_count`, `next_retry_at`, and `needs_human`; injected SQLite test verifies failed push rows are deferred for retry; packaged Tauri runtime smoke is still missing |
| P0-7 sqlcipher/keyring | Code-level closed; packaged-profile proof open | Rust-owned SQLCipher/keyring path is implemented in `desktop/src/services/secure_db.rs`; `getDesktopSQLiteSecurityStatus()` reports encrypted/keyring-backed/non-release-blocking; `scripts/desktop-sqlite-security-gate.sh` passes; `scripts/desktop-installed-profile-smoke.sh` proves local plaintext migration, keyring round-trip, second-launch reopen, and ordinary sqlite3 plaintext-read rejection |

## Product Impact

- Cross-device continuation is still blocked by missing packaged Tauri UI runtime smoke, signed/notarized packaged-profile migration proof, and mobile continuation verification.
- Backend now has a durable sync target, and desktop has a Rust SQLCipher path with injected code-level push/pull/retry tests instead of an empty push/pull command.
