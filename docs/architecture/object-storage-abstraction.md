# Object Storage Abstraction

> Date: 2026-05-06
> Status: backend contract implemented; production rollout still requires MinIO credential rotation and live integration proof.

## 1. Purpose

The document platform must not depend on local ad hoc paths for durable business files. All document and contract bytes should pass through a small storage contract that can run in local tests, docker-compose MinIO, or a future S3-compatible production backend.

## 2. Interface

Implemented in `backend/src/services/object_storage_service.py`:

| Method | Contract |
|---|---|
| `put(object_key, content, content_type=None)` | Writes bytes and returns `StoredObject(backend, bucket, object_key, size, content_type)` |
| `get(object_key)` | Reads bytes for small-object service flows |
| `delete(object_key)` | Deletes idempotently for local storage and removes object for MinIO |
| `exists(object_key)` | Checks object presence |
| `presigned_get_url(object_key, expires_seconds=3600)` | Returns a temporary read URL or `local://` development URL |

All object keys are normalized with POSIX separators. Empty keys, absolute paths, `.` segments, and `..` traversal are rejected before the adapter touches storage.

## 3. Backend Matrix

| Backend | Env | Use case | Notes |
|---|---|---|---|
| `local` | `STORAGE_BACKEND=local`, `STORAGE_LOCAL_PATH=...` | pytest, local development fallback | Writes below a configured root and guards path traversal |
| `minio` | `STORAGE_BACKEND=minio`, `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET`, `MINIO_USE_SSL` | docker-compose and S3-compatible deployments | Uses the MinIO Python client and creates the bucket on first use |
| `s3` alias | `STORAGE_BACKEND=s3` | future production S3-compatible mode | Currently routes to the MinIO adapter; cloud-specific behavior needs a dedicated rollout task if required |

## 4. Data Model

Migration 029 adds transition metadata:

| Table | Columns |
|---|---|
| `documents` | `storage_backend`, `object_key` |
| `document_versions` | `storage_backend`, `object_key` |

`file_path` remains during the transition window. Migration 029 backfills old rows with `storage_backend='local'` and `object_key=file_path` so code can resolve legacy metadata without dropping columns.

## 5. Current Adoption

| Module | Status |
|---|---|
| `DocumentService.upload_document` | Writes uploaded bytes to object storage |
| `DocumentService.update_document_content` | Writes new bytes to a new object and keeps the old object key on `DocumentVersion` |
| `DocumentService.delete_document` | Deletes current and version objects |
| `ContractService.save_contract_file` | Writes generated contract text to object storage |
| Upload routes | Use shared upload validation before data enters storage |
| Export route | Streams generated output and applies source/output size guards |

## 6. Rollout SOP

1. Rotate MinIO credentials away from defaults before any live regression.
2. Run `STORAGE_BACKEND=minio` put/get/delete tests against docker-compose MinIO.
3. Run migration 029 on a staging Postgres snapshot and record row counts before and after backfill.
4. Keep `file_path` reads available during the transition; prefer `object_key` for new writes.
5. Add storage adoption in downstream tasks only through this service contract.
6. After at least one stable release window, propose a separate migration to remove or deprecate legacy `file_path` usage.

## 7. Verification Evidence

- `backend/tests/test_object_storage_service.py`
- `backend/tests/test_document_object_storage_migration.py`
- `backend/tests/test_document_upload_validation_api.py`
- `backend/tests/test_document_export_limits.py`
- Backend full regression: `389 passed, 1 skipped, 9 warnings in 45.76s`

## 8. Risks

| Risk | Control |
|---|---|
| Default MinIO credentials accidentally used outside development | `.env`/deployment review must require rotated secrets |
| New file domains bypass the storage contract | Treat direct local file writes as review blockers for IM, cases, due diligence, templates, A2UI, and desktop sync |
| Large object reads exhaust memory | Add stream-oriented reads before exposing direct large-object download paths |

