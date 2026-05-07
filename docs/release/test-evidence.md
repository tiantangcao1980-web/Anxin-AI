# 测试证据清单

> 日期：2026-05-08
> 说明：本文件汇总当前已知测试证据和发布前仍需补齐的证据。通过测试不是商业完成的充分条件；必须覆盖对应业务要求才可作为放行依据。

## 1. 已执行证据

### 后端

```bash
cd backend && ./.venv/bin/pytest -q
# 467 passed, 1 skipped, 17 warnings in 36.11s
```

关键切片：

```bash
cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_external_surface_guards.py -k 'esign or fadada'
# 9 passed, 20 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py tests/test_contract_state_machine.py tests/test_contract_review_workflow.py -k 'esign or webhook or contract or provider'
# 56 passed, 8 deselected, 6 warnings

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/esign_service.py src/api/routes/esign.py src/services/esign_webhook_service.py src/services/official_webhook_security.py src/core/config.py src/models/audit.py tests/test_esign_provider_clients.py tests/test_external_surface_guards.py
# All checks passed

python3 -m py_compile scripts/sandbox-evidence-runner.py
# exit 0

backend/.venv/bin/ruff check scripts/sandbox-evidence-runner.py
# All checks passed

python3 scripts/sandbox-evidence-runner.py --scope payment --out /tmp/anxin-payment-sandbox-preflight.json
# redacted preflight JSON written; current local env reports missing payment sandbox credentials and does not run live checks

python3 scripts/sandbox-evidence-runner.py --scope payment --out docs/release/evidence/artifacts/payment-sandbox-preflight-20260507.json
# redacted release artifact written; missing WeChat Pay/Alipay app, merchant/key/callback, and official webhook configuration

python3 scripts/sandbox-evidence-runner.py --scope esign --out /tmp/anxin-esign-sandbox-preflight.json
# redacted preflight JSON written; current local env reports missing e-sign sandbox credentials and does not run live checks

python3 scripts/sandbox-evidence-runner.py --scope esign --out docs/release/evidence/artifacts/esign-sandbox-preflight-20260507.json
# redacted release artifact written; missing e签宝/法大大 app ID, app secret, and official webhook enable configuration

python3 scripts/sandbox-evidence-runner.py --scope wechat_pay --live --out /tmp/anxin-live-should-not-run.json
# exits 2; --live requires --confirm-live-side-effects

python3 -m py_compile eval/rag_live_qdrant_full50.py eval/export_builtin_legal_full50.py
# exit 0

backend/.venv/bin/ruff check eval/rag_live_qdrant_full50.py eval/export_builtin_legal_full50.py eval/rag_quality.py backend/tests/eval/test_rag_full50_runner.py backend/tests/eval/test_rag_quality_smoke.py
# All checks passed

backend/.venv/bin/pytest -q backend/tests/eval/test_rag_full50_runner.py
# 8 passed

backend/.venv/bin/pytest -q backend/tests/eval/test_rag_quality_smoke.py
# 4 passed

backend/.venv/bin/pytest -q backend/tests/test_sandbox_evidence_runner.py
# 7 passed

backend/.venv/bin/pytest -q backend/tests/test_release_evidence_secret_scan.py
# 2 passed

backend/.venv/bin/pytest -q backend/tests/test_release_artifact_validation.py
# 28 passed

backend/.venv/bin/pytest -q backend/tests/test_commercial_readiness_gate.py
# 1 passed

backend/.venv/bin/pytest -q backend/tests/test_release_evidence_validation.py
# 9 passed

backend/.venv/bin/ruff check scripts/validate-release-evidence.py backend/tests/test_release_evidence_validation.py
# All checks passed

python3 scripts/validate-release-evidence.py --json docs/release/evidence/static-quality-baseline.md\|static-quality
# {"ok": true, "failures": [], "warnings": []}

node scripts/validate-commercial-delivery-lanes.cjs
# Commercial delivery lanes: OK (7 lanes, status=not_ready, non_complete=6)

bash scripts/release-evidence-secret-scan.sh
# Release evidence secret scan: PASS

GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
  bash scripts/commercial-readiness-gate.sh --with-local-tests
# local code-level commands passed: git diff --check, frontend lint, frontend Vitest 10 files / 34 tests,
# frontend build, desktop cargo check, desktop cargo test 16 passed, desktop installed-profile SQLCipher/keyring smoke, backend mypy zero baseline now 0/0, RAG full50 runner tests 8 passed,
# RAG quality metrics tests 4 passed, sandbox evidence runner tests 7 passed, payment/e-sign provider/webhook/refund/action-audit tests 61 passed,
# release evidence secret scan tests 2 passed, release worktree inventory tests 2 passed, release evidence artifact validation tests 28 passed,
# commercial readiness gate warning propagation test 1 passed,
# release evidence validation tests 9 passed, commercial checklist tests 5 passed, commercial delivery lanes tests 3 passed,
# commercial checklist/lane validators + Ruff/JSON smoke, sandbox evidence preflight,
# mobile-device-smoke 7 files / 17 tests + mobile/mini tsc + Expo config/SDK guard + weapp build + WeChat DevTools CLI + refresh-auth/fake-fallback/design-token guards.
# on a clean baseline, final gate still fails because release docs declare Not ready
# and payment/e-sign/desktop/mobile release evidence remains pending; any new evidence
# docs must be committed before final clean-worktree/GitNexus rerun.
```

