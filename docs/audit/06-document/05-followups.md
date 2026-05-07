# TASK-06 Follow-ups

> Date: 2026-05-06

## 1. Release-blocking Follow-ups

| Priority | Follow-up | Exit criteria |
|---|---|---|
| P1 | Run MinIO container regression with rotated credentials | `STORAGE_BACKEND=minio` put/get/delete passes and credentials are not defaults |
| P1 | Add Playwright upload/download story | Download hash matches uploaded file hash |
| P1 | Add Playwright two-user collaboration story | Concurrent/offline edits merge without lost or duplicate content |
| P1 | Rehearse migration 029 on staging Postgres snapshot | Upgrade/downgrade succeeds; backfilled rows and duration recorded |
| P1 | Define downstream storage adoption tickets | IM, due diligence, case evidence, templates, A2UI, and desktop sync each have explicit storage path owner |

## 2. Quality Follow-ups

| Priority | Follow-up | Exit criteria |
|---|---|---|
| P2 | Add template frontend lint guard | CI blocks `rehype-raw`, `eval`, and `new Function` in template rendering surface |
| P2 | Add export benchmark | 100MB upload and large export P95 recorded |
| P2 | Reduce historical ruff/mypy baseline | Directory-level error counts trend down without blocking P0 delivery |

## 3. Memory Notes Persisted

The TASK-06 pass has persisted these two hierarchical-memory records:

- Feature `feature-1778040615684`: `Object Storage Abstraction Layer`, covering local/minio adapters, object-key normalization, DocumentService/ContractService adoption, and migration 029.
- Bugfix `bugfix-1778040615729`: document rows had `file_path` metadata without a unified durable-bytes contract; fixed with object storage service adoption plus `storage_backend/object_key` backfill.
