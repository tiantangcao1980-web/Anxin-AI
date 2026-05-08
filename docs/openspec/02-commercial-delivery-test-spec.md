# OpenSpec — 商业交付测试规范

> 日期：2026-05-08
> 目的：约束从现状到商业交付的验证门槛。没有测试证据，不进入下一波次。

## 0. 产品定位与全设备智能助手验收门槛

商业候选版不仅验证代码能跑，还必须验证产品定位真的落地：

| 验收域 | 必须证明 | 最低证据 |
|---|---|---|
| 中小企业需求方 | 老板/高管/行政/人事/财务等用户能完成日常法务、财务、税务、合规、舆情问题处理 | persona E2E 或 transcript：咨询、文书、风险分级、材料包、历史记录 |
| 重大事项专业转介 | 高风险事项不会被 AI 静默当作普通问答结束 | 后端规则/模型测试 + 前端卡片 E2E：风险摘要、服务类型、授权范围、专业服务方匹配 |
| 专业服务方 | 律师/律所 P0 真实可用，税务师/税务事务所/财务顾问/会计审计预留模型和权限 | provider_type/schema/API 测试；利益冲突、SLA、评价、线索来源和结算证据 |
| 舆情与获客 | 舆情不是普通资讯流，推广获客不是隐性广告 | 舆情告警、处置建议、转人工、线索归因、广告/推荐标识和反骚扰测试 |
| 桌面主工作站 | 桌面可安装、可本地安全运行、可配置模型/知识库/Skills/MCP | packaged runtime smoke、SQLCipher/keyring、安全门禁、本地 LLM/KB/config UI 或 transcript |
| 移动随身助手 | 移动端具备核心咨询、审批、通知、材料查看和跨设备继续能力 | iOS/Android 真机或模拟器 transcript + `scripts/mobile-device-smoke.sh` |
| 移动远程控制桌面 | 手机可安全控制已配对桌面客户端，而不是伪 UI | 设备配对、命令下发、状态回传、取消/撤销、敏感动作二次确认、审计日志和通道安全测试 |
| 任意模型/Skills/MCP | 用户或组织可配置 provider/endpoint/model/key、Skills、MCP Server 和权限策略 | 配置 CRUD、组织隔离、权限拒绝、MCP stdio/SSE/env/command-line allowlist、调用日志、失败回滚和隐私模式回归 |
| 独立知识库/本地模型安全 | 本地/绝密模式下数据默认不出设备 | 云调用/MCP 出站拦截测试、MCP 子进程最小环境、日志脱敏、来源引用、本地索引和本地模型调用证据 |
| 可信会话体验 | 长任务像 Codex/Claude 式可信工作台一样过程可见、证据可点、artifact 可编辑、可打断可恢复 | 任务时间线、工具状态、引用链接、artifact 编辑、暂停/恢复/取消/接管、跨设备继续 E2E |
| Skills 进化与智能体自我改进 | Skill 可以从失败中改进，但不能无评测、无审批自改生产能力 | SkillEvolutionProposal、eval gate、审批、灰度、回滚、审计日志和越权拒绝测试 |
| 企业智能体治理 | 组织默认只开放基础能力，完整能力受订阅、老板/Owner、超级管理员、角色、风险级别和设备信任约束 | 权限矩阵、审批流、审计日志、拒绝原因、撤销/回滚测试 |
| 协作式多智能体控制面 | Agent/Worker 不持有真实密钥，任务在可见工作室中可旁听、暂停、接管、终止 | AgentManager/Team/Worker/Human/ChannelPolicy/CapabilityRoute/TokenLease/Approval/AuditEvent 模型与迁移测试；Gateway consumer token 与 allowed route 回归 |

本节任一 P0 证据缺失时，不得把项目描述为“全面智能助手商业交付完成态”；只能描述为“已有基础，待发布验收”。

## 1. 全局质量门槛

每次合并候选必须运行：

