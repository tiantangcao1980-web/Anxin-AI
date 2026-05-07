# TASK-11b Sync Engine — Test Additions

## New Tests

`backend/tests/test_sync_log_service.py`

- `test_sync_push_persists_log_and_pull_returns_incremental` proves pushed records are persisted in `sync_log` and can be pulled by version.
- `test_sync_pull_is_user_scoped` proves two users receive only their own sync records.
- `test_sync_push_reports_conflict_for_stale_entity_version` proves stale client versions are rejected with conflict data.
- `test_sync_artifacts_are_session_scoped` proves harness artifacts are scoped by session id.

Existing:

- `backend/tests/test_sync_api_security.py` continues to prove authenticated API push/pull/status/full-sync and cross-user isolation.
- `backend/tests/test_auth_surface_hardening.py` includes sync auth-surface coverage.

`frontend/src/lib/api-adapter.sync.test.ts`

- `normalizes backend roots to the sync API base` proves desktop backend roots are converted to `/api/v1` before calling `/sync/*`.
- `builds the backend push payload without leaking local sync_log ids` proves local SQLite log ids are not sent to the backend contract.
- `normalizes remote records defensively for local application` proves malformed remote `data` does not crash local writeback.
- `maps conflict choices to backend resolve payloads` proves keep-local is sent as backend merge with local data, keep-remote does not mutate backend, and explicit merge carries merged data.
- `schedules failed sync rows with exponential backoff before human handoff` proves retry attempts produce bounded exponential delays and switch to human handling at the retry ceiling.
- `treats missing or expired retry timestamps as due` proves retry scheduling handles legacy/malformed timestamps safely.
- `runs a local push and pull cycle against injected desktop SQLite dependencies` proves the desktop sync orchestrator pushes pending rows, marks accepted local rows synced, pulls remote records, writes local SQLite tables, and advances the durable server-version cursor.
- `marks failed push rows for bounded retry before the next sync attempt` proves failed pushes are persisted as deferred retry work with `retry_count`, `next_retry_at`, and no false successful sync timestamp.
- `reports the current desktop SQLite encryption contract as release-ready` proves the code reports Rust-owned SQLCipher/keyring as encrypted, keyring-backed, and non-release-blocking.

`frontend/src/lib/sync-conflict-utils.test.ts`

- `formats conflict data as stable pretty JSON` proves conflict payloads render predictably for review.
- `builds a local-priority merge draft over remote data` proves the merge editor starts from a deterministic combined payload.
- `accepts only JSON objects for manual merge payloads` proves arrays and malformed JSON are rejected before submit.

`desktop/src/services/local_db.rs`

- `build_init_sql_contains_sync_tables` proves the embedded migration SQL contains the desktop sync/offline queue tables, retry fields, and sync version columns.
- `sqlite_migrations_register_initial_schema` proves `sqlcipher:anxin_local.db` has one registered schema migration with the expected version, description, and `sync_log` table.

`desktop/src/services/secure_db.rs`

- `security_contract_is_release_ready_when_secure_db_is_owner` proves the Rust secure DB contract is encrypted, keyring-backed, and not release-blocking.
- `migrates_plaintext_sqlite_to_sqlcipher` proves a plaintext SQLite profile can be exported into SQLCipher and reopened with the configured key.

`scripts/desktop-installed-profile-smoke.sh`

- Builds the debug binary, seeds a plaintext local profile DB, runs a first launch to migrate to SQLCipher and create an isolated real keyring entry, runs a second launch without `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX`, and confirms ordinary `sqlite3` cannot read the encrypted DB.

## Verification

```bash
cd backend && ./.venv/bin/pytest -q tests/test_sync_log_service.py tests/test_sync_api_security.py tests/test_auth_surface_hardening.py -k 'sync'
# 24 passed, 6 warnings

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/models/sync.py src/services/sync_service.py src/api/routes/sync.py tests/test_sync_log_service.py tests/test_sync_api_security.py alembic/versions/038_add_sync_log.py
# All checks passed

cd frontend && npm run test -- api-adapter.sync.test.ts
# 1 file / 9 tests passed

cd frontend && npm run test -- sync-conflict-utils.test.ts api-adapter.sync.test.ts
# 2 files / 12 tests passed

cd frontend && npm run test
# 10 files / 34 tests passed

cd frontend && npx tsc --noEmit
# passed

cd frontend && npm run lint
# passed

cd desktop && cargo check
# passed

cd desktop && cargo test
# 8 passed

cd desktop && cargo tauri build --debug --no-bundle --ci
# built desktop/target/debug/anxin-legal-desktop

bash scripts/desktop-installed-profile-smoke.sh --out /tmp/anxin-desktop-installed-profile-smoke.json
# installed-profile smoke ok: migrated=true, keyring=true, encryptedReopen=true

rustfmt --edition 2021 --check desktop/src/lib.rs desktop/src/services/local_db.rs
# passed
```
