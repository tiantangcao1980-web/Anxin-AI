# Desktop Sync Engine Runbook

> 日期：2026-05-06
> 状态：backend log available; Rust SQLCipher local profile smoke available; packaged UI runtime still pending.

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

Desktop should set `sync_state.last_sync_version=0` and pull again. Do not delete backend `sync_log` unless this is a test environment.

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