```bash
bash scripts/commercial-readiness-gate.sh --quick
cd backend && ./.venv/bin/pytest -q tests
cd backend && ./.venv/bin/ruff check src tests
cd backend && ./.venv/bin/mypy src
cd frontend && npm run lint
cd frontend && npm run build
bash scripts/mobile-device-smoke.sh
# mobile: 7 files / 17 tests passed; mobile tsc exit 0; Expo doctor 17/17; mobile npm audit exit 0; mini-program tsc/build exit 0; WeChat DevTools CLI project smoke exit 0; refresh-auth/fake-fallback/design-token guards exit 0

python3 scripts/sandbox-evidence-runner.py --scope payment --out /tmp/anxin-payment-sandbox-preflight.json
python3 scripts/sandbox-evidence-runner.py --scope esign --out /tmp/anxin-esign-sandbox-preflight.json
# preflight only; live sandbox calls require --live --confirm-live-side-effects
cd desktop && cargo check
cd desktop && cargo test
cd desktop && cargo tauri build --debug --no-bundle --ci
bash scripts/desktop-runtime-smoke.sh --with-app-bundle
bash scripts/desktop-sqlite-security-gate.sh
bash scripts/desktop-network-surface-gate.sh
```

当前全仓 Ruff 与 backend mypy 均已清零，商业交付路线采用分层零回退基线：

- P0/P1 改动文件不得新增 ruff/mypy 错误。
- 每个任务至少收口其 touched files 的类型/静态检查问题。
- 全仓 ruff/mypy 必须保持零回退；任何非零结果都应阻断 release readiness。

`scripts/commercial-readiness-gate.sh` 是商业发布硬门禁，不是普通开发门禁。当前它应当失败；GitNexus embeddings 零值阻断已解除，内建 RAG full50 release evidence 已完成，移动/小程序本地 smoke 已建立，但支付/电签真实沙箱、桌面 signed/notarized runtime 和移动真机仍未闭合。外部证据模板在 `docs/release/evidence/`，gate 只接受 `Status: complete`。

静态质量基线可用以下命令采集；当前 evidence 要求 backend mypy `0` 错误，并由 `scripts/mypy-baseline-check.sh` 的 zero-baseline gate 保护：

```bash
bash scripts/static-quality-baseline.sh --out /tmp/anxin-static-quality-baseline.md
```

### 2026-05-06 验证记录

本轮 V2 守卫、匿名聊天/A2UI 加固、对象存储、支付/电签 webhook 幂等与自动重试底座、微信/支付宝官方回调验签、e签宝官方 HMAC 回调验签、法大大 FASC webhook 验签、e签宝/法大大 provider 客户端、退款幂等、订阅状态机、合同生命周期状态机、合同版本 diff/回滚、合同审查并发/超时、合同附件对象存储生命周期、webhook processing lock、双客户端订阅前端展示、双端套餐过滤、IM 离线 ACK 前后端协议、小程序微信真实登录链路已运行：

