# TASK-05 Contract/E-sign — Followups

## Remaining P0

- P0-2-sandbox: run official e签宝 and 法大大 provider clients against real merchant sandbox accounts for 7 days, retaining request/response logs, signed-document download evidence, and cancellation/status-query evidence.
- P0-3-sandbox: export/confirm the current account's subscribed e签宝/法大大 event catalogue, replay each event variant through sandbox callbacks, and compare provider payloads with the local mapping table.
- Rollout: keep `ESIGN_PROVIDER=mock` by default until per-channel rollout reaches sandbox 7 days -> 1% -> 10% -> 50% -> 100% with rollback checkpoints.

## Release Risks

- The new state machine intentionally rejects `draft -> signed`; existing tests and provider writeback now set contracts to `approved` before signed completion. Any legacy integration that sent signed callbacks for draft contracts must be migrated.
- Contract rollback intentionally creates a new draft version instead of rewriting historical versions. Approved/signed/active/expired/terminated contracts must go through an explicit legal workflow before any rollback-like remediation.
- `CONTRACT_REVIEW_LOCK_BACKEND=auto` and `WEBHOOK_PROCESSING_LOCK_BACKEND=auto` use local locks outside production/staging. Production must keep Redis healthy or explicitly set `redis` to fail closed during rollout.
- `review_failed` is application-level status stored as string through `ValueEnum`; no native PostgreSQL enum migration was required, but downstream dashboards should learn this status before launch.
- Verified e-sign webhook transitions now write audit logs, but archive storage and provider-side certificate package retention still need real sandbox/prod evidence before commercial launch.
- 法大大 public SDK/source evidence was enough for code-level FASC V5.1 implementation, but the merchant backend must confirm endpoint availability, event names, and account-specific path/version switches before production.
- Contract attachment download now supports both authenticated streaming and object-storage download URLs. Production MinIO rollout must verify URL expiry, bucket policy, and CDN/proxy behavior with real credentials before opening external sharing.
- No database enum migration was required in this pass because `ContractStatus` already existed; future enum changes still need explicit Alembic handling and PostgreSQL rollback planning.

## Memory

- `feature-1778041562837`: Contract Lifecycle State Machine.
- `feature-1778043201056`: Contract Version Diff and Rollback.
- `feature-1778043952565`: Contract Review Timeout and Webhook Processing Lock.
- Project memory note: Contract Attachment Object Storage Lifecycle.
- Project memory note: Official E-sign Provider Clients and FASC Webhook Writeback (`noteCount: 16`).