补充扩展切片：

```bash
backend/.venv/bin/pytest -q \
  backend/tests/test_sandbox_evidence_runner.py \
  backend/tests/test_payment_provider_clients.py \
  backend/tests/test_esign_provider_clients.py \
  backend/tests/test_official_webhook_security.py \
  backend/tests/test_webhook_business_events.py \
  backend/tests/test_refund_idempotency.py \
  backend/tests/test_external_surface_guards.py \
  backend/tests/test_commercial_action_audit.py
# 68 passed
```

2026-05-08 本轮商业硬化切片：

```bash
cd backend && ./.venv/bin/ruff check src/api/routes/cli.py src/api/routes/esign.py src/api/routes/integrations.py src/api/routes/mcp_routes.py src/core/config.py src/mcp_server.py src/services/subscription_service.py tests/test_cli_route.py tests/test_config_commercial_guards.py tests/test_external_surface_guards.py tests/test_mode_subscription_guards.py
# All checks passed

cd backend && ./.venv/bin/pytest -q tests/test_config_commercial_guards.py tests/test_external_surface_guards.py tests/test_cli_route.py tests/test_mode_subscription_guards.py
# 48 passed

cd backend && ./.venv/bin/pytest -q tests/test_payment_provider_clients.py tests/test_esign_provider_clients.py tests/test_oa_integration.py tests/test_external_surface_guards.py tests/test_cli_route.py tests/test_config_commercial_guards.py tests/test_mode_subscription_guards.py tests/test_contract_state_machine.py
# 88 passed
```

覆盖增量：

- 支付、电签、OA 在 staging/production 不再静默回落 mock/fake；配置缺失或未知 provider 进入明确 503/配置错误路径。
- 电签 flow 查询、签署链接、撤销和创建已按当前用户组织过滤合同，不再仅凭外部 flow id 操作。
- CLI Key 创建/列表/撤销已绑定真实登录用户，`export` scope 需要对应角色权限，禁止匿名或跨用户管理。
- CLI Key 创建/撤销和 CLI execute 已写入 `AuditLog`；命令失败、scope 缺失和高危命令拒绝也会留审计轨迹。
- MCP 管理接口收紧到 `manage:system`，独立 MCP Server 在 staging/production 默认 fail-closed；MCP server 创建/更新/删除/连接会写入脱敏 `AuditLog`，只记录 env key 名不记录 secret 值。
- 未知订阅 feature 默认拒绝，staging 也拒绝默认 JWT secret。

