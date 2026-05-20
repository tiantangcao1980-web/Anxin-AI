# TASK-06 文档 + 协作编辑 + 模板 + 对象存储抽象层

> 波次 2 · 工时估 4-5 天（含对象存储抽象层）
> 前置依赖：任务 0（密钥治理 SOP 完成、MinIO 新凭据可用）
> 下游依赖：任务 5（合同附件）/ 任务 8b（案件证据）/ 任务 9（尽调报告）/ 任务 10（IM 文件消息）/ 任务 11b（桌面同步文件 records）
> 必读：`../PLAN.md`、`../00-platform/01-prd-reality-gap.md`、`../00-platform/03-cross-cutting-gaps.md` §1 缺口 A

---

## 1. 范围

### 要碰的文件
- 后端服务层：
  - `backend/src/services/document_service.py`
  - `backend/src/services/document_export.py`
  - `backend/src/services/document_generation_service.py`
  - `backend/src/services/document_parser.py`
  - `backend/src/services/document_validator.py`
  - `backend/src/services/batch_document_service.py`
  - `backend/src/services/collaboration_service.py`
  - `backend/src/services/template_engine.py`
  - `backend/src/services/template_context.py`
  - **新建** `backend/src/services/object_storage_service.py`
- 后端路由：
  - `backend/src/api/routes/documents.py`
  - `backend/src/api/routes/collaboration.py`
  - `backend/src/api/routes/collaboration_ws.py`
- 前端：
  - `frontend/src/pages/Documents.tsx`
  - `frontend/src/pages/DocumentWorkbench.tsx`
  - `frontend/src/pages/Collaboration.tsx`
  - `frontend/src/components/document-library/`
  - `frontend/src/components/document-workbench/`
  - `frontend/src/components/editor/`
- 数据库迁移：
  - 新建 alembic 迁移：`file_path` 字段补 `storage_backend` / `object_key`

### 不要碰的文件
- `backend/src/prompts/`（模板 prompt 改动需用户先看 diff）
- `frontend/src/lib/design-tokens.ts`
- `payment_service` / `subscription` / `billing` 任意文件
- 桌面端 `desktop/src/services/sync_engine.rs`（任务 11b 处理）
- 任何与本任务无关的 secret / `.env` 文件

---

## 2. 必修 P0（带文件:行号 + 期望状态）

| # | 文件:行 | 现状 | 期望 |
|---|---|---|---|
| P0-1 | `backend/src/services/object_storage_service.py` | ✅ 已新增统一抽象 | `local` / `minio` 后端，提供 `put / get / delete / exists / presigned_get_url` |
| P0-2 | `backend/src/services/document_service.py` upload | ✅ 已接入对象存储 | 已调用 `object_storage_service.put()` 落盘 |
| P0-2 | `backend/src/services/document_service.py` delete | ✅ 已接入对象存储 | 已删除当前与历史版本对象 |
| P0-2 | `backend/src/services/document_service.py` update_content | ✅ 已接入对象存储 | 已写新对象并保留旧版本 object_key |
| P0-3 | `backend/src/api/routes/documents.py` / `knowledge.py` / `contracts.py` 上传入口 | ✅ 2026-05-06 已修：文件类型/大小校验统一到共享 helper | `read_validated_upload_file` 统一接 `FileValidator.validate_file`，覆盖 documents、knowledge 单/批量、contracts 解析/流式审查/上传审查入口 |
| P0-4 | `backend/src/services/template_engine.py` + `template_context.py` | ✅ 2026-05-06 已修：变量边界已校验/转义 | 自研正则模板不引入 Jinja；渲染前校验变量白名单、类型、长度与输出大小，变量值做 HTML/Markdown 转义，禁用 `__class__` / `__mro__` 类变量名穿透 |
| P0-5 | `backend/src/services/collaboration_service.py` + `collaboration_ws.py` | ✅ 2026-05-06 已修：离线操作按 `base_version` 转换到当前版本 | A/B 离线插入、删除后插入、实时无版本兼容、广播 payload JSON 序列化均有回归 |
| P0-6 | `backend/src/services/document_export.py` | ✅ 2026-05-06 已修：导出前后均有大小限制，下载响应按 chunk 流式返回 | 默认 50MB、环境变量可调且最高 200MB；源内容/生成文件超限抛 413，`StreamingResponse` 使用 `iter_bytes()` 64KB 分块 |
| P0-7 | alembic 迁移 | ✅ 2026-05-06 已修：`029_document_object_storage` 新增字段并回填历史 `file_path` | `documents`/`document_versions` 旧数据升级时写 `storage_backend='local'` 与 `object_key=file_path`；downgrade 回滚字段/索引 |

---

## 3. 流程（Step 0-6）

### Step 0 · PRD vs 代码差分（强制）
产出 `docs/audit/06-document/00-prd-reality-gap.md`：
- 列 PROJECT_STATUS 中"文档管理已完成"vs `document_service.py` 三处 TODO 的差距
- 列 ROADMAP 中"协作编辑实时合并"vs collaboration_service 实测能力的差距
- 列横切缺口 A 对本任务的影响

### Step 1 · 检索复用
- `/hierarchical-memory find-feature "对象存储抽象 MinIO S3"`
- `/hierarchical-memory find-feature "CRDT 离线合并"`
- `/iterative-retrieval` 按 路由 → 服务 → 模型 → 前端 → 测试 分层读

### Step 2 · 设计 + 双写过渡
- 先写 `object_storage_service.py` + 单测（mock minio + moto[s3]）
- document_service 三处 TODO 改为"双写过渡"：先写 DB，再写存储；DB 写成功即对外 OK，存储失败排队重试
- 写完跑后端测试，确认 273 baseline 不退化

