# TASK-11b Sync Engine — Followups

## Remaining P0

- Add a real Tauri runtime smoke that opens `sqlcipher:anxin_local.db`, seeds `sync_log`, runs `triggerSync()`, and verifies local writeback against a test backend. The injected SQLite Vitest smoke now covers the orchestrator logic, but it is not a packaged Tauri proof.
- Keep Rust SQLCipher as the long-term owner of desktop local DB access. Do not reintroduce frontend `tauri-plugin-sql` writes or maintain two divergent sync implementations.
- Add runtime coverage for `/sync-conflicts` merge editing and keep-local/keep-remote paths inside the packaged Tauri app.
- Add runtime coverage for failed-task retry/backoff and `needs_human`; code-level scheduling exists, but it has not been proven inside a packaged Tauri runtime.
- Produce signed/notarized packaged-profile evidence for SQLCipher/keyring migration. Code-level and local installed-profile smoke are now in place, but they are not a signed installer proof.
- Add desktop runtime tests for push/pull/conflict/retry; Rust `cargo check`, frontend helper tests, and injected SQLite orchestrator tests are not enough for commercial release.
- Add packaged-runtime performance baselines: 100 push records P95 < 2s; 500 pull records P95 < 3s.

## Release Risk

Backend sync is now durable, and the desktop frontend path can read/write local SQLCipher through Rust secure commands with injected code-level push/pull/retry tests; however, there is not yet a real packaged Tauri UI smoke, signed/notarized packaged-profile migration proof, packaged-runtime performance baseline, or mobile continuation verification. Do not claim commercial cross-device continuation until those are verified end to end.
