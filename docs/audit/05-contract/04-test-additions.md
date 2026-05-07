# TASK-05 Contract/E-sign — Test Additions

## New Tests

`backend/tests/test_contract_state_machine.py`

- Matrix covers every `ContractStatus` value.
- Legal transitions cover draft/review/approval/signing/active/expiry.
- Illegal transitions cover shortcut signing, backward review, signed-to-draft rollback, active-to-review rollback, expired revival, and terminated revival.
- Service test proves illegal transition preserves stored status.
- API tests cover legal transition, illegal transition `409`, and unknown status `422`.
- E-sign flow API rejects draft contracts with `409`, preventing a delayed webhook failure.

`backend/tests/test_contract_versions.py`

- Applying suggestions creates v2 from v1 and increments `contracts.version`.
- Paragraph-level diff returns added/removed/unchanged segments.
- Rollback creates a new version from an older version instead of mutating history.
- Rollback is routed through the lifecycle state machine and rejected from terminal/legal states.
- API tests cover version list, diff, rollback, and cross-organization 404 behavior.

`backend/tests/test_contract_version_migration.py`

- SQLite migration upgrade creates `contracts.version` and `contract_versions`.
- Downgrade removes the version table/column, proving the local rollback path.

`frontend/e2e/contract-lifecycle.spec.ts`

- Browser story covers upload/review, accepting suggestions, applying versioned edits, comparing v1/v2, and rolling back v1 into v3 from the management contract review surface.

P0-5 additions:

- `tests/test_contract_review_workflow.py::test_review_contract_rejects_concurrent_review` proves a second in-flight review is rejected before the LLM runs.
- `tests/test_contract_review_workflow.py::test_review_contract_timeout_marks_failed_and_allows_retry` proves timeout marks `review_failed` and a later retry can complete.
- `tests/test_webhook_business_events.py::test_verified_webhook_serializes_concurrent_duplicate_business_writeback` proves concurrent duplicate verified webhooks run business writeback only once.

P0-6 additions:

- `tests/test_contract_attachments.py::test_contract_attachment_service_lifecycle` proves service-level upload/list/read/download-url/delete uses object storage and sanitizes path-like filenames.
- `tests/test_contract_attachments.py::test_contract_attachment_api_upload_list_download_delete` proves API-level upload/list/download/download-url/delete, object removal, and audit logging.
- `tests/test_contract_attachments.py::test_contract_attachment_api_blocks_cross_org_access` proves cross-organization users cannot list, download, get download URLs for, or delete another org's attachment.
- `tests/test_contract_attachments.py::test_contract_attachment_upload_uses_shared_file_validation` proves attachment upload reuses the shared file validation guard.
- `tests/test_contract_attachment_migration.py` proves migration `037_add_contract_attachments.py` upgrade/downgrade.

P0-2/P0-3 additions:

- `tests/test_esign_provider_clients.py::test_esignbao_provider_uses_signed_official_headers` proves e签宝 provider calls create/start/sign-url/status/download/cancel endpoints with signed official headers and `Content-MD5`.
- `tests/test_esign_provider_clients.py::test_fadada_provider_uses_fasc_v51_signed_form_calls` proves 法大大 provider uses FASC V5.1 form `bizContent`, grant/access-token flow, `X-FASC-*` signatures, and the expected sign task/status/download/cancel paths.
- `tests/test_external_surface_guards.py::test_fadada_official_webhook_verifies_fasc_headers` proves 法大大 official webhook form notifications are verified before contract state writeback.
- Existing webhook tests now also cover provider event idempotency, state-machine enforcement, and audit writes for signed/status-change transitions.

## Verification

```bash
cd backend && ./.venv/bin/pytest -q tests/test_contract_state_machine.py tests/test_contract_review_workflow.py tests/test_external_surface_guards.py -k 'contract or esign'
# 27 passed, 20 deselected, 6 warnings in 2.85s

cd backend && ./.venv/bin/pytest -q tests/test_webhook_business_events.py tests/test_external_surface_guards.py -k 'esign'
# 9 passed, 22 deselected, 6 warnings in 2.36s

cd backend && ./.venv/bin/pytest -q tests/test_contract_versions.py tests/test_contract_state_machine.py tests/test_contract_review_workflow.py tests/test_external_surface_guards.py -k 'contract or esign or version'
# 32 passed, 20 deselected

cd backend && ./.venv/bin/pytest -q tests/test_contract_version_migration.py tests/test_contract_versions.py
# 6 passed

cd backend && ./.venv/bin/pytest -q tests/test_contract_review_workflow.py tests/test_contract_state_machine.py
# 25 passed, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_webhook_business_events.py tests/test_external_surface_guards.py -k 'esign or webhook'
# 23 passed, 9 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_contract_review_workflow.py tests/test_contract_state_machine.py tests/test_contract_versions.py tests/test_contract_version_migration.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py -k 'contract or esign or webhook or version'
# 54 passed, 9 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_contract_attachments.py tests/test_contract_attachment_migration.py
# 5 passed, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_contract_attachments.py tests/test_contract_attachment_migration.py tests/test_contract_authorization_api.py tests/test_object_storage_service.py tests/test_document_upload_validation_api.py -k 'contract or object_storage or upload'
# 26 passed, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_external_surface_guards.py -k 'esign or fadada'
# 9 passed, 20 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py tests/test_contract_state_machine.py tests/test_contract_review_workflow.py -k 'esign or webhook or contract or provider'
# 56 passed, 8 deselected, 6 warnings

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/contract_lifecycle_service.py src/services/contract_service.py src/services/esign_webhook_service.py src/api/routes/contracts.py src/api/routes/esign.py tests/test_contract_state_machine.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/models/contract.py src/core/database.py src/services/contract_service.py src/api/routes/contracts.py src/api/routes/esign.py tests/test_contract_versions.py tests/test_contract_state_machine.py alembic/versions/036_add_contract_versions.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/contract_review_lock.py src/services/contract_service.py src/services/contract_lifecycle_service.py src/api/routes/contracts.py src/core/config.py tests/test_contract_review_workflow.py tests/test_contract_state_machine.py src/services/webhook_idempotency_service.py src/services/webhook_handler.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/models/contract.py src/models/audit.py src/services/contract_service.py src/api/routes/contracts.py tests/test_contract_attachments.py tests/test_contract_attachment_migration.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/esign_service.py src/api/routes/esign.py src/services/esign_webhook_service.py src/services/official_webhook_security.py src/core/config.py src/models/audit.py tests/test_esign_provider_clients.py tests/test_external_surface_guards.py
# All checks passed

cd backend && ./.venv/bin/pytest -q
# 430 passed, 1 skipped, 10 warnings in 46.41s

cd frontend && npm run lint
# exit 0

cd frontend && npm run build
# exit 0, with existing Vite warnings for lottie eval, api dynamic/static import mix, and large chunks

cd frontend && npx playwright test e2e/contract-lifecycle.spec.ts --project=chromium
# 1 passed
```
