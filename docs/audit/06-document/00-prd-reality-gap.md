# TASK-06 PRD Reality Gap

> Date: 2026-05-06
> Scope: document upload, object storage, template rendering, collaboration merge, export, and migration readiness.

## 1. Claimed Product State vs Code Reality

| Area | Product / status claim | Code-level reality | Commercial status |
|---|---|---|---|
| Document management | Document upload/version/collaboration is treated as functionally complete | `DocumentService` now writes real objects through `object_storage_service`, preserves old versions, and deletes current/version objects; this closes the original "DB row only" gap | Mostly closed for document core |
| Object storage | MinIO exists in compose, but storage contract was not enforced | `local` and `minio` adapters exist; `documents` and `document_versions` now have `storage_backend` and `object_key`; old `file_path` is backfilled by migration 029 | Closed for backend contract, not yet production-proven |
| Upload validation | Upload endpoints were scattered | `documents.py`, `knowledge.py`, and `contracts.py` use `read_validated_upload_file`, which delegates to `FileValidator.validate_file` | Closed for current UploadFile routes |
| Template rendering | Contract templates were user-variable driven | `TemplateRenderRequest` plus `TemplateEngine.validate_variables` enforce variable names, field types, lengths, options, and output size; interpolation escapes HTML/Markdown | Closed for backend P0 |
| Collaboration | Real-time editing existed, but offline replay could overwrite intent | `DocumentOperation.base_version` and operation transformation now rebase old insert/delete/replace operations | Closed for service-level merge tests |
| Export/download | Export returned in-memory files without a size guard | `ContractExportService` guards source/output size and `download_contract` streams chunks via `StreamingResponse` | Closed for contract download path |
| Legacy rows | `file_path` rows had no object storage migration | Migration 029 backfills `object_key=file_path` and `storage_backend='local'`, with downgrade coverage | Closed for SQLite migration proof |

## 2. Remaining Gaps

| Gap | Why it matters | Next action |
|---|---|---|
| MinIO container regression not run | Local adapter is covered, but `STORAGE_BACKEND=minio` is not proven against the compose service in this workspace | Run a disposable MinIO roundtrip test after credential rotation is complete |
| Other attachment domains still need migration | IM attachments, due diligence reports, case evidence, templates, A2UI exports, and desktop sync are downstream users of the same storage contract | Each downstream task must call `object_storage_service` rather than reintroducing local file paths |
| Playwright user stories missing | Backend tests prove services, not full browser upload/download/collaboration behavior | Add upload, download, and two-user collaboration stories |
| Production data migration not rehearsed | SQLite migration proof exists, but production will likely use Postgres | Run upgrade/downgrade on a staging snapshot before release |
| GitNexus full rebuild still blocked | Knowledge graph uses last successful index plus diff scanning, not a complete fresh graph over new files | Keep pairing GitNexus MCP with `git status`, `rg`, direct source review, and tests |

## 3. Decision

TASK-06 is no longer blocked by missing backend primitives. The remaining commercial blockers are verification and rollout work: MinIO integration proof, browser E2E, downstream attachment adoption, and staging migration rehearsal.

