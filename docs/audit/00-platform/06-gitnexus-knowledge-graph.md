# GitNexus 知识图验证记录

> 日期：2026-05-07
> 目标：在进入下一步商业交付开发前，确认 GitNexus 索引可作为代码级导航依据。

## 1. 当前索引状态

| 项 | 结果 |
|---|---|
| repo | `Anxin-Smart-Legal-Services` |
| path | `/Users/pengchengkeji/Documents/GitHub/Anxin-Smart-Legal-Services` |
| commit | `b01122d916f653b974ece08628a8d18fb4f581a3` |
| files | 1181 |
| symbols/nodes | 30003 |
| edges | 54587 |
| clusters | 1028 |
| flows/processes | 300 |
| embeddings rows | 28219 |
| distinct embedded nodes | not separately verified |

`npx -y gitnexus@latest status` 显示索引与当前 commit 一致。2026-05-06 23:06 使用 rc 版直接二进制完成主仓 embedding 生成；当前 `.gitnexus/meta.json` 显示 `capabilities.vectorSearch.status=vector-index`，embedding stats 和 store 均可读。验证通过：`cypher MATCH (e:CodeEmbedding) RETURN count(e) AS cnt` 返回 `28219`，`context getDesktopSQLiteSecurityStatus` 可定位到 `frontend/src/lib/api-adapter.ts:97`，`query "desktop sqlite security status"` 的 timing 显示走 vector/BM25 merge 并返回相关定义。注意：`npx gitnexus@rc` 在本机仍可能触发 npm/arborist rebuild bug；推荐使用 `GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus`。

## 2. 配置修正

- 新增 `.gitnexusignore`，只让 GitNexus 索引产品源码与耐久文档，排除 `.claude/`、`.omx/`、`.super-skill/`、`.superpowers/`、缓存、构建产物和密钥文件。
- `.gitignore` 新增 `.super-skill/`，避免本地代理记忆与 trace 进入 Git。
- `.gitignore` / `.gitnexusignore` 新增 `.gitnexus.*`，避免本地索引备份与失败产物进入 Git 或被 GitNexus 自己再次索引。
- Codex GitNexus MCP 配置增加：
  - `HF_HOME=/Users/pengchengkeji/.cache/gitnexus-huggingface`
  - `GITNEXUS_EMBEDDING_DEVICE=cpu`
- `scripts/gitnexus-index.sh` 支持 `GITNEXUS_NPX_SPEC`，默认 `gitnexus@latest`；需要 embedding 时当前使用 `gitnexus@rc`，因为 rc 版在最小仓库和主仓均可写入 embeddings/vector index。
- 修复默认 Hugging Face 缓存断链：`/Users/pengchengkeji/.cache/huggingface` 原本指向未挂载的 `/Volumes/安心科技01/...`，已备份为 `/Users/pengchengkeji/.cache/huggingface.broken-symlink-20260506-092121`，当前指向 `/Users/pengchengkeji/.cache/gitnexus-huggingface`。

## 3. 验证命令与证据

已执行：

```bash
npx -y gitnexus@latest clean -f
HF_HOME=/Users/pengchengkeji/.cache/gitnexus-huggingface \
GITNEXUS_EMBEDDING_DEVICE=cpu \
npx -y gitnexus@latest analyze --skip-agents-md

npx -y gitnexus@latest cypher -r Anxin-Smart-Legal-Services \
  "MATCH (e:CodeEmbedding) RETURN count(e) AS rows, count(DISTINCT e.nodeId) AS nodes"

npx -y gitnexus@latest context -r Anxin-Smart-Legal-Services ModeGate
npx -y gitnexus@latest context -r Anxin-Smart-Legal-Services ProtectedRoute
npx -y gitnexus@latest context -r Anxin-Smart-Legal-Services LLMService
npx -y gitnexus@latest context -r Anxin-Smart-Legal-Services DocumentService
```

符号级验证结果：

- `ModeGate` 能定位到 `frontend/src/components/mode/ModeGate.tsx`，并识别其对 `checkModeAccess` 的调用。
- `ProtectedRoute` 能定位到 `frontend/src/components/auth/ProtectedRoute.tsx`，并识别 `usePermission`、`isTokenExpired`、`inferPrimaryClient` 等出边。
- `LLMService` 能定位到 `backend/src/services/llm_service.py`，并枚举 `list_configs`、`get_config`、`set_default` 等方法。
- `DocumentService` 能定位到 `backend/src/services/document_service.py`，并枚举 `upload_document`、`delete_document`、`update_document_content` 等方法。
- `detect_changes(scope=all)` 可识别当前工作区改动符号，并提示 A2UI 相关流程受影响。

2026-05-06 本轮开发后复核：