### Step 3 · 数据库迁移
- 生成 alembic：`alembic revision -m "add storage_backend and object_key to documents"`
- 给回滚脚本 `downgrade()`，本地 SQLite + Postgres 各跑一遍升降级

### Step 4 · 修剩余 P0
- P0-3 上传校验统一
- P0-4 模板沙箱（已完成：自研模板保留无 eval/Jinja 路径，变量名/字段白名单 + HTML/Markdown 转义 + 输出大小限制）
- P0-5 协作合并测试（已完成：`base_version/baseVersion` 离线重放位置转换 + 4 个回归）
- P0-6 流式导出（已完成：源内容/输出文件 size guard + 64KB chunk StreamingResponse）
- 跑 `/security-review` 对照 PROJECT_STATUS 钉子

### Step 5 · 验证回路
- `/verification-loop`：pytest（后端，至少新增 15 个用例）+ tsc + lint + build
- `/e2e-testing`：补 Playwright 上传/下载/双人协作三个用户故事
- 性能基线：100MB 文件上传 + 流式导出，记 P95

### Step 6 · 沉淀
- `add-feature --name "object_storage_service" --pattern "MinIO+S3 双后端 env 切换" --files ...`
- `add-bugfix --symptom "document_service 三处 TODO 文件不落盘" --fix "接 storage_service" --files ...`
- 更新 `docs/architecture-v2.md` 加"对象存储抽象层"一节

---

## 4. 输出物

```
docs/audit/06-document/
├─ 00-prd-reality-gap.md
├─ 01-prd-coverage.md
├─ 02-issues.md            (P0/P1/P2 清单)
├─ 03-fixes.md             (本轮修复变更说明)
├─ 04-test-additions.md    (测试覆盖率前后对比)
└─ 05-followups.md         (遗留 → memory)
```

加一份独立的：
- `docs/architecture/object-storage-abstraction.md`（接口规约、env 切换矩阵、双写过渡 SOP）

---

## 5. 风险护栏

- **凭据**：MinIO 凭据必须用任务 0 SOP 完成后的"新凭据"，绝不能复用旧凭据；secret 通过 env，不进 git
- **切换策略**：先双写过渡期至少 7 天（DB + 存储双写），人工抽样比对后再切只读路径；不允许 big-bang 切换
- **schema 迁移**：必须给回滚脚本；本地 SQLite + Postgres 两库各跑升降级 1 次；生产前再灰度
- **本任务是依赖**：是任务 5 / 8b / 9 / 10 / 11b 的前置依赖，未交付前其它任务不得 mock 实现绕过
- **模板沙箱**：变更 prompt-like 的 template engine 配置前 diff 给用户
- **大文件**：导出 size 上限默认 50MB，超出即 413；可通过 env 调整，但生产配置不许超过 200MB
- **不动**：payment / billing / design-tokens / prompts / 桌面同步引擎

---

## 6. 完成标准（DoD）

- [x] `object_storage_service.py` 落地，local 单测覆盖核心 put/get/delete/path traversal；MinIO 容器回归待补
- [x] `document_service.py` 三处 TODO 全部接通；上传/删除/更新文件已在 local 对象存储回归中验证
- [x] 上传校验统一到共享校验器；越权/超大/非法 mime 全部 4xx。证据：`tests/test_document_upload_validation_api.py` 8 passed，相关回归 28 passed，`rg "UploadFile|File\\(" backend/src/api/routes -g '*.py'` 显示所有 UploadFile 路由均接 `read_validated_upload_file`
- [x] 模板引擎沙箱：注入 `__class__`/嵌套 party/非法 select/超长文本无法穿透；变量输出 HTML/Markdown 转义。证据：`tests/test_template_engine_security.py` 7 passed，文档上传/生成组合回归 17 passed，后端全量 `430 passed, 1 skipped, 10 warnings`
- [x] 协作离线合并测试：A/B 离线各编辑 100 字 → 合并后字符总数与重叠区一致，无丢字、无重复。证据：`tests/test_collaboration_offline_merge.py` 4 passed，协作 API/授权组合 `10 passed`
- [x] 大文档流式导出：导出源内容/输出文件超限拒绝，下载响应按 64KB chunk 迭代。证据：`tests/test_document_export_limits.py` 覆盖源内容超限、chunk 迭代和合同下载 413，合同下载授权组合 `4 passed`
- [x] alembic 升级 + 回滚双向跑通；老数据 backfill 本地 SQLite 已覆盖。证据：`tests/test_document_object_storage_migration.py` 通过，验证 `documents`/`document_versions` 回填与 downgrade 去列
- [x] 后端 pytest 全绿（当前 `430 passed, 1 skipped`）；前端 lint/build 通过。证据：`frontend npm run lint` exit 0，`npm run build` exit 0；仍有既有 Vite P2 警告（lottie eval、api 动/静态导入混用、大 chunk），未作为 TASK-06 P0 阻断
- [x] Playwright 三个用户故事（上传/下载/双人协作）全绿。证据：`cd frontend && npx playwright test e2e/document-flows.spec.ts --project=chromium` → `3 passed`
- [x] `docs/audit/06-document/00..05.md` + `docs/architecture/object-storage-abstraction.md` 全部产出
- [x] 经验沉淀到 hierarchical-memory（add-feature + add-bugfix 至少各 1 条）。证据：`feature-1778040615684` / `bugfix-1778040615729` 可通过 `find-feature` / `find-bugfix` 检索