```bash
cd backend && ./.venv/bin/pytest -q
# 467 passed, 1 skipped, 17 warnings in 36.11s

cd backend && ./.venv/bin/pytest -q tests/test_subscription_state_machine.py tests/test_refund_idempotency.py tests/test_payment_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py tests/test_mode_subscription_guards.py tests/test_im_offline_messages.py tests/test_im_websocket_auth.py -k 'subscription or refund or payment or webhook or metrics or provider or event or esignbao or mode or im or websocket'
# 58 passed, 6 deselected in 11.79s

cd backend && ./.venv/bin/pytest -q tests/test_auth_surface_hardening.py
# 18 passed

cd backend && ./.venv/bin/pytest -q tests/test_auth_surface_hardening.py -k 'wechat_mini or oauth_callback'
# 4 passed, 14 deselected

cd backend && ./.venv/bin/pytest -q tests/test_document_upload_validation_api.py
# 8 passed

cd backend && ./.venv/bin/pytest -q tests/test_document_upload_validation_api.py tests/test_document_authorization_api.py tests/test_object_storage_service.py tests/test_document_generation_api.py tests/test_security_authorization_guards.py
# 28 passed

cd backend && ./.venv/bin/pytest -q tests/test_template_engine_security.py
# 7 passed

cd backend && ./.venv/bin/pytest -q tests/test_template_engine_security.py tests/test_document_upload_validation_api.py tests/test_document_generation_api.py
# 17 passed

cd backend && ./.venv/bin/pytest -q tests/test_collaboration_offline_merge.py
# 4 passed

cd backend && ./.venv/bin/pytest -q tests/test_collaboration_offline_merge.py tests/test_chat.py -k collaboration tests/test_security_authorization_guards.py
# 10 passed, 32 deselected

cd backend && ./.venv/bin/pytest -q tests/test_document_export_limits.py tests/test_contract_authorization_api.py -k 'download or export'
# 4 passed, 6 deselected

cd backend && ./.venv/bin/pytest -q tests/test_document_object_storage_migration.py tests/test_object_storage_service.py
# 7 passed

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

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_external_surface_guards.py -k 'esign or fadada'
# 9 passed, 20 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_contract_review_workflow.py tests/test_contract_state_machine.py tests/test_contract_versions.py tests/test_contract_version_migration.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py -k 'contract or esign or webhook or version'
# 54 passed, 9 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py tests/test_contract_state_machine.py tests/test_contract_review_workflow.py -k 'esign or webhook or contract or provider'
# 56 passed, 8 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_contract_attachments.py tests/test_contract_attachment_migration.py
# 5 passed, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_contract_attachments.py tests/test_contract_attachment_migration.py tests/test_contract_authorization_api.py tests/test_object_storage_service.py tests/test_document_upload_validation_api.py -k 'contract or object_storage or upload'
# 26 passed, 6 warnings

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/api/routes/documents.py src/api/routes/knowledge.py src/api/routes/contracts.py src/api/routes/upload_validation.py src/core/validators.py tests/test_document_upload_validation_api.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/template_engine.py src/api/routes/contracts.py tests/test_template_engine_security.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/collaboration_service.py tests/test_collaboration_offline_merge.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/document_export.py src/api/routes/contracts.py tests/test_document_export_limits.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 alembic/versions/029_add_document_object_storage_fields.py tests/test_document_object_storage_migration.py
# All checks passed

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

cd backend && ./.venv/bin/pytest -q tests/test_investigation_cache_org_scope.py tests/test_mode_subscription_guards.py tests/test_anonymous_chat_token_split.py
# 19 passed, 13 warnings

cd backend && ./.venv/bin/pytest -q tests/test_risk_scoring_engine.py
# 2 passed

cd backend && ./.venv/bin/pytest -q tests/test_crawler_compliance.py
# 4 passed

cd backend && ./.venv/bin/pytest -q tests/test_due_diligence_intent.py tests/test_chat_due_diligence_routing.py
# 13 passed；200 条 JSONL 评测集，intent_accuracy=1.000，company_accuracy=1.000，ChatService 分流已覆盖

cd backend && ./.venv/bin/pytest -q tests/test_case_service.py tests/test_lawyer_matching_and_tasks_api.py
# 46 passed, 6 warnings；案件状态机、任务 owner、律师市场 local guard/冲突阻断/公平轮询

cd backend && ./.venv/bin/ruff check --select F401,F821 src/models/investigation.py src/core/database.py src/services/investigation_data_store.py src/services/investigation_orchestrator.py src/services/deep_research_engine.py src/api/routes/due_diligence.py tests/test_investigation_cache_org_scope.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,F821 src/config/crawler.py src/services/crawler_service.py src/services/crawl4ai_service.py src/services/due_diligence_service.py src/api/routes/lic.py tests/test_crawler_compliance.py
# All checks passed

cd backend && RUN_COMPREHENSIVE_FLOW=1 ./.venv/bin/pytest -q tests/test_comprehensive_flow.py
# opt-in workforce smoke；默认回归跳过，避免等待外部/长任务

cd frontend && npm run lint
# exit 0

cd frontend && npm test -- --run src/hooks/useIMWebSocket.test.ts
# 3 passed

cd frontend && npm test -- --run src/pages/MySubscription.test.ts
# 3 passed

cd frontend && npm test -- --run src/pages/Pricing.test.ts src/pages/MySubscription.test.ts
# 5 passed

cd frontend && npm test
# latest full local gate: 12 files / 45 tests passed

cd frontend && npm run build
# exit 0, tsc && vite build

cd mini-program && npx tsc --noEmit --skipLibCheck --noUnusedLocals false
# exit 0

rg "fallbackNews|mock 数据|假新闻|mock_token_|登录成功（体验模式）|/auth/wechat-login" mini-program/src backend/src backend/tests
# no matches

cd mini-program && npm run build:weapp
# exit 0

bash scripts/mobile-device-smoke.sh
# mobile Vitest 7 files / 17 tests passed; mobile tsc exit 0; Expo doctor 17/17; mobile npm audit exit 0; mini-program tsc/build exit 0; WeChat DevTools CLI project smoke exit 0; refresh-auth/fake-fallback/design-token guards exit 0

cd frontend && npx playwright test e2e/role-access.spec.ts
# 10 passed, 10 skipped

cd frontend && npx playwright test e2e/document-flows.spec.ts --project=chromium
# 3 passed

cd frontend && npx playwright test e2e/contract-lifecycle.spec.ts --project=chromium
# 1 passed

cd frontend && npx playwright test e2e/rag-source-links.spec.ts --project=chromium
# 1 passed

./backend/.venv/bin/python eval/rag_live_qdrant_smoke.py --out eval/rag_live_predictions_smoke.json --collection rag_eval_smoke_live_20260506
# indexed_chunks=15, predictions=10

python3 eval/rag_quality.py --golden eval/rag_golden_set.jsonl --predictions eval/rag_live_predictions_smoke.json --out eval/rag_live_baseline_smoke.json --smoke --run-label rag-live-qdrant-smoke-2026-05-06
# recall@10=1.000, MRR=1.000, NDCG@10=1.000

python3 eval/export_builtin_legal_full50.py --corpus eval/legal_full50_corpus.jsonl --golden eval/legal_full50_golden.jsonl
python3 eval/rag_live_qdrant_full50.py --golden eval/legal_full50_golden.jsonl --corpus eval/legal_full50_corpus.jsonl --preflight-only --out docs/release/evidence/artifacts/rag-full50-built-in-preflight-YYYYMMDD.json --run-label built-in-legal-full50-YYYYMMDD
./backend/.venv/bin/python eval/rag_live_qdrant_full50.py --golden eval/legal_full50_golden.jsonl --corpus eval/legal_full50_corpus.jsonl --out docs/release/evidence/artifacts/rag-full50-built-in-predictions-YYYYMMDD.json --collection <rag_eval_full50_builtin_collection> --run-label built-in-legal-full50-YYYYMMDD
python3 eval/rag_quality.py --golden eval/legal_full50_golden.jsonl --predictions docs/release/evidence/artifacts/rag-full50-built-in-predictions-YYYYMMDD.json --out docs/release/evidence/artifacts/rag-full50-built-in-metrics-YYYYMMDD.json --run-label built-in-legal-full50-YYYYMMDD
# current release evidence is complete in docs/release/evidence/rag-full50-live-baseline.md; external customer corpus evaluation is a post-release quality expansion
```