- 历史快照：MCP `list_repos` 当时可发现 `Anxin-Smart-Legal-Services`，显示 `embeddings: 23318`；该 embedding 口径已被当前结构重建结果取代。
- `npx -y gitnexus@latest status` 显示 `Indexed commit: b01122d`、`Current commit: b01122d`、`Status: up-to-date`。
- 历史快照：MCP `detect_changes(scope=unstaged)` 在认证 + token 存储迁移 + 小程序微信真实登录/假资讯 fallback 清理 + 移动端审批详情/首页/聊天/设置 fallback 与假数据标记清理 + S9 上传入口共享校验器 + TASK-06 P0-4 模板变量校验/转义 + TASK-06 P0-5 协作离线合并 `base_version` 转换 + TASK-06 P0-6 导出大小限制/分块下载 + TASK-06 P0-7 历史 `file_path` 回填迁移源码复核 + TASK-06 Playwright 上传/下载/双人协作故事 + TASK-05 P0-1 合同生命周期状态机 + TASK-05 P0-4 合同版本 diff/回滚 + TASK-05 P0-5 审查锁/超时与 webhook processing lock + TASK-05 P0-6 合同附件对象存储生命周期 + V2 守卫 + Web privacy mode header + IM WS 首包鉴权 + IM 离线 ACK 前后端协议 + 对象存储底座 + 支付/电签 webhook 通用回写 + webhook 持久化幂等 + Admin webhook 查询/手动重试 + Prometheus 指标 + 电签 flow 映射 + webhook 自动重试/backoff + 微信支付 v3/支付宝 RSA2 官方回调验签 + e签宝官方 HMAC 回调验签 + 退款幂等 + 订阅状态机 + 双客户端订阅隔离/前端双栏展示 + Pricing 双端套餐过滤 + 微信/支付宝 provider 请求客户端与同步响应验签 + 统一 `webhook_handler.py` + 稳定 webhook events + 官方通知 id 幂等补丁后返回 `changed_files/changed_symbols: 93/918`、`affected_processes: 64`、`risk_level: critical`。
- 受影响符号/流程扩展到 `getTokenStorage/createBrowserTokenStorage/createDesktopTokenStorage`、`ProtectedRoute/AdminRoute`、`Login/ResetPassword`、`useIMWebSocket`、`_routeMessage`、`ChatWindow → _routeMessage`、`Messages → _routeMessage`、`MySubscription` 双客户端订阅归一化/展示、`Pricing` 套餐归一化/端侧过滤、`mini-program/Profile.handleLogin`、`mini-program/Index.loadNews`、小程序 `request/refreshToken` 响应归一化、`WeChatMiniProgramOAuth.code2session` 与 `/auth/wechat/code2session`、`mobile/ApprovalDetailScreen.loadDetail`、`getDetailLoadErrorMessage`、`mobile/HomeScreen.loadInbox`、`mobile/EmptySection`、`mobile/ChatScreen` 欢迎语 header，`FileValidator.validate_file`、`read_validated_upload_file`、`documents.upload_document`、`knowledge.upload_document_to_kb`、`knowledge.batch_upload_documents`、`contracts.parse_contract_file`、`contracts.stream_review_contract`、`contracts.upload_and_review_contract`、`contracts.render_template`、`TemplateRenderRequest`、`TemplateEngine.validate_variables`、`TemplateEngine._escape_markdown_value`、`TemplateEngine._coerce_number`、`CollaborationSession.apply_operation`、`CollaborationSession._transform_operation`、`CollaborationSession._transform_position`、`CollaborationService.handle_operation`、`DocumentOperation.base_version`、`_operation_to_dict`、`contracts.download_contract`、`ContractExportService._ensure_export_size`、`ContractExportService.iter_bytes`、`ExportSizeLimitError`、`029_document_object_storage.upgrade`、`029_document_object_storage.downgrade`、`documents/document_versions.file_path → object_key` 回填，`AdminFeatureFlags`、`Collaboration`、A2UI handler，`create_text_document` / `upload_document` / `update_document_content` / `save_contract_file` 对象存储调用链，以及支付/电签 webhook 的业务回写、`webhook_received` 幂等、Admin `/admin/webhooks` 查询/重试链路、`/metrics` webhook 指标、`create_sign_flow → contracts.esign_flow_id → esign_webhook` 映射链路、FastAPI lifespan 启动的 webhook retry worker、`wechat_webhook` / `alipay_webhook` 官方验签开关路径、`esign_webhook` e签宝官方验签开关路径、`refund_order` / `RefundService.refund` 退款幂等路径、`payment_service` provider 选择/下单/退款调用路径，以及 `dep/get_my_features → get_effective_features → get_active_by_client` 订阅守卫路径。
- 这些流程已用 `backend/tests/test_auth_surface_hardening.py`（`18 passed`，含小程序 code2session 不泄露 `session_key`）、`backend/tests/test_a2ui_handler_auth.py`、`backend/tests/test_a2ui_protocol_version.py`、`backend/tests/test_object_storage_service.py`、`backend/tests/test_document_upload_validation_api.py`（`8 passed`）、`backend/tests/test_template_engine_security.py`（`7 passed`）、`backend/tests/test_collaboration_offline_merge.py`（`4 passed`）、`backend/tests/test_document_export_limits.py`（导出超限/分块，组合 `4 passed`）、`backend/tests/test_document_object_storage_migration.py`（迁移回填/downgrade，组合对象存储 `7 passed`）、`backend/tests/test_contract_state_machine.py`、`backend/tests/test_contract_versions.py`、`backend/tests/test_contract_version_migration.py`、`backend/tests/test_contract_review_workflow.py`、`backend/tests/test_contract_attachments.py`、`backend/tests/test_contract_attachment_migration.py`、合同/e签相关回归（`27 passed`/`9 passed`/`32 passed`/`6 passed`/`25 passed`/`54 passed`）、合同附件/对象存储/上传授权回归（`5 passed`/`26 passed`）、文档/模板/上传/协作/授权相关回归（`17 passed`/`28 passed`/`10 passed`）、`backend/tests/test_official_webhook_security.py`、`backend/tests/test_external_surface_guards.py`、`backend/tests/test_refund_idempotency.py`、`backend/tests/test_subscription_state_machine.py`、`backend/tests/test_im_offline_messages.py`、`backend/tests/test_im_websocket_auth.py`、`backend/tests/test_knowledge_management_security.py`（`5 passed`）、`frontend/src/hooks/useIMWebSocket.test.ts`、`frontend/src/pages/MySubscription.test.ts`、`frontend/src/pages/Pricing.test.ts`、`frontend/e2e/document-flows.spec.ts`（`3 passed`）、`frontend/e2e/contract-lifecycle.spec.ts`（`1 passed`）、`frontend/e2e/knowledge-graph-performance.spec.ts`（`1 passed`）、`mobile/src/features/workflow/detail-model.test.ts`、小程序 `tsc --skipLibCheck` / `build:weapp`、移动端 `npm test`（`6 files / 15 tests passed`）、`npx tsc --noEmit --module esnext`、移动/小程序 fallback grep 与 mini-program design token guard、后端全量 pytest（当前最新 `467 passed, 1 skipped, 17 warnings in 36.11s`）、前端 Vitest（当前最新 `10 files / 34 tests passed`）、lint/build 与 `frontend/e2e/role-access.spec.ts` 复核。注意：当前 GitNexus 结构图和 embeddings 已覆盖本轮工作树；本轮仍以 GitNexus 影响面 + `rg` 源码复核 + 测试共同判定。
- MCP/Cypher 复核显示 `ContractService` 与 `ContractReview` 仍可定位，但图内 `ContractService` 方法列表缺少本轮新增的 `transition_status`、`get_contract_versions`、`get_version_diff`、`rollback_to_version`、`upload_attachment`、`get_attachment_download_url`；`ContractLifecycleStateMachine`、`ContractVersion` 与 `ContractAttachment` 未进入图谱；`query("ContractAttachment upload attachment download-url object storage contract attachments")` 和 `context(name="ContractAttachment")` 返回空。结论：GitNexus 现阶段只能证明旧图 + 当前 diff 影响面，不能证明新增状态机/版本/附件类已进入 embedding 图。
- 2026-05-06 电签 provider/webhook 收口后复核：
  - 历史快照：MCP `list_repos` 当时显示本仓库 `files: 1026`、`nodes: 25735`、`edges: 38986`、`processes: 167`、`embeddings: 23318`，索引基础可用。
  - MCP `detect_changes(scope=unstaged)` 在新增 e签宝 provider、法大大 provider、FASC webhook 验签、审计双写与测试/文档更新后返回历史快照 `changed_files/changed_symbols: 94/991`、`affected_processes: 64`、`risk_level: critical`。
  - MCP `context(name="ESignBaoProvider", kind="Class")` 与 `context(name="FaDaDaProvider", kind="Class")` 可定位到 `backend/src/services/esign_service.py` 并列出 `create_sign_flow/get_sign_url/get_flow_status/download_signed_doc/cancel_flow` 等方法，说明旧图可作为 provider 方法导航；但当前源码中的新 helper、签名细节、法大大 webhook verifier、配置项和测试仍以 `rg`、直接读源码、pytest 结果为事实依据，直到下一次全量 embedding 重建成功。
  - MCP `context(name="verify_fadada_notification")`、`context(name="_fadada_signature")`、`context(name="test_fadada_provider_uses_fasc_v51_signed_form_calls")` 返回 `Symbol not found`，确认新 helper 与新测试尚未进入当前图谱。
  - 历史观察：MCP `cypher("MATCH (e:CodeEmbedding) RETURN count(e)")` 当时返回 `0`，与 `list_repos.stats.embeddings=23318` 不一致。该口径先被结构重建快照取代，当前最终以 `.gitnexus/meta.json` 的 `embeddings: 28219` 为准。
  - 本轮代码级事实已用 `backend/tests/test_esign_provider_clients.py`、`backend/tests/test_official_webhook_security.py`、`backend/tests/test_webhook_business_events.py`、`backend/tests/test_external_surface_guards.py`、`backend/tests/test_contract_state_machine.py`、`backend/tests/test_contract_review_workflow.py` 切片（`56 passed, 8 deselected`）以及后端全量 pytest（当前最新 `467 passed, 1 skipped, 17 warnings in 36.11s`）补盲。
