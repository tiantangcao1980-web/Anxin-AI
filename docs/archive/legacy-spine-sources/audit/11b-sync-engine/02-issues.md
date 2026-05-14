# TASK-11b Sync Engine — Issues

| ID | Severity | Issue | Status |
|---|---|---|---|
| SYNC-001 | P0 | Desktop push body does not read SQLite pending records | Closed for code path and unsigned packaged loopback; shared-staging/signed runtime evidence open |
| SYNC-002 | P0 | Desktop pull response is not written to local SQLite tables | Closed for code path and unsigned packaged loopback; shared-staging/signed runtime evidence open |
| SYNC-003 | P0 | Backend sync log was process memory only | Closed for backend |
| SYNC-004 | P0 | Sync conflicts are not persisted/displayed on desktop | Code-level page/merge UI closed; unsigned packaged conflict-row smoke closed; interactive UI evidence open |
| SYNC-005 | P0 | Failed desktop sync tasks have no exponential retry loop | Code-level backoff + injected SQLite retry test + unsigned packaged retry-to-human smoke closed; shared-staging/human UI transcript open |
| SYNC-006 | P0 | Local SQLite is not sqlcipher/keyring backed | Unsigned packaged-profile proof closed; signed/notarized packaged-profile proof open |
| SYNC-007 | P0 | Real push/pull performance baselines are missing | Local and unsigned packaged SQLCipher baseline closed; signed packaged runtime baseline open |

## Closed Details

SYNC-003 is fixed by `SyncLog`, migration `038_add_sync_log`, and `SyncService(db)` using append-only per-user versions. Existing API tests and new service tests verify user-scoped push/pull, incremental pull, conflict reporting for stale versions, and session-scoped artifacts.

SYNC-001/SYNC-002 are now fixed locally in both code-level and unsigned packaged-binary evidence. `frontend/src/lib/api-adapter.ts` reads local `sync_log` rows via Rust secure SQLCipher commands, hydrates payloads from local tables, posts `/sync/push`, writes `/sync/pull` records back to SQLCipher, and advances `sync.last_server_version`. `runLocalSyncWithDependencies()` gives tests the same orchestration path with injected SQLite/API dependencies, and `api-adapter.sync.test.ts` verifies push body construction, accepted-row marking, remote document writeback, and version advancement. `desktop/src/commands/sync.rs` no longer sends empty records or reports fake success when this frontend SQLite path is unavailable. `desktop/src/services/sync_engine.rs` and `--sync-loopback-smoke` prove the unsigned release `.app` binary can push two retryable records with bearer auth to a local HTTP backend, persist one conflict, write one pulled document, and advance the cursor to `13`.

SYNC-004/SYNC-005 remain release blockers only for the interactive/shared-staging evidence layer. Conflicts are persisted and now have bridge-level `listLocalSyncConflicts` / `resolveLocalSyncConflict`, a minimal `SyncStatus` conflict dialog, a dedicated `/sync-conflicts` merge page, and failed rows now get bounded exponential `next_retry_at` scheduling plus `needs_human`. The unsigned packaged-binary smoke proves conflict-row persistence and retry-to-human handling, but there is still no real packaged Tauri UI transcript for human conflict resolution or a shared-staging retry/backoff transcript.

SYNC-006 now has code-level, local installed-profile, and unsigned release packaged-profile evidence. `getDesktopSQLiteSecurityStatus()` reports Rust-owned `rusqlite/sqlcipher`, encrypted/keyring-backed/non-release-blocking storage; `scripts/desktop-sqlite-security-gate.sh` verifies the dependency/capability/package contract; `scripts/desktop-installed-profile-smoke.sh` proves plaintext-to-SQLCipher migration, isolated keyring round-trip, second-launch reopen without an explicit DB key, and ordinary sqlite3 plaintext-read rejection; `scripts/desktop-release-profile-smoke.sh` proves the same class of behavior through the unsigned release `.app` binary with SQLCipher 100/500 performance checks. The remaining gap is packaged-profile proof from a signed/notarized build.