### 前端/移动/小程序

当前 OpenSpec 记录：

- `cd frontend && npm test` -> `10 files / 34 tests passed`
- `cd frontend && npm run lint` -> exit 0
- `cd frontend && npm run build` -> exit 0，保留既有 Vite warning
- `cd frontend && npm audit --omit=dev --json > docs/release/evidence/artifacts/frontend-npm-audit-prod-20260507.json` -> production dependency audit `0` vulnerabilities after removing unused aggregate `react-force-graph`/stale Tauri SQL frontend package entry, bumping `uuid`/`postcss`, and adding targeted overrides for `lodash`, `lodash-es`, `markdown-it`, and `picomatch` v2/v4 chains
- `cd frontend && npx playwright test e2e/rag-source-links.spec.ts --project=chromium` -> `1 passed`
- `cd frontend && npx playwright test e2e/knowledge-graph-performance.spec.ts --project=chromium` -> `1 passed`
- `cd frontend && npx playwright test e2e/role-access.spec.ts` -> `10 passed, 10 skipped`
- `cd frontend && npx playwright test e2e/document-flows.spec.ts --project=chromium` -> `3 passed`
- `cd frontend && npx playwright test e2e/contract-lifecycle.spec.ts --project=chromium` -> `1 passed`
- `cd mini-program && npx tsc --noEmit --skipLibCheck --noUnusedLocals false` -> exit 0
- `cd mini-program && npm run build:weapp` -> exit 0
- `cd mobile && npm test` -> `7 files / 17 tests passed`
- `cd mobile && npx tsc --noEmit --module esnext` -> exit 0
- `cd desktop && cargo check` -> exit 0
- `cd desktop && cargo test` -> `16 passed`
- `cd desktop && cargo run -- --self-test` -> built binary self-test JSON, 8 required local/sync tables present, `sqlite_security.encrypted=true`, `sqlite_security.keyring_backed=true`, `sqlite_security.release_blocking=false`
- `bash scripts/desktop-runtime-smoke.sh --with-app-bundle --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log` -> frontend desktop sync slice `2 files / 12 tests passed`; desktop cargo test `16 passed`; cargo check `0`; SQLite migration SQL smoke passes against fresh and legacy `sync_log` temp DB paths; SQLite 100/500 sync performance smoke P95 `12.4ms` / `14.2ms`; unsigned debug macOS `.app` build outputs `desktop/target/debug/bundle/macos/安心法务.app`; debug bundle self-test validates migration/table/security contract; runtime startup smoke exits cleanly; WebView page-load smoke returns `pageLoadFinished=true`, `webviewLabel=main`, `url=tauri://localhost`; structured artifacts written to `docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json` and `docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log`
- `bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` -> exit `0`; first launch migrates seeded plaintext SQLite to SQLCipher and writes an isolated real keyring key; second launch reopens without explicit DB key; ordinary `sqlite3` read is rejected; report has `mode=desktop_installed_profile_smoke`, `status=passed`, `release_evidence_complete=false`, `keyringRoundTrip=true`, `encryptedReopen=true`, `plaintextBackupPresent=true`, `plaintextOpenBlocked=true`
- `bash scripts/desktop-sqlite-security-gate.sh` -> exit `0`; Rust SQLCipher/keyring dependency, frontend package removal, stale capability removal, and self-test security contract are aligned
- `bash scripts/desktop-release-package.sh --dry-run --out docs/release/evidence/artifacts/desktop-release-package-dry-run-20260507.json --preflight-out docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` -> exit `0`; redacted artifact has `status=dry_run`, `release_ready=false`, `release_evidence_complete=false`, and confirms release packaging is blocked before live signing/notarization inputs exist
- `bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` -> exit `0`; redacted artifact has `release_ready=false` and blockers `tauri.signing_identity`, `codesign.identities`, `notary.credentials`, `release.app.codesign_verify`, `release.app.signature_authority`; `command.hdiutil=pass`, `dmg.hdiutil_create_probe=pass`, `release.app.exists=pass`, `release.dmg.exists=pass`, and `tauri.entitlements.aps_environment=pass`; supporting debug `.app`, runtime transcript and installed-profile report are present
- `cd desktop && cargo tauri build --ci --bundles app,dmg --no-sign` -> first failed inside the Codex sandbox because `hdiutil` / DiskManagement was blocked; the same command then passed in an unsandboxed macOS environment and produced unsigned `.app` plus `desktop/target/release/bundle/dmg/安心法务_1.0.0_aarch64.dmg`.
- `cd desktop && cargo tauri build --ci --bundles app --no-sign` -> exit `0`; unsigned release `.app` was built at `desktop/target/release/bundle/macos/安心法务.app`
- `ANXIN_DESKTOP_RELEASE_APP=desktop/target/release/bundle/macos/安心法务.app bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-unsigned-20260507.json` -> exit `0`; release `.app` and DMG exist, but `release_ready=false` remains blocked by missing signing identity, codesign identity, notarization credentials, code-sign verification, and signature authority. Supporting artifact: `docs/release/evidence/artifacts/desktop-release-unsigned-local-build-20260507.json`
- `bash scripts/desktop-release-runtime-smoke.sh --out docs/release/evidence/artifacts/desktop-release-runtime-unsigned-smoke-20260507.json --ui-log-out docs/release/evidence/artifacts/desktop-release-runtime-ui-smoke-unsigned-20260507.log` -> exit `0`; unsigned release `.app` binary self-test, runtime startup, and WebView page-load handshake passed; artifact has `signed_or_notarized=false` and remains supporting evidence only
- `bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` -> exit `0` in unsandboxed macOS Keychain context; unsigned release `.app` binary migrates a seeded plaintext profile DB to SQLCipher, creates an isolated real keyring key, reopens without explicit DB key, ordinary `sqlite3` read is rejected, and SQLCipher 100 push / 500 pull performance passes with P95 `3.5ms` / `1.8ms`; artifact has `signed_or_notarized=false` and remains supporting evidence only
- `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json` -> mobile Vitest `7 files / 17 tests passed`; mobile tsc `0`; Expo config/SDK guard `0`; Expo doctor `17/17`; mobile npm audit `critical=0/high=0/total=0`; mini-program tsc `0`; mini-program `build:weapp` `0`; WeChat DevTools CLI project smoke `0`; refresh auth guard `0`; fake fallback guard `0`; mini-program design token guard `0`; code-level JSON artifact and manual device evidence template written