- 2026-05-06 TASK-11b 后端同步日志收口后复核：
  - 历史快照：MCP `list_repos` 当时显示本仓库 `files: 1026`、`nodes: 25735`、`edges: 38986`、`processes: 167`、`embeddings: 23318`。
  - MCP `detect_changes(scope=unstaged)` 在同步日志模型、迁移、服务、路由、测试与文档更新后返回历史快照 `changed_files/changed_symbols: 97/1029`、`affected_processes: 64`、`risk_level: critical`。
  - MCP `cypher` 可定位 `SyncService`、`ESignBaoProvider`、`FaDaDaProvider`，并列出 `SyncService.push/pull/status/resolve/full_sync/push_artifacts/pull_artifacts` 与 provider 方法；但 `SyncLog`、`verify_fadada_notification`、`_fadada_signature` 等新增/细粒度符号仍不可按名称定位。
  - MCP 概念查询 `backend sync service push pull incremental offline sync SyncLog` 与 `ESignBaoProvider FaDaDaProvider FASC webhook` 返回空，而 Cypher 可查到类级符号。结论：当前图谱对类/方法级结构仍可导航，但自然语言 query 不能作为新增代码覆盖率证明。
  - 同步底座事实以 `backend/src/models/sync.py`、`backend/alembic/versions/038_add_sync_log.py`、`backend/src/services/sync_service.py`、`backend/src/api/routes/sync.py` 的源码审计，以及 `tests/test_sync_log_service.py` / `tests/test_sync_api_security.py` 切片（`24 passed, 6 warnings`）和后端全量 pytest（当前最新 `467 passed, 1 skipped, 17 warnings in 36.11s`）为准。
