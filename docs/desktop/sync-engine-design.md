# Desktop Sync Engine Design

> 日期：2026-05-06
> 状态：backend durable log implemented; Rust-owned SQLCipher local DB path, frontend bridge sync, and Rust IPC fallback sync are code-level implemented; packaged UI/runtime evidence pending.

## Components

- Desktop local SQLCipher: local messages/documents/cases/contracts, offline tasks, local artifacts, app settings sync cursors, conflicts.
- Desktop schema migration: `desktop/migrations/001_offline_queue.sql` is applied to `sqlcipher:anxin_local.db` by the Rust secure DB service.
- Desktop sync engine primary path: `frontend/src/lib/api-adapter.ts` reads pending local changes through Rust Tauri SQLCipher commands, pushes to `/api/v1/sync/push`, pulls from `/api/v1/sync/pull`, writes local tables, updates `sync.last_server_version`.
- Desktop sync IPC fallback: `desktop/src/commands/sync.rs` now mirrors the same SQLCipher push/pull flow when the frontend bridge path is unavailable. It preserves fail-closed TopSecret/no-token behavior, creates `sync.device_id`, marks HTTP failures into bounded retry/backoff state, persists conflicts as `needs_human`, and applies pulled records for messages, documents, conversations, cases, contracts, settings, harness artifacts, and deletes.
- Retry scheduler: failed push rows get `next_retry_at` using bounded exponential backoff; rows reaching the retry ceiling are marked `needs_human`.
- Backend sync log: append-only `sync_log` table scoped by `user_id`, `device_id`, `entity_type`, `entity_id`, `version`.
- Conflict resolver: backend returns conflicts; desktop stores conflict rows in `sync_log`; `SyncStatus` exposes a compact keep-local/keep-remote path and `/sync-conflicts` provides local/cloud comparison plus editable merge submission.

## Current Backend Schema

`sync_log`:

- `id`
- `user_id`
- `device_id`
- `entity_type`
- `entity_id`
- `action`
- `payload`
- `version`
- `client_version`
- `client_timestamp`
- `created_at`
- `updated_at`

Indexes:

- `user_id, version`
- `user_id, entity_type, entity_id`
- `user_id, device_id`

## Mode Rules

- TopSecret: no data-plane upload.
- Hybrid: upload only records explicitly allowed by privacy policy.
- Cloud: upload all eligible local records.

## Open Design Decisions

- Long-term desktop SQLite owner: Rust secure DB service (`desktop/src/services/secure_db.rs`) owns SQLCipher open, keyring lookup, schema migration, and plaintext-to-encrypted migration.
- SQLCipher/keyring code-level gate and local installed-profile keyring/reopen smoke are implemented; release evidence still needs packaged UI interaction, packaged-profile migration transcript, signed/notarized packaging, packaged-runtime performance, and cross-device continuation.
- Real packaged Tauri smoke for migration application, Rust IPC fallback push/pull/conflict/retry, frontend bridge sync, and merge editing.
