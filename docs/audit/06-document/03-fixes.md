# TASK-06 Fixes

> Date: 2026-05-06

## 1. Backend Fixes

| Area | Files | Change |
|---|---|---|
| Object storage | `backend/src/services/object_storage_service.py` | Added async storage contract plus `local` and `minio` adapters with object-key normalization and path traversal protection |
| Document persistence | `backend/src/services/document_service.py` | Upload, update, and delete now write/delete object storage keys while preserving DB metadata |
| Contract persistence | `backend/src/services/contract_service.py` | Contract file save now writes through the object storage abstraction |
| Upload validation | `backend/src/api/routes/upload_validation.py`, `documents.py`, `knowledge.py`, `contracts.py` | Upload routes now share the same validator and reject bad extension/MIME/magic/size inputs |
| Template render guard | `backend/src/services/template_engine.py`, `backend/src/api/routes/contracts.py` | Added request model, variable validation, Markdown/HTML escaping, and render output cap |
| Collaboration merge | `backend/src/services/collaboration_service.py` | Added `base_version/baseVersion` support and operation transformation for offline replay |
| Export guard | `backend/src/services/document_export.py`, `backend/src/api/routes/contracts.py` | Added source/output size limits and chunk iterator for `StreamingResponse` |
| Migration | `backend/alembic/versions/029_add_document_object_storage_fields.py` | Added `storage_backend/object_key` fields, indexes, backfill, and downgrade |

## 2. Test Fixes

| Test file | Coverage |
|---|---|
| `backend/tests/test_object_storage_service.py` | Local storage put/get/delete, path traversal, document upload/update/delete, contract save |
| `backend/tests/test_document_upload_validation_api.py` | Upload route validation and rejection behavior |
| `backend/tests/test_template_engine_security.py` | Variable whitelist, type checks, escaping, output cap, malicious template id behavior |
| `backend/tests/test_collaboration_offline_merge.py` | Offline insert/delete rebase and JSON-safe broadcast payload |
| `backend/tests/test_document_export_limits.py` | Export source/output limit and chunk iteration |
| `backend/tests/test_document_object_storage_migration.py` | Migration 029 backfill and downgrade |

## 3. Behavior Preserved

- Old clients that do not send collaboration `base_version` keep current-position semantics.
- `file_path` remains in the document schema during transition; new `object_key` is added without dropping legacy columns.
- Template strings authored by the product remain unescaped; only runtime variable values are escaped.
- Export default limit is conservative at 50MB and can be tuned by env up to an absolute 200MB cap.