- 2026-05-06 TASK-11b 桌面 Tauri SQL 同步路径收口后复核：
  - MCP `detect_changes(scope=unstaged)` 在前端 `api-adapter.ts` 同步路径、retry/backoff、`tauri-bridge.ts` 优先本地同步、`SyncStatus.tsx` 状态更新、`SyncConflicts.tsx` 冲突管理页、Rust IPC fallback 去假阳性、Rust local DB schema 对齐、Tauri build command 修正、测试与文档更新后返回 `changed_files: 102`、`changed_symbols: 1059`、`affected_processes: 64`、`risk_level: critical`。
  - MCP `cypher` 可定位既有 `triggerSync` 与 `getPendingSyncCount`，但新 helper `triggerLocalSync`、`buildSyncPushPayload`、`normalizeRemoteSyncRecord` 尚未进入图谱；概念查询 `desktop Tauri SQLite sync triggerLocalSync buildSyncPushPayload api-adapter sync_log` 返回空。
  - 2026-05-06 retry/backoff + 冲突页复核：CLI `gitnexus status` 显示 `Indexed commit: b01122d`、`Current commit: b01122d`、`Status: up-to-date`；MCP `context(name="triggerSync", kind="Function")` 仍可定位既有桥接入口，但 `context(name="calculateSyncRetryState", kind="Function")` 与 `context(name="SyncConflicts", kind="Function")` 返回 `Symbol not found`，说明新增 retry helper 和冲突管理页尚未进入当前图谱。
  - 桌面同步事实以 `frontend/src/lib/api-adapter.ts`、`frontend/src/lib/tauri-bridge.ts`、`frontend/src/components/mode-switcher/SyncStatus.tsx`、`frontend/src/pages/SyncConflicts.tsx`、`desktop/src/commands/sync.rs` 的源码审计，以及 `frontend/src/lib/api-adapter.sync.test.ts`、`frontend/src/lib/sync-conflict-utils.test.ts`、`npm run test`（当前最新 `10 files / 34 tests passed`）、`npm run lint`、`npx tsc --noEmit`、`desktop cargo check` 为准。