注意：Playwright 本地运行前必须确认 `3001` 没有旧 Vite 进程；`reuseExistingServer` 会复用旧进程，可能导致测试跑到旧路由。

## 2. 任务级测试矩阵

| 波次 | 任务 | 必跑测试 |
|---|---|---|
| 1 | auth | `pytest -k "auth or reset or captcha or redis"`；`npm test` storage/auth-client；新增 token/captcha/localStorage E2E |
| 1 | mode-llm | `pytest -k "llm or mode or privacy or guard"`；`role-access.spec.ts`；Pro 路由 E2E |
| 2 | agents/chat | websocket 鉴权、断线恢复、prompt 注入、A2UI 流式事件、长任务时间线、artifact 创建、暂停/恢复、Skill 进化提案 |
| 2 | a2ui | 协议版本兼容、未知组件降级、action 权限 |
| 2 | contract/esign | webhook 签名、业务回写、合同状态机、版本 diff/回滚、审查锁/超时、webhook 并发幂等、附件持久化、e签宝/法大大 provider 客户端、法大大 FASC webhook；真实商户沙箱单列为发布阻断证据 |
| 2 | document | 上传/下载/删除/版本、对象存储、模板沙箱、协作离线合并；`e2e/document-flows.spec.ts` 覆盖上传、下载、双人协作故事 |
| 2 | rag | 召回质量、引用回链、权限过滤、PII 脱敏 |
| 3 | case/task | 案件状态机、终态只读、任务 owner/assignee/admin、组织隔离 |
| 3 | professional-services/acquisition | 专业服务方 provider_type、资质认证、利益冲突阻断、SLA、评价、线索来源、推广/获客标识、结算隔离；P0 覆盖律师/律所，P1/P2 覆盖税务/财务服务方 |
| 3 | lawyer-market | local 模式拒绝、利益冲突阻断、投标/接受/评价权限、重复评价、撮合公平；作为 professional-services 的 P0 子集保留 |
| 3 | risk/investigation/sentiment | 匿名咨询 token 分离、尽调缓存 org 维度、抓取合规、风险解释、意图路由评测、舆情告警、处置建议、转专业服务材料包 |
| 3 | billing-im | 支付状态机、退款幂等、IM 首包鉴权、RTC 参与者授权 |
| 4 | desktop-assistant-runtime | Tauri smoke、快捷键、拖拽分析、本地模式状态、本地 LLM、本地知识库、Skills/MCP 配置入口、执行审计 |
| 4 | sync | push/pull/conflict、离线队列重放、跨端连续会话、远程命令队列、审批确认、执行状态回传 |
| 4 | mobile | `scripts/mobile-device-smoke.sh`、底部 Tab、safe-area、44px 触控、mock token/fallback 清理、消息/任务详情错误态、跨设备会话继续 |
| 4 | mobile-remote-control | 设备配对、远程命令、状态回传、取消/撤销、敏感动作二次确认、审计日志、端到端通道安全 |
| 4 | extensibility | LLM provider/endpoint/model/key、Skills、MCP Server、知识库配置 CRUD；组织隔离、权限拒绝、隐私模式出站拦截、调用日志；Skill 版本、评测、审批、回滚 |
| 5 | enterprise-agent-governance | 订阅、角色、能力、风险级别、隐私模式、设备信任、通信策略、审批状态的统一决策；Agent/Worker consumer token；真实密钥不进 agent；人类可介入工作室；Skill Evolution Gate |

