# TASK-05 Contract/E-sign — Issues

| ID | Severity | Issue | Status |
|---|---|---|---|
| CON-001 | P0 | Contract status could be changed directly by services without a legal transition matrix | Closed |
| CON-002 | P0 | E-sign webhook writeback could bypass lifecycle rules | Closed for state enforcement; official provider/event mapping still open |
| CON-003 | P0 | API had no explicit transition contract for illegal status moves | Closed |
| CON-004 | P0 | Version diff and rollback are missing, and rollback must respect terminal states | Closed |
| CON-005 | P0 | Review concurrency lacks distributed lock and 90s timeout semantics | Closed |
| CON-006 | P0 | Contract attachments lack object-storage-backed upload/download/delete lifecycle | Closed |
| CON-007 | P0 | e签宝/法大大 provider APIs are not fully implemented against official protocols | Closed for code-level clients |
| CON-008 | P0 | Real merchant sandbox, provider event catalogue, and staged rollout evidence are missing | Open |

## Closed Details

CON-001 is fixed by moving lifecycle mutation into `ContractLifecycleStateMachine.transition`.

CON-002 is fixed at the local writeback boundary: webhook status changes now fail if provider events attempt an illegal transition. Provider-level full protocol work remains tracked separately.

CON-003 is fixed by `POST /api/v1/contracts/{contract_id}/transition`, which returns `409` for illegal transitions and preserves the stored status.

CON-004 is fixed by `ContractVersion`, version list/diff/rollback APIs, a front-end version timeline, and rollback through `ContractLifecycleStateMachine`. Rollback from signed/active/expired/terminated style states remains rejected instead of silently reviving legally sensitive contracts.

CON-005 is fixed by `ContractReviewLock`, `CONTRACT_REVIEW_TIMEOUT_SECONDS`, retryable `review_failed`, and `webhook_processing_lock` around webhook idempotency/business writeback. Duplicate review jobs are rejected before the LLM runs; duplicate verified webhook deliveries serialize so business side effects run once.

CON-006 is fixed by `ContractAttachment`, migration `037_add_contract_attachments.py`, org-scoped attachment endpoints, shared upload validation, object-storage put/get/presigned/delete, front-end attachment controls, and audit logs for upload/download/delete.

CON-007 is fixed at the code boundary by `ESignBaoProvider` and `FaDaDaProvider` HTTP clients, env-driven credentials/path settings, official request signing, sign flow creation/start, signer URL retrieval, status query, signed document download, cancellation, and provider-client tests that assert signed headers and payloads.

## Open Details

CON-008 remains open because no real e签宝/法大大 merchant sandbox credentials or account event subscription catalogue are available in this workspace. Commercial rollout still requires 7 days of sandbox callback/request evidence, provider-side event type confirmation, and staged rollout records per channel.