- 2026-05-06 TASK-07 RAG 引用/权限/PII 收口后复核：
  - 历史快照：MCP `list_repos` 当时显示本仓库 `files: 1026`、`nodes: 25735`、`edges: 38986`、`processes: 167`、`embeddings: 23318`。
  - 历史快照：MCP `detect_changes(scope=unstaged)` 当时在大工作树上返回 `changed_files: 108`、`changed_symbols: 1144`、`affected_processes: 68`、`risk_level: critical`。当前最新 CLI detect-changes 为 `354/5685/240/critical`。
  - MCP `context(name="build_context", file_path="backend/src/services/rag_service.py")` 可定位 `RAGService.build_context`，入边为 `query`、`stream_query`、`multi_query_rag`。
  - MCP `impact(target="build_context", direction="upstream", includeTests=true)` 返回 `risk: LOW`、直接影响 3 个调用者、2 个流程、1 个模块。
  - MCP `context(name="rag_query", file_path="backend/src/services/knowledge_service.py")` 可定位 `KnowledgeService.rag_query`，入边为 API route `knowledge.rag_query` 和 chat handler `handle_rag_query`。
  - MCP `context(name="SmartSearch", file_path="frontend/src/components/knowledge-center/SmartSearch.tsx")` 与 `context(name="KnowledgeBase", file_path="frontend/src/pages/KnowledgeBase.tsx")` 可定位组件/页面，但新增 `source-preview-utils.ts` / `getExternalSourceUrl` 仍返回 `Symbol not found`，说明新增前端 utility 尚未进入当前图谱。
  - TASK-07 事实以 `backend/src/services/knowledge_service.py`、`backend/src/services/knowledge_management.py`、`backend/src/api/routes/knowledge_management.py`、`backend/src/services/pii_service.py`、`backend/src/services/citation_tracker.py`、`backend/src/services/rag_service.py`、`frontend/src/components/knowledge-center/SmartSearch.tsx`、`frontend/src/components/knowledge-center/source-preview-utils.ts`、`frontend/src/pages/KnowledgeBase.tsx`、`frontend/src/components/knowledge-graph/graphPerformance.ts`、`frontend/src/components/knowledge-graph/ForceGraphCanvas.tsx`、`frontend/src/components/knowledge-center/KnowledgeGraphExplorer.tsx`、`eval/rag_live_qdrant_smoke.py`、`eval/rag_live_qdrant_full50.py`、`eval/export_builtin_legal_full50.py` 的源码审计，以及后端 RAG 切片、知识管理安全切片、RAG full50 runner tests（`8 passed`）、RAG quality tests（`4 passed`）、后端全量 pytest（`467 passed, 1 skipped, 17 warnings in 36.11s`）、前端 Vitest（`10 files / 34 tests passed`）、Playwright RAG source E2E（`1 passed`）、Playwright 图谱 1k 性能 E2E（`1 passed`）、lint/build 为准。live Qdrant smoke 已验证 Qdrant + embedding plumbing，内建法律知识库 full50 live baseline 已写出 50 条 predictions 和 release metrics。
- 2026-05-06 TASK-07 知识管理接口安全复核：
  - CLI `gitnexus context KnowledgeManagementService` 可定位旧图中的 `backend/src/services/knowledge_management.py` 类和 `add_experience/search_experiences/get_experience/mark_useful/recommend_for_task/add_custom_template/list_custom_templates/extract_from_review/get_stats` 方法。
  - 当前新增的 `_require_org_id`、权限依赖变更、PII 出口脱敏调用、新 UUID ID 生成和 `backend/tests/test_knowledge_management_security.py` 仍属于未提交新事实，必须以 `rg`、源码阅读、ruff 与 pytest 为准。
- 2026-05-06 TASK-07 知识图谱大图性能复核：
  - CLI `gitnexus context ForceGraphCanvas` 可定位旧图中的画布组件；`gitnexus context createGraphRenderPlan` 返回 `Symbol not found`，说明新增渲染计划 helper 尚未入图。
  - 图谱大图事实以 `frontend/src/components/knowledge-graph/graphPerformance.ts`、`ForceGraphCanvas.tsx`、`KnowledgeGraphExplorer.tsx`、`frontend/src/components/knowledge-graph/graphPerformance.test.ts` 和 `frontend/e2e/knowledge-graph-performance.spec.ts` 为准。
- 2026-05-06 TASK-09 尽调缓存 org 隔离复核：
  - CLI `gitnexus status` 仍显示 `Indexed commit: b01122d`、`Current commit: b01122d`、`Status: up-to-date`，说明当前可用图谱仍是提交级旧索引。
  - CLI `gitnexus context SearchCache` 可定位旧图中的 `SearchCache`，但属性列表不含本轮新增 `org_id`，确认未提交新 schema 尚未入图。
  - CLI `gitnexus context test_investigation_cache_org_scope` 返回 `Symbol not found`，说明新增回归测试尚未入图。
  - TASK-09 P0-7 事实以 `backend/src/models/investigation.py`、`backend/alembic/versions/039_add_search_cache_org_scope.py`、`backend/src/services/investigation_data_store.py`、`backend/src/services/investigation_orchestrator.py`、`backend/src/services/deep_research_engine.py`、`backend/src/api/routes/due_diligence.py` 的源码审计，以及 `backend/tests/test_investigation_cache_org_scope.py`（`3 passed`）为准。
