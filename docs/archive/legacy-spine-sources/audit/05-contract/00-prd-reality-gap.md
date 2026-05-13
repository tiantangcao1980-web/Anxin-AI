# TASK-05 Contract/E-sign — PRD Reality Gap

> Date: 2026-05-06
> Scope: contract lifecycle state machine, contract versioning/diff/rollback, review concurrency/timeout, contract attachment object storage, and e-sign writeback boundary.

## PRD Claim

The commercial-delivery path requires a traceable contract lifecycle: draft, review, risk handling, modification, signing, active execution, expiry, and termination. Once a contract reaches a legal terminal state, later code must not be able to silently move it backward.

## Code Reality Before This Pass

- `ContractStatus` already existed in `backend/src/models/contract.py`.
- `contract_service.review_contract` wrote status fields directly.
- `esign_webhook_service.apply_esign_webhook` wrote signed/terminated status directly from provider payloads.
- No single transition gateway protected terminal states, rollback paths, or invalid shortcuts.
- API consumers had no explicit transition endpoint with 409 semantics for illegal moves.
- Contract review could apply suggestions, but the system did not persist comparable contract versions or expose a rollback path.
- Contract review had no per-contract lock or business timeout; duplicated clicks could run duplicate LLM jobs, and stuck reviews did not land in a retryable failure state.
- Webhook idempotency had durable records, but concurrent duplicate deliveries still needed a short processing lock around the idempotency check and business side effect.
- Contract attachment handling did not have an org-scoped object storage lifecycle. The product could save generated contract text, but arbitrary contract attachments lacked durable upload/list/download/delete records and audit evidence.

## Gap

The enum existed, but the lifecycle contract was not enforced. Any service with a `Contract` model instance could bypass legal sequencing, which made "signed", "expired", and "terminated" states weaker than the business spec requires.

The version story was also incomplete: repeated review/apply cycles could mutate text without a durable version ledger, paragraph-level diff, or state-machine-protected rollback.

The concurrency story was incomplete: the product required one active review per contract round and safe provider retries, but the code only had normal request execution and post-fact webhook dedupe.

The attachment story was incomplete: the object storage service existed for documents and generated contract text, but contract-specific attachment lifecycle paths were still absent.

## Current Result

P0-1, P0-4, P0-5, and P0-6 are now closed at code level:

- `backend/src/services/contract_lifecycle_service.py` owns `LEGAL_TRANSITIONS`, `IllegalStateTransition`, and `ContractLifecycleStateMachine.transition`.
- `backend/src/services/contract_service.py` routes review start/completion and manual transitions through the state machine.
- `backend/src/services/esign_webhook_service.py` routes provider writeback through the same state machine.
- `backend/src/api/routes/contracts.py` exposes `POST /api/v1/contracts/{contract_id}/transition` with 422 for unknown status and 409 for illegal transitions.
- `backend/src/models/contract.py` adds `Contract.version` and `ContractVersion`.
- `backend/src/services/contract_service.py` persists initial/applied/rollback versions, exposes paragraph-level diffs, and routes rollback through `ContractLifecycleStateMachine`.
- `backend/src/api/routes/contracts.py` exposes version list, version diff, and rollback endpoints.
- `frontend/src/pages/ContractReview.tsx` exposes a version timeline, compare action, diff view, and guarded rollback action.
- `backend/src/services/contract_review_lock.py` serializes contract review per contract/version round; production/staging can force Redis, while development/tests use local locks.
- `backend/src/services/contract_service.py` wraps review LLM execution in `asyncio.wait_for`, defaults to 90s, records `review_failed`, and allows retry through the lifecycle matrix.
- `backend/src/services/webhook_idempotency_service.py` exposes `webhook_processing_lock`; `webhook_handler.py` now serializes duplicate webhook deliveries around the durable idempotency record and business writeback.
- `backend/src/models/contract.py` adds `ContractAttachment`; `backend/alembic/versions/037_add_contract_attachments.py` creates the attachment object metadata table.
- `backend/src/services/contract_service.py` uploads attachments through `object_storage_service`, lists by contract/org, reads bytes for authenticated streaming download, creates object-storage download URLs, and deletes object + DB record together.
- `backend/src/api/routes/contracts.py` exposes attachment upload/list/download/download-url/delete endpoints with shared upload validation, organization scope, and audit log double-write for upload/download/delete.
- `frontend/src/pages/ContractReview.tsx` exposes contract attachment upload/download/delete controls in the review workflow.

Remaining gaps stay open for later TASK-05 P0 items: official e签宝/法大大 provider protocols, official provider event variants, and archive/audit double-write for signing/archival events.