## 3. GitNexus 使用门槛

每个任务开工前：

```bash
GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
bash scripts/gitnexus-index.sh --skip-context-checks
/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
  context -r Anxin-Smart-Legal-Services <target-symbol>
```

对共享符号：

```bash
/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
  impact -r Anxin-Smart-Legal-Services <symbol> --direction upstream
```

补充规则：

- 如果目标在 13 个 Python warning 文件内，必须额外 `rg`。
- 如果目标是 React JSX 组件使用关系，必须额外 `rg "<ComponentName>" frontend/src frontend/e2e`。
- 本机有多个 GitNexus 仓库索引；所有 `query` 必须显式指定 `--repo Anxin-Smart-Legal-Services`，否则会因 multi-repo disambiguation 失败。
- 如果 GitNexus `query --repo Anxin-Smart-Legal-Services` 返回空，不代表代码不存在；必须使用 `rg`、源码阅读和测试复查。
- 当前 GitNexus embeddings 已生成，direct rc binary 的 `context/query/cypher` 已通过 smoke；semantic query 仍不作为发布放行证据，必须与源码和测试互证。

## 4. 发布前验收

商业交付候选版必须满足：

- 后端全量 pytest 通过。
- 前端 lint/build 通过，关键 E2E 通过。
- 移动端本地 smoke 通过，且真机/微信开发者工具关键路径证据齐全。
- 桌面端 `cargo check`、`cargo test`、`cargo tauri build --debug --no-bundle --ci`、`bash scripts/desktop-runtime-smoke.sh --with-app-bundle`、`bash scripts/desktop-sqlite-security-gate.sh`、`bash scripts/desktop-network-surface-gate.sh` 通过，必要 smoke 手测通过。
- 中小企业需求方、专业服务方、舆情/获客、重大事项转专业人士路径有 persona 级验收证据。
- 桌面主工作站、本地模型、本地/组织知识库、用户可配置 LLM/Skills/MCP 和移动远程控制桌面路径有可复跑证据。
- 本地/绝密模式下云端模型、外部 MCP、同步上传和远控外传默认 fail-closed，且日志不泄露密钥、材料正文或 session token。
- 企业智能体治理覆盖基础能力默认开放、高级能力订阅开放、老板/Owner 和超级管理员完整控制、普通员工边界、外部服务方材料包边界。
- 多智能体控制面证明 Agent/Worker 只持有短期 consumer token，真实密钥由网关/密钥服务托管，撤销 route 后 agent 立即失权。
- 可信会话体验证明长任务过程可见、证据可点、artifact 可编辑、用户可暂停/恢复/接管，失败后保留可恢复状态。
- Skills 进化证明 agent 只能提出改进、生成测试和提交审批；未评测、未审批或已回滚 Skill 不能进入可执行状态。
- P0 安全项全部关闭。
- 支付/电签/对象存储/同步均有失败、重试、幂等测试。
- 所有 release 文档齐全。
- 已知风险有 owner、优先级、验证计划和回滚方案。