- 2026-05-06 TASK-09 意图路由评测复核：
  - CLI `gitnexus context --repo Anxin-Smart-Legal-Services classify_investigation_request` 返回 `Symbol not found`，说明新增 classifier 尚未入图。
  - CLI `gitnexus context --repo Anxin-Smart-Legal-Services investigation_routing_eval` 返回 `Symbol not found`，说明新增 JSONL 评测集尚未入图。
  - TASK-09 P0-5 事实以 `backend/src/services/due_diligence_service.py`、`backend/src/services/chat_service.py`、`backend/tests/test_due_diligence_intent.py`、`backend/tests/test_chat_due_diligence_routing.py`、`backend/tests/eval/investigation_routing_eval.jsonl` 的源码审计，以及意图 + ChatService 路由切片（`13 passed`，200 条评测样本，意图/企业名准确率均为 `1.000`）为准。
- 2026-05-06 TASK-08a/08b 案件与律师市场复核：
  - 当前 GitNexus 索引仍是提交级旧图；`CASE_STATUS_TRANSITIONS`、`_MATCHING_EXPOSURE_COUNTER`、local 模式拒绝 helper 和新增 08a/08b 测试属于未提交新事实。
  - TASK-08a/08b 事实以 `backend/src/services/case_service.py`、`backend/src/services/task_service.py`、`backend/src/api/routes/cases.py`、`backend/src/api/routes/tasks.py`、`backend/src/api/routes/lawyer_matching.py`、`backend/src/api/routes/case_market.py`、`backend/src/services/conflict_check_service.py`、`backend/src/services/lawyer_matching_service.py` 的源码审计，以及 `backend/tests/test_case_service.py` + `backend/tests/test_lawyer_matching_and_tasks_api.py`（组合 `46 passed`）为准。
- 2026-05-06 09:10 尝试对当前工作树做强制重建并生成 embeddings：
  - 先备份现有可用索引到 `.gitnexus.backup-20260506-091041`。
  - `HF_HOME=/Users/pengchengkeji/.cache/gitnexus-huggingface npx -y gitnexus@latest analyze --force --embeddings --skip-agents-md` 最终退出码 1，未更新本仓库 meta。
  - `npx -y gitnexus@latest analyze . --force --skip-agents-md --name Anxin-Smart-Legal-Services` 暴露两类配置/存储问题：旧 LadybugDB `Corrupted wal file` warning，以及默认 `/Users/pengchengkeji/.cache/huggingface` 为断链。
  - 清理坏索引后，使用显式 `HF_HOME` / `HF_HUB_CACHE` 从干净状态重建仍在 embedding 阶段退出码 1，且未生成 `.gitnexus/meta.json` / registry 条目。
  - 已将失败产物移到 `.gitnexus.failed-20260506-092121`，恢复 `.gitnexus.backup-20260506-091041` 与 registry 中的 `Anxin-Smart-Legal-Services` 条目。
- 2026-05-06 15:28 再次尝试强制重建当前工作树：
  - `npx -y gitnexus@latest analyze --force --embeddings --skip-agents-md --name Anxin-Smart-Legal-Services .` 在若干 Python scope extraction warning 后长时间无输出并以退出码 -1 结束。
  - 失败后 `.gitnexus/lbug` 与 `.gitnexus/lbug.wal` 被半写；CLI `query` 暴露 `Cannot execute write operations in a read-only database` warning。
  - 已将半写索引移到 `.gitnexus.failed-20260506-153328`，并从 `.gitnexus.backup-20260506-091041` 恢复可用索引。
  - 恢复后 `npx -y gitnexus@latest status` 正常，`context build_context` 可读。