2026-05-08 本轮 UI/UX 与桌面同步切片：

```bash
cd frontend && npx eslint src/components/chat/DocumentDiff.tsx src/components/chat/AnalysisView.tsx src/components/chat/ContextPane.tsx --max-warnings 0
# exit 0

cd frontend && npm test
# 10 files / 34 tests passed

cd frontend && npm run build
# exit 0; 保留既有 Vite dynamic import / lottie eval / large chunk warnings

cd mobile && npm run typecheck
# exit 0

cd mobile && npm test
# 7 files / 17 tests passed

cd desktop && cargo test sync_engine
# 3 passed
```

覆盖增量：

- `DocumentDiff` 删除静态演示合同条款，只渲染当前会话传入的真实 diff 数据；`AnalysisView` 和 `ContextPane` 已传入真实数据。
- 移动端尽调和知识库搜索入口去掉 `console.log`/伪提交，改为真实 API 调用、加载态和错误态。
- Rust 同步引擎云同步数据面未启用时不再返回 `Ok(0)` 假成功，改为同步状态 Error + 明确错误。

## 2. 证据覆盖矩阵

| 能力 | 当前证据 | 覆盖是否充分 |
|---|---|---|
| 商业发布 gate | `scripts/commercial-readiness-gate.sh` 已建立，默认 quick 模式检查 release artifacts、`commercial-delivery-checklist.json`、`commercial-delivery-lanes.json`、支付/电签 live runner 必需 env 模板字段、GitNexus embeddings、dirty worktree release-blocking gate、`docs/release/evidence/*` 的 `Status: complete`、complete evidence 的 Owner/Environment/Date range 元数据、Required Scope 未闭合行、空 artifact reference 和正文 pending/not-ready 冲突、发布证据 secret/PII 扫描、RAG full50 provenance、桌面加密 gate 和全仓静态质量基线声明；`--with-local-tests` 已覆盖 diff check、frontend lint/test/build、desktop check/test、desktop installed-profile SQLCipher/keyring smoke、RAG full50 runner tests、RAG quality tests、sandbox evidence runner tests、payment/e-sign provider/webhook/action-audit tests、release evidence secret scan tests、release artifact/evidence validation tests、commercial readiness gate warning propagation test、Ruff、sandbox evidence preflight 和 mobile/mini local smoke | gate 本身充分；当前预期 FAIL，说明商业证据未齐且交付文件尚未提交复验 |
| 静态质量基线采集 | `scripts/static-quality-baseline.sh` 可生成 diff/ruff/mypy/frontend/desktop/release-evidence secret+PII/full-repo secret/mock scan 摘要；当前采集 ruff `0`、mypy `0`、mypy zero-baseline gate `0`、release evidence secret/PII scan `0`、secret scan `0`、mock/fallback scan `0`；全仓 Ruff 与 backend mypy 已清零；`docs/release/evidence/static-quality-baseline.md` 已记录 zero-baseline 规则 | 当前发布静态质量证据充分；后续需保持零回退 |
| GitNexus 索引 | `bash scripts/gitnexus-index.sh` 可重建结构图并显式报告 dirty worktree drift；`GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus bash scripts/gitnexus-index.sh --embeddings --skip-context-checks` 已在本轮本地交付提交后生成主仓 embedding；当前 `.gitnexus/meta.json` 为约 `1.3k files / 32.5k nodes / 58.8k edges / 300 flows / 30.4k embeddings`，`capabilities.vectorSearch.status=vector-index`，精确统计以最新 meta 为准；`cypher` 真实计数为非零，`status` 显示 indexed/current commit 一致，`detect-changes` 返回 `No changes detected`；`scripts/gitnexus-index.sh` 已纳入 repo-scoped query smoke | 结构、embedding 数据和 direct rc 读取充分；semantic query 不能单独放行；后续新增提交仍需重建/复验并用 `rg` 和测试补盲 |
| 合同状态机 | 单元/API 测试 + webhook 回写测试 | 充分 |
| 电签 provider 代码级协议 | fake `httpx.AsyncClient` 校验官方 header/body/path | 代码级充分，商业级不足 |
| 电签真实沙箱 | `scripts/sandbox-evidence-runner.py` 已提供配置预检和可选 live 采集入口，预检 artifact 会列出 env 之外的 `runtime_prerequisites` 和 `external_evidence_requirements`，避免签署文件/完成 flow、官方回调、重复幂等、失败重试缺失导致 live 步骤被误当完整；live step validator 会把无 signer URL 标为 `pending`、空签署文件下载标为 `fail`；`backend/tests/test_sandbox_evidence_runner.py` 覆盖 live 确认门、脱敏写出、env 模板同步、runtime prerequisite、外部证据槽输出、honest-gating validators 和外部交接文档 live 参数防漂移；当前本地预检缺少真实账号配置，未运行 live | 不充分 |
| 支付 provider 代码级协议 | provider/client/webhook 单测 | 代码级充分，商业级不足 |
| 支付/电签关键动作审计 | `backend/tests/test_commercial_action_audit.py` 覆盖支付下单、关单、退款与电签发起、取签署链接、取消流程均写入 `AuditLog`；签署链接 URL 不进入审计内容 | 代码级充分；真实沙箱仍需验证外部渠道事件与本地审计可对账 |
| 支付真实沙箱 | `scripts/sandbox-evidence-runner.py` 已提供配置预检和可选 live 采集入口，预检 artifact 会列出 env 之外的 `runtime_prerequisites` 和 `external_evidence_requirements`，避免退款/查单/关单订单 ID、官方回调、重复幂等、失败重试、平台 key/cert 轮换缺失导致 live 步骤被误当完整；live step validator 会把退款 `pending` 和关单/取消 `False` 标为 `pending`，不会误报 `pass`；`backend/tests/test_sandbox_evidence_runner.py` 覆盖 live 确认门、脱敏写出、env 模板同步、runtime prerequisite、外部证据槽输出、honest-gating validators 和外部交接文档 live 参数防漂移；当前本地预检缺少真实渠道配置，未运行 live | 不充分 |
| 文档对象存储 | local backend 单测、迁移测试、上传校验测试 | 本地充分，生产 MinIO/S3 不足 |
| IM 首包鉴权/离线 ACK | 后端和前端测试 | 当前切片充分 |
| 桌面同步 | 后端 sync API/service 切片 `24 passed, 6 warnings`；既有 `desktop-runtime-code-smoke-20260507.json` / `desktop-runtime-ui-smoke-20260507.log` 记录过一次 unsigned debug `.app` self-test/runtime/WebView page-load 代码级通过；后续 fresh local 复跑的 debug `.app` runtime startup 在 AppKit registration 前 `Abort trap: 6`，因此不能把 debug bundle runtime 作为当前稳定 passing evidence；Rust IPC 离线任务/同步状态已改为真实读写本地队列与 `sync_log`，不再伪造空 payload 成功；`bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` 通过本地 installed-profile keyring/reopen/明文迁移/普通 sqlite3 拒读，并写出 release artifact；`scripts/desktop-sqlite-security-gate.sh` 当前通过；`scripts/desktop-release-package.sh --dry-run ...`、`scripts/desktop-release-preflight.sh` 和 unsigned release `.app`/DMG preflight 已生成脱敏 artifact，production APNs entitlement、`hdiutil` / DiskManagement probe、release `.app` exists、release DMG exists 均通过；unsigned `app,dmg` 已在 unsandboxed macOS 环境产出；unsigned release packaged runtime self-test/startup/WebView page-load smoke 已通过；unsigned release packaged-profile plaintext-to-SQLCipher/keyring reopen 和 SQLCipher performance smoke 已通过；全量 Vitest `10 files / 34 tests passed` | 代码级底座、SQLCipher/keyring 安全门禁、local installed-profile keyring/reopen、migration SQL、SQLite 性能基线、release unsigned app+DMG build、unsigned release packaged runtime smoke、unsigned release packaged-profile/performance smoke、release package dry-run 和 release preflight 充分；signed/notarized installer、signed packaged-profile 迁移、signed packaged runtime 性能和跨设备连续会话不足 |
| RAG 引用与召回质量 | 后端 RBAC/PII、offline smoke 质量基线、live Qdrant smoke、source + 导出文档/chunk/anchor 巡检、前端引用预览/高亮纯函数测试、Playwright 引用点击/预览/高亮已落地；`eval/export_builtin_legal_full50.py` 已从内建法律语料导出 `42` 个法条 chunk 与 `50` 条非 smoke golden；`eval/rag_live_qdrant_full50.py` 已跑通 built-in full50 preflight 和 live Qdrant collection `rag_eval_full50_builtin_20260507`，写出 `rag-full50-built-in-predictions-20260507.json`；`eval/rag_quality.py` 写出 `rag-full50-built-in-metrics-20260507.json`，recall@10 `1.000`、MRR `1.000`、NDCG@10 `0.997`；`backend/tests/eval/test_rag_full50_runner.py` `8 passed`，`backend/tests/eval/test_rag_quality_smoke.py` `4 passed` | 内建 RAG full50 release evidence complete；外部客户知识库评测可作为上线后扩展 |
| 知识图谱大图性能 | 渲染层 >200 节点自动降采样；1k 节点/2k+ 边 Vitest；桌面+移动 Playwright FPS/canvas/screenshot smoke | 代码级充分；真实业务图谱数据预发复跑不足 |
| 知识管理接口 | `knowledge_management` 读写权限分层、无组织用户 fail-closed、出口脱敏和组织分桶隔离测试 `5 passed` | 代码级安全收口；进程内存存储仍非商业持久化形态 |
| 尽调缓存组织隔离 | `SearchCache.org_id` scope + 编排器/deep research 传递 org；`test_investigation_cache_org_scope.py` `3 passed` | 代码级充分；真实预发数据路径仍需复跑 |
| 风险评分解释性 | `risk_scoring_engine` 顶层 `score/factors/explain` + 确定性/兼容性测试 `2 passed`，`RiskAlertPanel` 支持因子贡献条 | 代码级充分；前端真实合同因子数据仍需联调 |
| 爬虫合规入口 | `crawler_service.fetch()` 统一白名单/robots/UA/host 频控；`crawl4ai_service` 与尽调抓取不再绕过；`test_crawler_compliance.py` `4 passed` | 代码级充分；真实外网 dry-run 被本机 DNS 私网解析防护阻断，发布前需在预发网络复跑 |
| 调查意图路由 | 200 条 JSONL 离线评测集；`test_due_diligence_intent.py` + `test_chat_due_diligence_routing.py` 组合 `13 passed`；意图准确率 `1.000`、企业名抽取准确率 `1.000`（150 条含企业名）；ChatService 已分流尽调/舆情/法规监测 | 代码级充分；真实用户 query 分布上线后需持续采样复核 |
| 案件/任务 | 案件状态机/终态只读/时间线 event_at 语义、任务 owner/assignee/admin 过滤；`test_case_service.py` + `test_lawyer_matching_and_tasks_api.py` 组合 `46 passed` | 代码级核心充分；全矩阵和 Playwright 全流程仍需发布前扩展 |
| 专业服务市场 P0（律师/律所） | local 模式固定拒绝、投标前利益冲突命中 409、同分律师曝光轮询；`test_lawyer_matching_and_tasks_api.py` `17 passed` | 律师/律所代码级核心充分；律所 RBAC 全矩阵、8 API 打勾、1000 次公平报告仍需补；税务师/税务事务所/财务顾问/会计审计仍为后续扩展验收 |
| 全设备智能助手底座 | 后端 LLM/private LLM/MCP/Skills/knowledge 代码基础、桌面 local LLM/SQLCipher/keyring/本地队列、移动隐私模式语义已存在 | 底座存在但商业证据不足；桌面主工作站配置面、移动远控桌面、任意 LLM/Skills/MCP 组织策略、独立本地知识库体验和绝密模式出站拦截仍需测试 |
| 可信会话与 Skills 进化 | OpenSpec、参考分析、TASK-03 和 TASK-12 已把 Codex/Claude 式工作台体验、Skill lifecycle、SkillEvolutionProposal、eval gate、审批和回滚纳入验收 | 当前仍是规范和任务级证据；缺前后端长任务事件、artifact 编辑、跨设备恢复、Skill 评测/审批/回滚代码测试 |
| 移动/小程序 | `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json` 当前通过：mobile Vitest `7 files / 17 tests passed`、mobile tsc、Expo config/SDK dependency guard、`npx expo-doctor` `17/17 checks passed`、mobile production `npm audit --omit=dev` `0`、mini-program tsc、Taro weapp build、WeChat DevTools CLI project smoke、refresh auth guard、fake fallback guard、mini-program design token guard，并写出包含 `mobile_expo_doctor=passed` 的代码级 artifact 与手工设备证据模板；`mobile_npm_audit` artifact 字段记录 `status=passed/critical=0/high=0/total=0`，并由 validator 锁住；host probe 已写入 `mobile-device-host-probe-20260508.json`，确认本机 iOS Simulator 当前可用且列出 iOS 26.4 设备、ADB 无连接 Android device、Android emulator CLI 不在 PATH、WeChat DevTools 与 WeChat app 存在；移动端弱网 refresh-token 不误清会话已有单测；小程序 refresh-token 已区分认证失效和临时刷新失败；消息详情和任务详情已移除 synthetic fallback 数据；`getDetailLoadErrorMessage` 已补字符串 transport error 和 status 优先级用例；移动/小程序已补最小触控 token 底座；小程序语义 token 层已补并迁移首页/聊天/个人中心与 `app.config.ts`；`docs/design/cross-platform-token-drift.md` 已产出三端 token 漂移清单；`docs/release/mobile-error-state-release-notes.md` 已补错误态发布说明草案 | 代码级充分；品牌主色最终统一仍待定；iOS app-run、Android、交互式 WeChat DevTools 或真机证据仍不足 |

