# Desktop Sync Engine Runbook

> 日期：2026-05-06
> 状态：backend log available; Rust SQLCipher local profile smoke, Rust IPC fallback sync code path, and packaged-binary sync code smoke available; packaged real-backend UI runtime still pending.

## Inspect Backend Sync Logs

Check recent versions for a user:

```sql
SELECT user_id, device_id, entity_type, entity_id, action, version, created_at
FROM sync_log
WHERE user_id = :user_id
ORDER BY version DESC
LIMIT 50;
```

Check device activity:

```sql
SELECT device_id, COUNT(*) AS records, MAX(created_at) AS last_seen
FROM sync_log
WHERE user_id = :user_id
GROUP BY device_id;
```

## Common Incidents

### Client Push Accepted But Other Device Cannot See Data

1. Confirm source record exists in backend `sync_log`.
2. Confirm target client uses the same `user_id`.
3. Confirm target client's `since_version` is lower than the record version.
4. Confirm desktop pull writeback is implemented for that `entity_type`.

### Conflict Returned

1. Inspect returned `conflicts`.
2. If user chooses local, push a new update with latest `last_sync_version`.
3. If user chooses remote, mark local task synced without writing.
4. If user merges, call `/api/v1/sync/resolve`.

### Reset Local Sync Cursor

Desktop should set `app_settings['sync.last_server_version']=0` and pull again. Do not delete backend `sync_log` unless this is a test environment.

## Rust IPC Fallback Sync

The frontend bridge remains the primary desktop sync path. If it is unavailable, `trigger_sync` in `desktop/src/commands/sync.rs` now runs the same SQLCipher-backed data plane:

1. Read retryable `sync_log` rows from local SQLCipher.
2. Hydrate payloads from local entity tables when `data_json` is empty.
3. Push to `/api/v1/sync/push` with `sync.device_id` and `sync.last_server_version`.
4. Mark accepted rows synced, conflict rows `needs_human=1`, and transport failures into bounded retry state.
5. Pull `/api/v1/sync/pull`, apply supported entity types locally, and advance `sync.last_server_version`.

Current evidence is code-level (`cd desktop && cargo test sync`). Signed packaged runtime push/pull/conflict/retry evidence is still required before release.

## Local SQLCipher/Keyring Smoke

Before collecting packaged evidence, run the local installed-profile smoke:

```bash
bash scripts/desktop-installed-profile-smoke.sh --out /tmp/anxin-desktop-installed-profile-smoke.json
```

The smoke uses an isolated keyring service/user, migrates a seeded plaintext DB to SQLCipher, reopens it on a second launch without `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX`, and confirms ordinary `sqlite3` cannot read the encrypted DB.

## Release Metrics

- push success rate
- pull latency P95
- conflicts per 1000 records
- failed/needs_human queue size
- records rejected by auth/user isolation