- 历史结论（已被当前结构重建取代）：GitNexus 当时保持“上一版成功索引 + 23318 embeddings + 当前 diff 影响扫描”可用；未提交的新文件与新符号需用 `detect_changes`、`git status --short`、`rg`、直接源码阅读和专项 pytest/Vitest/Playwright 补齐事实。
- 2026-05-06 当前工作树结构索引恢复：
  - `npx -y gitnexus@latest clean --force && npx -y gitnexus@latest analyze --force --skip-agents-md .` 成功，输出 `Repository indexed successfully`，清理损坏 WAL 后恢复了结构索引。
  - 历史结构-only `bash scripts/gitnexus-index.sh` 成功，输出 `1179 files / 28599 nodes / 43768 edges / 1005 clusters / 229 flows`。
  - `npx -y gitnexus@latest status` 显示 `Indexed commit: b01122d`、`Current commit: b01122d`、`Status: up-to-date`。
  - `npx -y gitnexus@latest context --repo Anxin-Smart-Legal-Services runLocalSyncWithDependencies` 已可定位 `frontend/src/lib/api-adapter.ts:986`，出边包括 `writeSetting`、`getDeviceId`、`pushPendingRecords`、`pullIncrementalUpdates`，入边来自 `frontend/src/lib/api-adapter.sync.test.ts`。
  - `npx -y gitnexus@latest context --repo Anxin-Smart-Legal-Services getDesktopSQLiteSecurityStatus` 已可定位 `frontend/src/lib/api-adapter.ts:97`，入边来自 `frontend/src/lib/api-adapter.sync.test.ts`。
  - `npx -y gitnexus@latest context --repo Anxin-Smart-Legal-Services sqlite_migrations` 已可定位 `desktop/src/services/local_db.rs:12`，入边来自 `desktop/src/lib.rs::run` 与 `sqlite_migrations_register_initial_schema`。
  - direct rc CLI `detect-changes --repo Anxin-Smart-Legal-Services` 在当前大工作树上返回 `changed_files: 354`、`changed_symbols: 5685`、`affected_processes: 240`、`risk_level: critical`。
  - 历史结构-only 快照中 `.gitnexus/meta.json` 为 `embeddings: 0`。`analyze --embeddings` 在 up-to-date 状态下直接 `Already up to date`，不会补生成 embeddings；`analyze --force --embeddings --verbose --skip-agents-md .` 两次在长时间本地 embedding 阶段后退出码 1，并让后续 `context` 报 `Corrupted wal file`，因此当时已清理并恢复为无 embeddings 的结构索引。
  - 2026-05-06 19:20 使用 `.env` 现有 `EMBEDDING_BASE_URL/MODEL/DIMENSIONS/API_KEY` 复用 OpenAI-compatible endpoint，最小 `/embeddings` probe 返回 HTTP 200，向量维度 1024。随后运行 `scripts/gitnexus-index.sh --embeddings --skip-context-checks`，脚本备份 `.gitnexus` 到 `.gitnexus.backup-20260506-192019`，约 42 分钟后退出码 1；半写索引已移到 `.gitnexus.failed-20260506-200138`，并恢复备份结构索引。失败索引体积约 213M，`meta.json` 仍为 `embeddings: 0`。
  - `scripts/gitnexus-index.sh --embeddings` 已支持在未显式设置 `GITNEXUS_EMBEDDING_*` 时，自动从 `.env` / `backend/.env` 的 `EMBEDDING_*` 读取 base URL、model、dims 和 API key。
  - 2026-05-06 20:24 进一步定位：直接调用 GitNexus 1.6.3 的 HTTP embedder 成功返回 1024 维 query/batch 向量；最小临时仓库在真实 endpoint 与本地 fake 384 维 endpoint 下均以 `SIGSEGV` / `analyze_rc=139` 失败。macOS crash report 指向 `lbugjs.node` 的 `lbug::vector_extension::InMemHNSWIndex`，说明崩溃发生在 `CREATE_VECTOR_INDEX` 的 HNSW 原生索引创建阶段，而不是 endpoint/API key/model/dims。隔离安装 `@ladybugdb/core@0.16.1` 和单线程连接仍复现；临时跳过 vector index 后，最小仓库可写入 `embeddings: 1`。因此当前真实阻断是 LadybugDB vector-index 原生崩溃。
  - `scripts/gitnexus-index.sh --embeddings` 已新增 tiny embedding preflight：先在临时 Git 仓库验证 embedding 写入 + `CREATE_VECTOR_INDEX`。`gitnexus@latest` 仍会在 LadybugDB HNSW vector index 原生扩展中段错误；`gitnexus@rc` 的 preflight 已通过。
  - 2026-05-06 21:52 使用 `GITNEXUS_NPX_SPEC=gitnexus@rc` 成功完成主仓 embedding 写入：`1181 files / 29999 nodes / 54587 edges / 1024 clusters / 300 flows / 28219 embeddings`；当时 meta 中记录过 vector-index 状态。
  - 同次运行中，analyze 已成功，但后置 `gitnexus@rc status` 触发 npm/arborist rebuild bug，脚本误恢复旧索引；已从 `.gitnexus.failed-20260506-215230` 恢复成功索引，并修正 `scripts/gitnexus-index.sh`，使 meta stats 已验证后不再因后置 status 失败恢复旧索引。
  - 2026-05-06 23:06 使用 `GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus` 重新完成全量 embedding 写入：`1181 files / 30003 nodes / 54587 edges / 1028 clusters / 300 flows / 28219 embeddings`，并通过 `cypher` 真实计数、`context getDesktopSQLiteSecurityStatus`、`query "desktop sqlite security status"` 和 `npx -y gitnexus@latest status` 验证。
- 当前结论：GitNexus 结构知识图、embedding 数据和读取型 CLI（直接 rc binary）对提交级索引可读，`detect-changes` 可给出当前 dirty worktree 的影响面提示；但当前 worktree 仍存在大量未提交/未跟踪改动，semantic query 不能单独作为需求覆盖或风险放行依据。未提交的新文件与新符号仍需结合 `detect_changes`、`git status --short`、`rg`、直接源码阅读和专项 pytest/Vitest/Playwright 补齐事实。

## 4. 已知限制

