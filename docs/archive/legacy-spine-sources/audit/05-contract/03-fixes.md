# TASK-05 Contract/E-sign — Fixes

## P0-1 Contract State Machine

Implemented:

- Added `LEGAL_TRANSITIONS` for every `ContractStatus` value.
- Added `IllegalStateTransition` for invalid or unsupported status moves.
- Added `ContractLifecycleStateMachine.transition(contract, target_status, actor_id, reason)`.
- Added `ContractService.transition_status` as the service-layer status gateway.
- Updated review start/completion to transition through the gateway.
- Updated e-sign webhook writeback to transition through the gateway.
- Updated e-sign flow creation to reject contracts that have not reached `approved`.
- Added `POST /api/v1/contracts/{contract_id}/transition`.

## Code Touchpoints

- `backend/src/services/contract_lifecycle_service.py`
- `backend/src/services/contract_service.py`
- `backend/src/services/esign_webhook_service.py`
- `backend/src/api/routes/contracts.py`
- `backend/src/api/routes/esign.py`
- `backend/tests/test_contract_state_machine.py`

## Behavior

- Same-status transitions are idempotent.
- Unknown status strings are rejected.
- Illegal transitions leave the model status unchanged.
- Terminal `expired` and `terminated` statuses cannot be revived by the new gateway.
- Draft/unapproved contracts cannot create a signing flow.
- E-sign provider events cannot move a contract into `signed` unless the current local state permits it.

## P0-2 Official E-sign Provider Clients

Implemented:

- Added provider-specific config for e签宝 and 法大大 API base URLs, endpoint paths, app ids, app secrets, and optional 法大大 access token.
- Added e签宝 request signing with `X-Tsign-Open-*`, `Content-MD5`, timestamp freshness inputs, and signed JSON requests.
- Implemented e签宝 create flow, start flow, signer URL retrieval, flow status, signed-document download, and revoke/cancel.
- Added 法大大 FASC V5.1 signing based on sorted request parameters, `bizContent`, timestamp/nonce, derived HMAC key, `X-FASC-*` headers, and `application/x-www-form-urlencoded` bodies.
- Implemented 法大大 access-token retrieval, sign task creation, actor URL retrieval, app detail/status query, owner download URL retrieval, and cancel.
- Added provider config/API exceptions and mapped route errors to 503/502 rather than exposing raw upstream failures.

Additional code touchpoints:

- `backend/src/services/esign_service.py`
- `backend/src/core/config.py`
- `.env.example`
- `backend/.env.example`
- `backend/tests/test_esign_provider_clients.py`

## P0-3 Official E-sign Webhook Writeback

Implemented:

- Kept the existing generic e-sign HMAC fallback for development and legacy tests.
- Added 法大大 FASC webhook verification with `X-FASC-App-Id`, `X-FASC-Sign-Type`, `X-FASC-Sign`, `X-FASC-Timestamp`, `X-FASC-Nonce`, `X-FASC-Event`, and form `bizContent`.
- Updated the e-sign webhook route to parse raw JSON or 法大大 form bodies before handing verified payloads to the unified webhook handler.
- Extended provider event extraction for `signTaskId` / `taskId` / `transReferenceId`, 法大大 event headers, numeric provider statuses, and additional signed/cancelled/in-progress event names.
- Added audit-log double-write for signed and status-change transitions produced by verified e-sign webhooks.

Additional code touchpoints:

- `backend/src/api/routes/esign.py`
- `backend/src/services/official_webhook_security.py`
- `backend/src/services/esign_webhook_service.py`
- `backend/src/models/audit.py`
- `backend/tests/test_external_surface_guards.py`

## P0-4 Contract Version Diff And Rollback

Implemented:

- Added `Contract.version` and `ContractVersion` for a durable contract text ledger.
- Added Alembic migration `036_add_contract_versions.py` with downgrade coverage.
- Added `ContractService.get_contract_versions`, `get_version_diff`, and `rollback_to_version`.
- Updated `apply_suggestions` to append a new version instead of only mutating text.
- Routed rollback through the lifecycle state machine, so terminal or legally sensitive states cannot be silently revived.
- Added API endpoints for version list, paragraph diff, and rollback.
- Added version timeline, compare, diff view, and rollback controls to `ContractReview`.
- Embedded `ContractReview` in the contract management modal so the full review/version workflow is reachable from the management page.

Additional code touchpoints:

- `backend/src/models/contract.py`
- `backend/alembic/versions/036_add_contract_versions.py`
- `backend/tests/test_contract_versions.py`
- `backend/tests/test_contract_version_migration.py`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/Contracts.tsx`
- `frontend/e2e/contract-lifecycle.spec.ts`

## P0-5 Review Concurrency, Timeout, And Webhook Double-Write Guard

Implemented:

- Added `ContractStatus.REVIEW_FAILED` and lifecycle transitions `under_review -> review_failed -> under_review`.
- Added `ContractReviewLock` with Redis support for production/staging and local lock fallback for development/tests.
- Wrapped `ContractService.review_contract` LLM execution with `asyncio.wait_for`; default business timeout is `CONTRACT_REVIEW_TIMEOUT_SECONDS=90`.
- Timeout and execution errors now mark the contract as `review_failed` with retryable summary/result metadata.
- Contract review API returns 409 for duplicate in-flight review, 503 for lock backend failure, and 504 for timeout while preserving the failed state.
- Added `webhook_processing_lock` around `handle_verified_webhook`, so duplicate provider deliveries cannot concurrently pass idempotency and run business writeback twice.
- Added env/config controls for contract review locks and webhook processing locks.

Additional code touchpoints:

- `backend/src/services/contract_review_lock.py`
- `backend/src/services/webhook_idempotency_service.py`
- `backend/src/services/webhook_handler.py`
- `backend/src/core/config.py`
- `backend/.env.example`
- `backend/tests/test_contract_review_workflow.py`
- `backend/tests/test_webhook_business_events.py`

## P0-6 Contract Attachment Object Storage Lifecycle

Implemented:

- Added `ContractAttachment` and `Contract.attachments` to persist attachment object metadata.
- Added Alembic migration `037_add_contract_attachments.py` with downgrade coverage.
- Added `ContractService.upload_attachment`, `list_attachments`, `get_attachment_content`, `get_attachment_download_url`, and `delete_attachment`.
- Added org-scoped API endpoints for attachment upload, list, streaming download, object-storage download URL, and delete.
- Routed attachment uploads through the shared `read_validated_upload_file` guard.
- Added audit logs for attachment upload/download/delete actions.
- Added front-end API methods and a contract review attachment panel with upload/download/delete controls.

Additional code touchpoints:

- `backend/src/models/contract.py`
- `backend/src/models/audit.py`
- `backend/src/api/routes/contracts.py`
- `backend/alembic/versions/037_add_contract_attachments.py`
- `backend/tests/test_contract_attachments.py`
- `backend/tests/test_contract_attachment_migration.py`
- `frontend/src/lib/api.ts`
- `frontend/src/pages/ContractReview.tsx`
