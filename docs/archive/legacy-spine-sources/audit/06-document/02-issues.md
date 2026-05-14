# TASK-06 Issues

> Date: 2026-05-06

## P0 Issues

| ID | Issue | Current status | Evidence |
|---|---|---|---|
| DOC-P0-1 | Documents had no durable object storage abstraction | Fixed | `object_storage_service.py`, `test_object_storage_service.py` |
| DOC-P0-2 | Document upload/update/delete did not consistently operate on stored bytes | Fixed | DocumentService object storage tests |
| DOC-P0-3 | Upload validation was duplicated across routes | Fixed | `read_validated_upload_file`, `test_document_upload_validation_api.py` |
| DOC-P0-4 | Template variables could inject Markdown/HTML/business clauses | Fixed | `TemplateEngine.validate_variables`, `test_template_engine_security.py` |
| DOC-P0-5 | Offline collaboration operations were applied against current coordinates | Fixed | `DocumentOperation.base_version`, `test_collaboration_offline_merge.py` |
| DOC-P0-6 | Contract export could generate oversized in-memory output | Fixed | `ExportSizeLimitError`, `ContractExportService.iter_bytes`, `test_document_export_limits.py` |
| DOC-P0-7 | Existing `file_path` rows were not mapped into the new storage contract | Fixed | Migration 029 and `test_document_object_storage_migration.py` |

## P1 Issues

| ID | Issue | Why it remains | Plan |
|---|---|---|---|
| DOC-P1-1 | MinIO live integration is not proven | Credentials must be rotated before production-like tests | Run container roundtrip with non-default credentials |
| DOC-P1-2 | Browser upload/download flows lack E2E | Backend coverage does not prove UI and API integration | Add Playwright upload/download/hash story |
| DOC-P1-3 | Browser collaboration lacks multi-user story | Service rebasing is covered, socket/UI behavior is not | Add two-browser collaboration story |
| DOC-P1-4 | Other file domains are not fully migrated | The object storage interface is ready, but downstream tasks still own adoption | Enforce storage contract in task-specific PRs |
| DOC-P1-5 | Staging backfill is not rehearsed on Postgres | SQLite proves schema behavior, not production operational timing | Run migration on staging snapshot and record timing |

## P2 Issues

| ID | Issue | Plan |
|---|---|---|
| DOC-P2-1 | Full `ruff check src tests` and `mypy src` still have historical baseline failures | Keep touched-file checks green; reduce baseline by directory in Phase 4 |
| DOC-P2-2 | Export performance ceiling has no measured P95 | Add 100MB upload and large export benchmark after MinIO roundtrip |
| DOC-P2-3 | Template frontend ReactMarkdown guard is documented but not enforced by a custom lint rule | Add ESLint guard against `rehype-raw`, `eval`, and `new Function` in template components |

