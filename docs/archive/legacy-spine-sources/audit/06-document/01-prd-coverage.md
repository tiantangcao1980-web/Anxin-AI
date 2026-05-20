# TASK-06 PRD Coverage

> Date: 2026-05-06

## 1. Coverage Matrix

| Requirement | Implementation | Test / evidence | Status |
|---|---|---|---|
| Unified object storage abstraction | `backend/src/services/object_storage_service.py` with `put/get/delete/exists/presigned_get_url` for `local` and `minio` | `backend/tests/test_object_storage_service.py` | Covered for local adapter |
| Document upload persists bytes | `DocumentService.upload_document` writes object and stores `storage_backend/object_key` | `test_document_upload_writes_object_storage` | Covered |
| Document content updates preserve versions | `DocumentService.update_document_content` writes a new object and stores old key in `DocumentVersion` | `test_document_content_update_preserves_versions_in_storage` | Covered |
| Document deletion removes objects | `DocumentService.delete_document` deletes current and historical objects | `test_document_delete_removes_current_and_version_objects` | Covered |
| Contract save path uses storage | `ContractService.save_contract_file` writes through object storage | `test_contract_save_file_writes_object_storage` | Covered |
| Upload validation is shared | `read_validated_upload_file` used by documents, knowledge, and contract upload/review routes | `backend/tests/test_document_upload_validation_api.py` and route grep | Covered |
| Template variables are bounded | `TemplateEngine.validate_variables` checks names, types, options, lengths, and total payload | `backend/tests/test_template_engine_security.py` | Covered |
| Template output is escaped | `_interpolate` and `_render_party` escape variable values | `backend/tests/test_template_engine_security.py` | Covered |
| Offline collaboration merge preserves intent | `CollaborationSession._transform_operation` rebases old operations by `base_version` | `backend/tests/test_collaboration_offline_merge.py` | Covered at service level |
| Collaboration broadcast is JSON serializable | `_operation_to_dict` serializes timestamps | `test_operation_broadcast_payload_is_json_serializable` | Covered |
| Export has DoS guard | `ContractExportService._ensure_export_size` limits source and output size | `backend/tests/test_document_export_limits.py` | Covered |
| Contract download streams bytes | `download_contract` uses `ContractExportService.iter_bytes` | `test_contract_download_over_limit_returns_413` plus chunk iterator test | Covered |
| Legacy document rows are backfilled | Migration 029 writes `storage_backend='local'` and `object_key=file_path` | `backend/tests/test_document_object_storage_migration.py` | Covered for SQLite |

## 2. Not Yet Covered

| Requirement | Missing proof | Owner task |
|---|---|---|
| MinIO/S3-compatible backend roundtrip | No live MinIO test has been run with rotated credentials | TASK-06 verification follow-up |
| Browser upload/download journey | No Playwright story for real file upload and download hash check | TASK-06 E2E follow-up |
| Two-user browser collaboration | Service merge is tested, but browser/socket collaboration story is not | TASK-06 E2E follow-up |
| Staging Postgres migration rehearsal | Migration is tested with SQLite only | Release migration rehearsal |
| Downstream attachment adoption | IM/case/due-diligence/desktop sync still need feature-specific adoption | TASK-05, TASK-08b, TASK-09, TASK-10, TASK-11b |

