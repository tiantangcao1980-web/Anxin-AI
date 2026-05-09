# TASK-11b Sync Engine — Followups

## Remaining P0

- Add a real interactive Tauri UI runtime smoke that opens `sqlcipher:anxin_local.db`, seeds conflict and retry rows, runs the visible sync workflow, and verifies conflict/human-intervention states through the UI. The injected SQLite Vitest smoke and unsigned packaged-binary loopback smoke now cover the data path, but they do not prove the interactive UI workflow.
- Keep Rust SQLCipher as the long-term owner of desktop local DB access. Do not reintroduce frontend `tauri-plugin-sql` writes or maintain two divergent sync implementations.
- Add runtime coverage for `/sync-conflicts` merge editing and keep-local/keep-remote paths inside the packaged Tauri app.
- Add shared-staging runtime coverage for failed-task retry/backoff and `needs_human`; code-level scheduling and unsigned packaged-binary retry-to-human evidence exist, but a real backend transcript is still missing.
- Produce signed/notarized packaged-profile evidence for SQLCipher/keyring migration. Code-level, local installed-profile, and unsigned release packaged-profile smoke are now in place, but they are not a signed installer proof.
- Add shared-staging desktop runtime tests for push/pull/conflict/retry; Rust `cargo check`, frontend helper tests, injected SQLite orchestrator tests, and unsigned packaged-binary loopback smoke are strong local evidence but not a production-like backend transcript.
- Add signed packaged-runtime performance baselines: 100 push records P95 < 2s; 500 pull records P95 < 3s.

## Release Risk

Backend sync is now durable, and the desktop path can read/write local SQLCipher through Rust secure commands with injected code-level push/pull/retry tests plus unsigned packaged-binary loopback evidence; however, there is not yet a real interactive packaged Tauri UI conflict/human-intervention transcript, signed/notarized packaged-profile migration proof, signed packaged-runtime performance baseline, shared-staging backend transcript, or mobile continuation verification. Do not claim commercial cross-device continuation until those are verified end to end.