| 限制 | 影响 | 使用策略 |
|---|---|---|
| Python scope extraction 对 15 个文件报 `Invalid argument` | 这些文件内部调用边可能不完整 | 对这些文件必须用 `rg` + 直接读源码补盲 |
| JSX/React 使用关系未完整反映为 upstream caller | `ProtectedRoute` 的 `impact upstream` 返回 0，但 `rg` 能看到大量 JSX 使用 | 前端路由/组件影响分析必须配合 `rg` |
| `shape_check` 返回 0 routes | 当前索引未形成可用 API response shape/consumer 对照 | API 契约验证用测试与源码审计，不依赖 shape_check |
| 概念级 `query` 对部分中文/业务查询返回空 | 不能单独作为需求检索依据 | 优先使用 `context/impact/cypher` + `rg` |
| 本机存在多个 GitNexus 仓库索引 | 未带 repo 的 `query` 会因 multi-repo disambiguation 失败 | 所有 query 使用 `--repo Anxin-Smart-Legal-Services`；`scripts/gitnexus-index.sh` 已纳入 repo-scoped query smoke |
| `gitnexus@latest` embedding 重建会在 LadybugDB HNSW vector index 阶段崩溃 | 稳定版不能安全生成主仓 embeddings | 当前 embedding 路径使用 `GITNEXUS_NPX_SPEC=gitnexus@rc`；脚本先跑 tiny preflight，通过后才写主仓 |
| `npx gitnexus@rc` wrapper 可能触发 npm/arborist rebuild bug | 通过 npx 调 rc 的读取命令可能失败，但直接 rc binary 已通过 `context/query/cypher` | 使用 `GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus`；semantic/context 结果仍需用 `rg`、源码阅读和测试补盲 |
| `status: up-to-date` 是 commit 口径，不是 clean-worktree 口径 | 当前工作树很脏，后续新增编辑不会自动入图；GitNexus status 仍可能显示 commit 一致 | 每轮开发前后必须读取 `git status --short`，大改后重跑结构 `analyze --force --skip-agents-md`，并用 `context` 抽查新增符号 |
| 当前索引覆盖本轮工作树且已有 embeddings | 新 helper 和 embedding rows 已进入 `.gitnexus`；direct rc binary 的 `context/query/cypher` 已可读 | 以 `.gitnexus/meta.json`、`status`、direct rc CLI、源码阅读和测试作为硬证据；对 P0 仍以 `rg` + 直接源码阅读 + pytest/Vitest/Playwright 作为事实源 |

触发过 scope extraction 警告的关键文件：

- `backend/scripts/seed_all.py`
- `backend/src/agents/base.py`
- `backend/src/agents/coordinator.py`
- `backend/src/agents/workforce.py`
- `backend/src/api/routes/auth.py`
- `backend/src/api/routes/chat.py`
- `backend/src/api/routes/collaboration.py`
- `backend/src/api/routes/contracts.py`
- `backend/src/api/routes/due_diligence.py`
- `backend/src/services/esign_service.py`
- `backend/src/services/a2ui_intent_handler.py`
- `backend/src/services/chat_service.py`
- `backend/src/services/due_diligence_service.py`
- `backend/src/services/scenario_templates.py`
- `backend/tests/test_external_surface_guards.py`

## 5. 开发前使用规则

1. 改代码前先用 GitNexus `context` 查目标符号。
2. 对共享符号再跑 `impact`，但前端 JSX 调用关系必须补一遍 `rg`。
3. 对上述 Python warning 文件，不把 GitNexus 调用边当完整事实。
4. API shape / response contract 不使用 `shape_check` 作唯一依据。
5. 所有语义查询必须显式指定仓库，例如 `gitnexus query "desktop sqlite security status" --limit 3 --repo Anxin-Smart-Legal-Services`。
6. 每次大改或合并后运行：

```bash
bash scripts/gitnexus-index.sh
```

该脚本默认只重建结构图，并抽查 `runLocalSyncWithDependencies`、`getDesktopSQLiteSecurityStatus`、`sqlite_migrations` 等本轮新增符号。

7. embedding 生成当前使用 `gitnexus@rc`：可显式配置 `GITNEXUS_EMBEDDING_URL`、`GITNEXUS_EMBEDDING_MODEL`、必要时配置 `GITNEXUS_EMBEDDING_DIMS` / `GITNEXUS_EMBEDDING_API_KEY`，或直接复用 `.env` 的 `EMBEDDING_*`，再运行：

```bash
GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
bash scripts/gitnexus-index.sh --embeddings
```

`GITNEXUS_EMBEDDING_URL` 必须是 `/v1` base URL，GitNexus 会自行追加 `/embeddings`。`scripts/gitnexus-index.sh --embeddings` 会先运行 tiny preflight；通过 preflight 后脚本才会备份现有 `.gitnexus` 并执行主仓全量 embedding；如 `meta.json` 仍为 `embeddings: 0` 或 `cypher` 计数不可读，脚本会失败并恢复备份。当前主仓已完成 `28219` 条 embedding rows；direct rc binary 的 `context/query/cypher` 已通过 smoke，`npx gitnexus@rc` wrapper 仍需规避。