## 3. 发布前新增测试要求

- 支付/电签：先用 `scripts/sandbox-evidence-runner.py` 生成脱敏预检/live JSON，再补每个真实渠道至少 7 天沙箱日志，覆盖成功、失败、重试、撤销/退款，并更新 `docs/release/evidence/payment-sandbox.md` / `esign-sandbox.md`。
- 桌面同步：unsigned `app,dmg`、unsigned release packaged runtime smoke 和 unsigned release packaged-profile/performance smoke 已通过；下一步补齐 Tauri signingIdentity、Apple codesign identity 和 notary credentials，再补 signed/notarized installer packaging、signed packaged-profile plaintext-to-SQLCipher 迁移实录、signed packaged runtime performance 和跨设备连续会话证据，并更新 `docs/release/evidence/desktop-runtime-smoke.md`。
- RAG：内建法律知识库 full50 已闭合；后续如果接入外部客户知识库，需要另建外部语料 golden/corpus、复跑 `eval/rag_live_qdrant_full50.py` 和 `eval/rag_quality.py`，并把它作为上线后质量扩展而不是当前内建 RAG 阻断项。
- 案件/任务：已补核心状态机非法跳转、终态只读、owner/assignee/admin 过滤；仍需 Playwright 全流程和全矩阵。
- 专业服务市场：已补律师/律所 P0 的 local 模式拒绝、历史当事人利益冲突投标阻断和同分曝光轮询；仍需律所 RBAC 全矩阵、8 API 打勾、重复评价，并继续扩展税务/财务服务方模型和验收。
- 全设备智能助手：补桌面主工作站配置面、移动远控桌面、任意 LLM/Skills/MCP 配置、独立本地知识库和绝密模式出站 fail-closed 测试。
- 可信会话与 Skills 进化：补长任务事件流、任务时间线、工具状态、artifact 编辑、暂停/恢复/接管、跨设备恢复、SkillEvolutionProposal、eval gate、审批、灰度和回滚测试。
- 风险调查：缓存 org 隔离、风险分可解释性、robots/UA/频控入口、200 条意图路由评测已有代码级证据；仍需预发网络真实 dry-run。
- 移动/小程序：按 `docs/design/cross-platform-token-drift.md` 决定品牌主色最终统一方向，并补 iPhone/Android/微信开发者工具关键故事手测记录，再更新 `docs/release/evidence/mobile-device-smoke.md`。

## 4. 当前不应作为完成证据的信号

- GitNexus `impact` 低风险：新文件/新 helper 未必入图。
- GitNexus `query` / semantic search：direct rc binary 已可读，但 semantic search 仍不能单独作为需求覆盖或风险放行证据，必须与源码阅读和测试互证。
- 全量 pytest 通过：未覆盖真实渠道沙箱和真机。
- 前端 build 通过：不证明业务路径真实可用。
- `cargo check` 通过：不证明 Tauri packaged UI runtime push/pull、冲突管理页、重试和签名安装包 profile 真实可用。
- provider fake client 测试通过：不证明商户后台路径、事件名和证书轮换匹配。
