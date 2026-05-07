# TASK-06 Test Additions

> Date: 2026-05-06

## 1. New / Expanded Tests

| Command | Result | Purpose |
|---|---|---|
| `cd backend && ./.venv/bin/pytest -q tests/test_template_engine_security.py` | `7 passed` | Template variable validation and escaping |
| `cd backend && ./.venv/bin/pytest -q tests/test_template_engine_security.py tests/test_document_upload_validation_api.py tests/test_document_generation_api.py` | `17 passed` | Template plus document upload/generation regression |
| `cd backend && ./.venv/bin/pytest -q tests/test_collaboration_offline_merge.py` | `4 passed` | Offline merge transform behavior |
| `cd backend && ./.venv/bin/pytest -q tests/test_collaboration_offline_merge.py tests/test_chat.py -k collaboration tests/test_security_authorization_guards.py` | `10 passed, 32 deselected` | Collaboration plus authorization regression slice |
| `cd backend && ./.venv/bin/pytest -q tests/test_document_export_limits.py tests/test_contract_authorization_api.py -k 'download or export'` | `4 passed, 6 deselected` | Export/download guard and authorization slice |
| `cd backend && ./.venv/bin/pytest -q tests/test_document_object_storage_migration.py tests/test_object_storage_service.py` | `7 passed` | Migration backfill plus storage adapter/document persistence |
| `cd backend && ./.venv/bin/pytest -q` | `430 passed, 1 skipped, 10 warnings in 46.41s` | Backend default full regression after TASK-05 P0-2/P0-3 additions |
| `cd frontend && npx playwright test e2e/document-flows.spec.ts --project=chromium` | `3 passed` | Upload, download, and two-user collaboration delivery stories |

## 2. Static Checks

| Command | Result |
|---|---|
| `cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/template_engine.py src/api/routes/contracts.py tests/test_template_engine_security.py src/services/collaboration_service.py tests/test_collaboration_offline_merge.py src/services/document_export.py tests/test_document_export_limits.py alembic/versions/029_add_document_object_storage_fields.py tests/test_document_object_storage_migration.py` | `All checks passed!` |
| `cd frontend && npm run lint` | pass |
| `cd frontend && npm run build` | pass; existing Vite warnings remain for `lottie-web` eval, `api.ts` mixed dynamic/static import, and large chunks |
| `git diff --check` | pass |
| stale backend-test-count grep across `docs/audit` and `docs/openspec` | no matches |

## 3. Remaining Tests To Add

| Missing test | Acceptance |
|---|---|
| MinIO live roundtrip | With rotated non-default credentials, upload/get/delete a document through `STORAGE_BACKEND=minio` |
| Full Playwright document suite across all browser/device projects | The new upload/download/two-user collaboration stories currently pass on chromium; run full project matrix before release |
| Postgres migration rehearsal | Migration 029 upgrade/downgrade on a staging snapshot records row counts and duration |
| Export performance baseline | Large export stays under agreed memory and latency thresholds |
