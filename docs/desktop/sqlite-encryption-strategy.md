# Desktop SQLite Encryption Strategy

> 日期：2026-05-07
> 状态：code-level implementation landed; local installed-profile keyring/reopen smoke passed; release evidence pending for packaged UI interaction, signed packaging, and packaged-profile migration proof.

## Current State

- `desktop/Cargo.toml` now uses `rusqlite` with `bundled-sqlcipher-vendored-openssl`, plus `keyring` and `getrandom`.
- Tauri's official SQL plugin documentation lists SQLite, MySQL, and PostgreSQL as the supported Cargo-feature-selected drivers, with no documented SQLCipher/keyring mode in that plugin surface as of 2026-05-07: <https://v2.tauri.app/plugin/sql/>.
- The frontend sync adapter calls Rust Tauri commands (`secure_sql_execute`, `secure_sql_select`) instead of owning SQLite writes through `@tauri-apps/plugin-sql`.
- `desktop/src/services/secure_db.rs` owns SQLCipher open, platform key retrieval/creation, and plaintext-to-encrypted migration.
- `desktop/src/services/secure_db.rs` keeps the SQLCipher key in an in-process cache after the first successful platform key-store read. This avoids reading macOS Keychain / Windows Credential Manager for every entity query or every SQLCipher connection in the same app run.
- `desktop/src/services/runtime_config.rs` only probes the encrypted `app_settings` mirror when the local DB file already exists, so a fresh first launch does not create a Keychain prompt just to check for optional runtime mode/backend state.
- `secure_db_reset_local_data` exposes the explicit lost-key recovery path: it requires the confirmation phrase `ERASE LOCAL DATA`, deletes the platform keyring item, and removes the DB/WAL/SHM/migration artifacts before the next launch recreates a fresh encrypted profile.
- `frontend/src/lib/api-adapter.ts::getDesktopSQLiteSecurityStatus()` now reports the Rust SQLCipher/keyring contract as encrypted, keyring-backed, and not release-blocking.
- `scripts/desktop-sqlite-security-gate.sh` exits `0` when the Rust dependency, capability, frontend package, and self-test contract stay aligned.
- `scripts/desktop-installed-profile-smoke.sh` exercises an isolated real keyring service/user, plaintext-to-SQLCipher migration, second-launch reopen, and ordinary `sqlite3` plaintext-read rejection.
- Commercial release still requires packaged-profile evidence: packaged UI interaction, signed/notarized packaging, packaged-profile migration transcript, packaged-runtime performance, and cross-device continuation.

## Required Release Design

1. Storage engine: use one SQLite encryption path only.
   - Current implementation: Rust-owned SQLCipher-compatible SQLite layer, exposed through Tauri commands.
   - Do not reintroduce frontend-owned `@tauri-apps/plugin-sql` writes without reworking the security gate and migration ownership.
2. Key custody:
   - macOS: Keychain item scoped to app bundle id.
   - Windows: DPAPI/Credential Manager scoped to current user.
   - Linux: Secret Service/libsecret when available, with explicit unsupported-state messaging otherwise.
3. Key lifecycle:
   - Generate a 256-bit random key on first launch.
   - Store only in the platform secure store.
   - Never write the key to `app_settings`, logs, crash reports, sync payloads, or frontend storage.
   - Support logout without deleting the DB key; support explicit "erase local data" to destroy key + DB.
4. Migration:
   - Existing plaintext DB must be migrated into encrypted DB through a one-time copy.
   - Migration must be transactional: keep plaintext backup until encrypted DB integrity check passes.
   - After success, securely delete or quarantine the plaintext file according to platform capability.

## Acceptance Gates

- Opening `anxin_local.db` with a hex/text viewer must not reveal message, document, contract, case, token, or artifact plaintext.
- App restart can reopen the encrypted DB without user re-login when the platform key store is available.
- Lost key path is explicit: app reports local data cannot be opened and offers reset local data through the guarded Rust command.
- macOS Keychain prompts must be bounded: business entities do not require separate passwords; one SQLCipher profile key unlocks the local DB, and the running process must reuse it instead of prompting on each query.
- `sync_log`, `local_messages`, `local_documents`, `local_cases`, `local_contracts`, `offline_tasks`, and `local_artifacts` are all covered.
- CI or release smoke runs:
  - first-launch key creation
  - restart reopen
  - plaintext-to-encrypted migration
  - corrupted key handling
  - erase-local-data path (`cd desktop && cargo test secure_db` covers the guarded reset helper and artifact cleanup)
- `bash scripts/desktop-sqlite-security-gate.sh` exits `0`.

## Implementation Constraint

Do not silently maintain both frontend-owned `tauri-plugin-sql` writes and Rust-owned SQLCipher writes. Rust is now the SQLite owner; future changes must keep `docs/desktop/sync-engine-design.md`, `scripts/desktop-runtime-smoke.sh`, and `scripts/desktop-sqlite-security-gate.sh` in agreement.

## macOS Keychain Prompt Notes

- The password dialog is the macOS login Keychain asking whether the current executable may read the single SQLCipher DB key named by the `com.anxin.legal.desktop` service. It is not a per-entity password requirement.
- Debug, direct `target/debug/anxin-legal-desktop`, rebuilt unsigned `.app`, and release `.app` binaries can look like different clients to Keychain. That can make macOS ask again after rebuilds or when switching between direct binary and app bundle.
- Signed/notarized release builds should have a stable code identity. After a trusted build is authorized, ordinary entity reads/writes should reuse the process cache and should not keep reopening the Keychain dialog during that app run.
- For repeatable smoke tests, keep using isolated `ANXIN_DESKTOP_KEYRING_SERVICE` values. For purely synthetic unit tests, `ANXIN_DESKTOP_SQLCIPHER_KEY_HEX` remains the explicit bypass so tests do not depend on the user's login Keychain.
