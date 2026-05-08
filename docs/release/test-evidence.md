# 测试证据清单

> 日期：2026-05-08
> 说明：本文件汇总当前已知测试证据和发布前仍需补齐的证据。通过测试不是商业完成的充分条件；必须覆盖对应业务要求才可作为放行依据。

## 1. 已执行证据

### 后端

```bash
cd backend && ./.venv/bin/pytest -q
# 736 passed, 1 skipped, 12 warnings in 44.61s
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
# 30 passed

backend/.venv/bin/pytest -q backend/tests/test_commercial_readiness_gate.py
# 7 passed

backend/.venv/bin/pytest -q backend/tests/test_release_evidence_validation.py
# 9 passed

backend/.venv/bin/ruff check scripts/validate-release-evidence.py backend/tests/test_release_evidence_validation.py
# All checks passed

python3 scripts/validate-release-evidence.py --json docs/release/evidence/static-quality-baseline.md\|static-quality
# {"ok": true, "failures": [], "warnings": []}

node scripts/validate-commercial-delivery-lanes.cjs
# Commercial delivery lanes: OK (8 lanes, status=not_ready, non_complete=7)

bash scripts/release-evidence-secret-scan.sh
# Release evidence secret scan: PASS

bash scripts/commercial-readiness-gate.sh --with-local-tests
# local code-level commands passed: git diff --check, frontend lint, frontend Vitest 13 files / 51 tests,
# frontend build, frontend workstation settings Playwright e2e 9 passed / 1 skipped, frontend agent approval workspace Playwright e2e 5 passed / 5 skipped, desktop cargo check, desktop cargo test 31 passed, desktop network surface gate, desktop installed-profile SQLCipher/keyring smoke, backend mypy zero baseline now 0/0, agent capability policy tests 13 passed, agent governance policy tests 4 passed, unified capability policy engine tests 11 passed, capability route token tests 4 passed, agent governance model tests 8 passed, agent governance service tests 7 passed, agent approval service tests 8 passed, agent approval API tests 7 passed, MCP route governance tests 5 passed, CLI route governance tests 10 passed, LLM route governance tests 6 passed, crawler browser route governance tests 7 passed, approval authorization guard tests 7 passed, MCP connection config policy tests 7 passed, skill governance gate tests 25 passed, RAG full50 runner tests 8 passed,
# RAG quality metrics tests 4 passed, sandbox evidence runner tests 7 passed, payment/e-sign provider/webhook/refund/action-audit tests 62 passed,
# release evidence secret scan tests 2 passed, release worktree inventory tests 2 passed, release evidence artifact validation tests 30 passed,
# commercial readiness gate tests 17 passed, including artifact warning propagation, desktop network gate, workstation e2e gate coverage, Agent approval workspace e2e gate coverage, agent governance gate coverage, unified capability policy engine gate coverage, capability route token gate coverage, agent governance model/service/approval API/MCP/CLI/LLM/browser-crawler route gate coverage, approval authorization gate coverage, and skill evolution gate coverage,
# release evidence validation tests 9 passed, commercial checklist tests 5 passed, commercial delivery lanes tests 3 passed,
# commercial checklist/lane validators + Ruff/JSON smoke, sandbox evidence preflight,
# mobile-device-smoke 8 files / 37 tests + mobile/mini tsc + mobile result-surface/lawyer-conversion guards + Expo config/SDK/Metro config guard + Expo doctor 17/17 + mobile npm audit 0 + mini privacy/navigation boundary + weapp build + WeChat DevTools CLI + refresh-auth/mobile+mini privacy/fake-fallback/design-token guards.
# on a clean baseline, final gate still fails because release docs declare Not ready
# and payment/e-sign/desktop/mobile/agent-governance release evidence remains pending; only remaining warning is missing GITNEXUS_BIN cypher integrity verification.
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
# 56 passed

cd backend && ./.venv/bin/pytest -q tests/test_harness.py -k 'PolicyEngine or AgentMcpToolPolicy'
# 13 passed, 21 deselected

cd backend && ./.venv/bin/pytest -q tests/test_config_commercial_guards.py tests/test_external_surface_guards.py tests/test_harness.py tests/test_cli_route.py tests/test_mode_subscription_guards.py
# 90 passed

cd backend && ./.venv/bin/pytest -q tests/test_config_commercial_guards.py tests/test_harness.py -k 'mcp or PolicyEngine or AgentMcpToolPolicy'
# 20 passed, 23 deselected

cd backend && ./.venv/bin/mypy src/services/mcp_client_service.py src/api/routes/mcp_routes.py src/core/config.py
# Success: no issues found in 3 source files

cd backend && ./.venv/bin/pytest -q tests/test_payment_provider_clients.py tests/test_esign_provider_clients.py tests/test_oa_integration.py
# 19 passed
```

覆盖增量：

- 支付、电签、OA 在 staging/production 不再静默回落 mock/fake；配置缺失或未知 provider 进入明确 503/配置错误路径。本轮复核：`cd backend && ./.venv/bin/pytest -q tests/test_payment_provider_clients.py tests/test_esign_provider_clients.py tests/test_oa_integration.py` -> `19 passed`；`ruff check` 对应 service/test 文件通过。
- 电签 flow 查询、签署链接、撤销和创建已按当前用户组织过滤合同，不再仅凭外部 flow id 操作。
- CLI Key 创建/列表/撤销已绑定真实登录用户，`export` scope 需要对应角色权限，禁止匿名或跨用户管理。
- CLI Key 创建/撤销和 CLI execute 已写入 `AuditLog`；命令失败、scope 缺失、高危命令拒绝和 route-token 拒绝也会留审计轨迹。
- CLI `/execute` 已接入 DB-backed route token：商业环境缺 token fail-closed；`/cli/route-token` 可按 API Key `key_id` consumer 绑定签发短期 token；桌面端 CLI execute 会在调用前申请并传递 `X-Capability-Route-Token`；命令 scope 映射为 `cli:read/chat/export`；`backend/tests/test_cli_route.py` 当前 `10 passed`，`desktop cargo test` 当前 `31 passed`。
- MCP 管理接口收紧到 `manage:system`，独立 MCP Server 在 staging/production 默认 fail-closed；MCP server 创建/更新/删除/连接会写入脱敏 `AuditLog`，只记录 env key 名不记录 secret 值。
- Agent capability policy 已补 fail-closed 基线：未注册工具默认拒绝；`AgentPolicy.allowed_tools` 生效；订阅 feature、角色 permission、绝密模式、设备信任、通道策略和高风险审批上下文可进入 `PolicyContext`；新增服务层 `CapabilityPolicyEngine.can_execute_capability()` 会把订阅、角色、权限、风险级别、隐私模式、数据范围、设备信任、通道策略、CapabilityRoute 状态和 AgentApproval 审批状态串成单次可审计决策，且已覆盖员工浏览器填表拒绝、部门管理员报表 Agent 放行、老板桌面远控审批、超级管理员 MCP route 撤销后失权、外部服务方材料包边界五类权限回归，`backend/tests/test_capability_policy_engine.py` 当前 `11 passed`；agent 看到 MCP tool list 前会先过滤，模型返回 tool call 后执行前会二次判权，拒绝结果结构化回传。
- AgentApproval API 已补正式后端契约：`POST /agent-approvals`、列表/详情、`/pending/count`、`/{id}/audit-events`、`/{id}/audit-export`、`/{id}/workspace-control`、approve/reject/revoke 和 validate 覆盖未登录拒绝、组织/本人 scope、普通员工自批拒绝、管理员批准/撤销、执行前放行/拒绝、审批审计时间线、审批审计 JSON 导出、运行时未接入时暂停/接管/终止 fail-closed 和 payload 脱敏；该切片已加入 `scripts/commercial-readiness-gate.sh --with-local-tests`。
- 审批流授权已补 fail-closed 基线：`backend/tests/test_business_authorization_guards.py -k 'approval or template'` 覆盖单个审批、批量审批、列表 scope、`admin` 组织级 scope、模板写入权限和过期审批拒绝；该切片已加入 `scripts/commercial-readiness-gate.sh --with-local-tests`。
- MCP 外部连接已补商业环境 fail-closed 基线：stdio 默认关闭；stdio command、完整 command line 和 env key 必须显式 allowlist；SSE 必须匹配 scheme/host allowlist；stdio 子进程不再继承全量 `os.environ`。
- 未知订阅 feature 默认拒绝，staging 也拒绝默认 JWT secret。

### 前端/移动/小程序

当前 OpenSpec 记录：

- `cd frontend && npm test` -> latest full local gate `13 files / 51 tests passed`
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
- `cd mobile && npm test` -> latest full local gate `8 files / 37 tests passed`
- `cd mobile && npx tsc --noEmit --module esnext` -> exit 0
- `cd desktop && cargo check` -> exit 0
- `cd desktop && cargo test` -> latest full local gate `31 passed`
- `cd desktop && cargo run -- --self-test` -> built binary self-test JSON, 8 required local/sync tables present, `sqlite_security.encrypted=true`, `sqlite_security.keyring_backed=true`, `sqlite_security.release_blocking=false`
- `bash scripts/desktop-runtime-smoke.sh --with-app-bundle --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log` -> frontend desktop sync slice `2 files / 12 tests passed`; desktop cargo test `16 passed`; cargo check `0`; SQLite migration SQL smoke passes against fresh and legacy `sync_log` temp DB paths; SQLite 100/500 sync performance smoke P95 `12.4ms` / `14.2ms`; unsigned debug macOS `.app` build outputs `desktop/target/debug/bundle/macos/安心法务.app`; debug bundle self-test validates migration/table/security contract; runtime startup smoke exits cleanly; WebView page-load smoke returns `pageLoadFinished=true`, `webviewLabel=main`, `url=tauri://localhost`; structured artifacts written to `docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json` and `docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log`
- `bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` -> exit `0`; first launch migrates seeded plaintext SQLite to SQLCipher and writes an isolated real keyring key; second launch reopens without explicit DB key; ordinary `sqlite3` read is rejected; report has `mode=desktop_installed_profile_smoke`, `status=passed`, `release_evidence_complete=false`, `keyringRoundTrip=true`, `encryptedReopen=true`, `plaintextBackupPresent=true`, `plaintextOpenBlocked=true`
- `bash scripts/desktop-sqlite-security-gate.sh` -> exit `0`; Rust SQLCipher/keyring dependency, frontend package removal, stale capability removal, and self-test security contract are aligned
- `bash scripts/desktop-network-surface-gate.sh` -> exit `0`; Tauri Rust HTTP plugin dependency/registration, frontend `@tauri-apps/plugin-http`, active `http:*` capability permissions, broad `shell:allow-open` / `opener:*` launch permissions, `script-src 'unsafe-eval'`, and broad `img-src https://*` are absent from the checked desktop/WebView surface
- `bash scripts/desktop-release-package.sh --dry-run --out docs/release/evidence/artifacts/desktop-release-package-dry-run-20260507.json --preflight-out docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` -> exit `0`; redacted artifact has `status=dry_run`, `release_ready=false`, `release_evidence_complete=false`, and confirms release packaging is blocked before live signing/notarization inputs exist
- `bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` -> exit `0`; redacted artifact has `release_ready=false` and blockers `tauri.signing_identity`, `codesign.identities`, `notary.credentials`, `release.app.codesign_verify`, `release.app.signature_authority`; `command.hdiutil=pass`, `dmg.hdiutil_create_probe=pass`, `release.app.exists=pass`, `release.dmg.exists=pass`, and `tauri.entitlements.aps_environment=pass`; supporting debug `.app`, runtime transcript and installed-profile report are present
- `cd desktop && cargo tauri build --ci --bundles app,dmg --no-sign` -> first failed inside the Codex sandbox because `hdiutil` / DiskManagement was blocked; the same command then passed in an unsandboxed macOS environment and produced unsigned `.app` plus `desktop/target/release/bundle/dmg/安心法务_1.0.0_aarch64.dmg`.
- `cd desktop && cargo tauri build --ci --bundles app --no-sign` -> exit `0`; unsigned release `.app` was built at `desktop/target/release/bundle/macos/安心法务.app`
- `ANXIN_DESKTOP_RELEASE_APP=desktop/target/release/bundle/macos/安心法务.app bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-unsigned-20260507.json` -> exit `0`; release `.app` and DMG exist, but `release_ready=false` remains blocked by missing signing identity, codesign identity, notarization credentials, code-sign verification, and signature authority. Supporting artifact: `docs/release/evidence/artifacts/desktop-release-unsigned-local-build-20260507.json`
- `bash scripts/desktop-release-runtime-smoke.sh --out docs/release/evidence/artifacts/desktop-release-runtime-unsigned-smoke-20260507.json --ui-log-out docs/release/evidence/artifacts/desktop-release-runtime-ui-smoke-unsigned-20260507.log` -> exit `0`; unsigned release `.app` binary self-test, runtime startup, and WebView page-load handshake passed; artifact has `signed_or_notarized=false` and remains supporting evidence only
- `bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` -> exit `0` in unsandboxed macOS Keychain context; unsigned release `.app` binary migrates a seeded plaintext profile DB to SQLCipher, creates an isolated real keyring key, reopens without explicit DB key, ordinary `sqlite3` read is rejected, and SQLCipher 100 push / 500 pull performance passes with P95 `3.5ms` / `1.8ms`; artifact has `signed_or_notarized=false` and remains supporting evidence only
- `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json` -> mobile Vitest `8 files / 37 tests passed`; mobile tsc `0`; mobile result surface guard `0`; mobile lawyer conversion guard `0`; Expo config/SDK/Metro config guard `0`; Expo doctor `17/17`; mobile npm audit `critical=0/high=0/total=0`; mini-program tsc `0`; mini-program privacy boundary guard `0`; mini-program navigation boundary guard `0`; mini-program `build:weapp` `0`; WeChat DevTools CLI project smoke `0`; refresh auth guard `0`; mobile/mini privacy network guard `0`; fake fallback guard `0`; mini-program design token guard `0`; code-level JSON artifact and manual device evidence template written
- `bash scripts/mobile-device-smoke.sh --skip-mini-build --skip-wechat-devtools` -> exit `0`; follow-up lightweight refresh confirmed mobile Vitest `8 files / 37 tests passed`, mobile TypeScript, mobile result surface guard, mobile lawyer conversion guard, Expo config/doctor, mobile production audit, mini-program TypeScript, mini privacy/navigation guards, fake fallback guard, refresh/privacy network guard, and mini design token guard. This refresh intentionally skipped `build:weapp` and WeChat DevTools CLI, so it remains code-level evidence only.
- `bash scripts/mobile-ios-simulator-smoke.sh --out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.json --log-out docs/release/evidence/artifacts/mobile-ios-simulator-expo-go-smoke-20260508.log --timeout 90` -> exit `0`; iPhone 17 simulator booted, `expo-asset` and Expo Metro config resolved, Expo Go opened local app URL, and Metro recorded `iOS Bundled`; supporting evidence only, `release_evidence_complete=false`

2026-05-08 本轮 UI/UX 与桌面同步切片：

```bash
cd frontend && npx eslint src/components/chat/DocumentDiff.tsx src/components/chat/AnalysisView.tsx src/components/chat/ContextPane.tsx --max-warnings 0
# exit 0

cd frontend && npm test
# latest full local gate: 13 files / 51 tests passed

cd frontend && npm run build
# exit 0; 保留既有 Vite dynamic import / lottie eval / large chunk warnings

cd mobile && npm run typecheck
# exit 0

cd mobile && npm test
# 8 files / 37 tests passed

cd desktop && cargo test sync_engine
# 3 passed
```

覆盖增量：

- `DocumentDiff` 删除静态演示合同条款，只渲染当前会话传入的真实 diff 数据；`AnalysisView` 和 `ContextPane` 已传入真实数据。
- 移动端尽调和知识库搜索入口去掉 `console.log`/伪提交，改为真实 API 调用、加载态和错误态。
- Rust 同步引擎云同步数据面未启用时不再返回 `Ok(0)` 假成功，改为同步状态 Error + 明确错误。

2026-05-08 本轮绝密模式出站熔断切片：

```bash
cd frontend && npm test -- api-adapter.sync.test.ts
# 1 file / 10 tests passed

cd frontend && npm run lint
# exit 0

cd frontend && npm run build
# exit 0; 保留既有 Vite dynamic import / lottie eval / large chunk warnings

cd desktop && cargo check
# exit 0

cd desktop && cargo test
# 19 passed

bash scripts/desktop-network-surface-gate.sh
# exit 0
```

覆盖增量：

- 桌面 Rust IPC 新增统一 data-network guard：TopSecret 下拒绝 CLI execute/key 管理、同步冲突上报、Harness artifact 推送/拉取等外部数据动作。
- 前端桌面本地同步桥在 `top-secret` 下不会发起 `sync/push`、`sync/pull` 或同步冲突上报，`runLocalSyncWithDependencies` 已有 no-fetch 回归。
- `SyncStatus` 冲突弹窗已从双栏原始 JSON 改为字段差异摘要，并把原始数据保留在高级详情折叠；`cd frontend && npm test -- sync-conflict-utils.test.ts` 当前 `1 file / 5 tests passed`，`npm exec tsc -- --noEmit` 与 `npm run lint` 通过。
- `SyncStatus` 桌面工具栏同步/冲突入口已改为稳定按钮尺寸、不换行状态文案和冲突数字胶囊；`cd frontend && npm test -- sync-status-ui.test.ts` 覆盖 `min-h-9/min-w-9/shrink-0`、状态文案和冲突计数 contract；本轮完整 `cd frontend && npm test` 为 `13 files / 51 tests passed`。
- 桌面托盘模式菜单与 tooltip 已移除 emoji 字形依赖，改为纯文本“绝密模式 / 混合模式 / 云端模式”；`cd desktop && cargo test tray` 覆盖三种模式标签和 tooltip 防回归。
- 前端统一 API fetch、新增 WebView 全局 fetch guard 和 WebSocket guard：`cd frontend && npm test -- api.test.ts api-adapter.sync.test.ts` -> `2 files / 17 tests passed`；`cd frontend && npm run lint`、`npm exec tsc -- --noEmit`、`npm run build` 通过。
- Tauri 原生 HTTP 插件、前端 `@tauri-apps/plugin-http`、活跃 `http:*` capability、宽泛 `shell:allow-open` / `opener:*` launch capability 和宽松 CSP 已由 `scripts/desktop-network-surface-gate.sh` 守住。
- 仍不能把绝密模式称为全链路完成：signed/notarized packaged runtime 出站拦截、外部脚本运行时复验和跨设备连续会话证据仍需补。

2026-05-08 本轮桌面主工作站入口切片：

```bash
cd frontend && npm test -- desktopWorkstationModel.test.ts settingsTabs.test.ts
# 2 files / 6 tests passed

cd frontend && npm exec tsc -- --noEmit
# exit 0

cd frontend && npm run lint
# exit 0

cd frontend && npm test
# 13 files / 51 tests passed

cd frontend && npm run build
# exit 0; 保留既有 Vite dynamic import / lottie eval / large chunk warnings

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile
# 9 passed, 1 skipped; mobile-only viewport assertion skipped on chromium by design
```

覆盖增量：

- 设置页新增受控 `工作站` tab，并兼容历史 `/settings?tab=privacy` 跳转到工作站入口；tab 归一化已有单测覆盖。
- 顶部系统操作新增 `工作站` 入口，桌面壳与 Web 预览均可看到本地模型、独立知识库、Skills/MCP、跨端同步和移动远控状态。
- 工作站状态探针已接入现有 Tauri IPC 和受治理前端 API：桌面运行时只读检查本地 LLM 可用性、模型数量、离线任务队列统计、知识库数量/文档数和 MCP 服务/启用/工具缓存统计；非桌面环境继续显示预览态，绝密模式跳过知识库/MCP 数据网络探针，远控安全闸仍为绝密阻断或待验收。
- `desktopWorkstationModel` 明确 TopSecret 下跨端同步和移动远控默认 `blocked` 且 action disabled；非桌面预览下本地模型、同步和移动远控也保持 disabled，只允许知识库与 Skills/MCP 治理入口；Skills/MCP 在 TopSecret 下只能进入治理视图，不诱导外部连接。
- 新增回归测试锁定“绝密模式无 unsafe outbound enabled action”和“非绝密模式才展示连接动作”。
- 新增 Playwright 覆盖 `/settings?tab=workstation`、历史 `/settings?tab=privacy`、tab URL 写回、非桌面预览禁用桌面专属动作、模拟桌面运行时的本地模型/知识库/MCP/队列探针，以及移动宽度下资源卡不越界。
- e2e 暴露并已修复两个 UI/UX 缺口：MCP tab 在 mock 空对象下不再因 `servers.map` 崩溃；Settings 页面在 iPhone 14 视口不再因 tab/page-shell min-content 造成工作站卡片横向溢出。
- 仍不能把桌面主工作站称为完成态：缺完整配置 CRUD、approved MCP connector 演练、移动远控设备配对、signed packaged runtime UI/出站复验证据。

2026-05-08 本轮移动远控控制面与 host 生命周期切片：

```bash
cd backend && ./.venv/bin/pytest -q tests/test_remote_control_fail_closed.py
# 9 passed

cd backend && ./.venv/bin/ruff check src/api/routes/sync.py src/models/sync.py src/services/remote_control_service.py tests/test_remote_control_fail_closed.py alembic/versions/043_add_remote_control_execution_state.py
# All checks passed

cd desktop && cargo test remote_control
# 8 passed; 21 filtered out

cd desktop && cargo check
# exit 0

cd mobile && npm test -- desktop-control api.test.ts
# 2 files passed; 19 tests passed

cd mobile && npm test
# 8 files / 37 tests passed

cd mobile && npm run typecheck
# exit 0
```

覆盖增量：

- `backend/src/models/sync.py`、`backend/alembic/versions/042_add_remote_control_queue.py`、`backend/alembic/versions/043_add_remote_control_execution_state.py` 和 `backend/src/services/remote_control_service.py` 新增 DB-backed 配对、命令队列、host 领取、执行状态和审计事件控制面。
- `/sync/remote-control/pairings` 在混合/云端模式可创建待桌面确认的持久化配对请求，本地/绝密模式继续 403 fail-closed。
- `/sync/remote-control/pairings/{pairing_id}/confirm` 要求桌面设备匹配；确认前不会接受命令。
- `/sync/remote-control/route-token` 通过 CapabilityRoute 为已确认 pairing 签发短期 `desktop:control` route token，命令入队前再次校验 token、consumer、scope、过期和撤销状态。
- `/sync/remote-control/commands` 只在已配对、已授权、已二次确认的前提下写入队列；`/commands/{command_id}/cancel` 可撤销 queued 命令；审计事件会脱敏 token/secret 类字段。
- `/sync/remote-control/commands/claim` 允许桌面 host 在配对和 route token 有效时领取 queued 命令；`/commands/{command_id}/status` 支持 running/completed/failed 状态回传，结果摘要和嵌套 token/secret 字段会递归脱敏。
- `desktop/src/services/remote_control_host.rs` 和 `desktop/src/commands/remote_control.rs` 新增桌面 Tauri IPC host 客户端：确认配对、领取命令、回传 running/completed/failed 状态均使用登录态 bearer token、后端 URL、pairing-scoped route token 和 TopSecret data-network guard；本地测试锁住 URL/payload/状态值、claim 响应解析、safe probe completed、未知命令 failed/unsupported，以及有间隔/次数/limit 上限的 bounded safe-probe host poll 配置与汇总。
- `mobile/app/desktop-control.tsx`、`mobile/src/services/api.ts` 和 `mobile/src/features/desktop-control/model.ts` 新增移动端 safe-probe 入队/状态/取消/审计时间线面：只有 confirmed pairing 同时返回 `desktop_device_id` 与 `pairing_id` 时才启用；点击后先申请短期 route token，再只下发 `desktop.status_probe` / `l2` / 120 秒过期命令；local 模式仍在 fetch 前 fail-closed；UI 显示“入队等待桌面 host 回传”，可刷新命令状态、取消 queued/claimed 探针，并展示脱敏审计时间线，不声明已执行且不渲染命令 payload/metadata 原文。
- 这仍不是远控完成态：当前只证明后端 host lifecycle API、桌面 IPC host 客户端、受限 safe-probe poll 配置、移动端安全探针入队和审计边界，不证明常驻后台 daemon、高风险真实桌面执行、跨设备连续会话、真实移动设备或 signed desktop runtime。

## 2. 证据覆盖矩阵

| 能力 | 当前证据 | 覆盖是否充分 |
|---|---|---|
| 商业发布 gate | `scripts/commercial-readiness-gate.sh` 已建立，默认 quick 模式检查 release artifacts、`commercial-delivery-checklist.json`、`commercial-delivery-lanes.json`、支付/电签 live runner 必需 env 模板字段、最终 GitNexus 索引卫生、dirty worktree release-blocking gate、`docs/release/evidence/*` 的 `Status: complete`、complete evidence 的 Owner/Environment/Date range 元数据、Required Scope 未闭合行、空 artifact reference 和正文 pending/not-ready 冲突、企业智能体治理 runtime evidence、发布证据 secret/PII 扫描、RAG full50 provenance、桌面加密 gate、桌面网络面 gate 和全仓静态质量基线声明；`--with-local-tests` 已覆盖 diff check、frontend lint/test/build、workstation settings Playwright e2e、Agent 治理工作台 Playwright e2e、desktop check/test、desktop network surface gate、desktop installed-profile SQLCipher/keyring smoke、SkillGovernance gate、RAG full50 runner tests、RAG quality tests、sandbox evidence runner tests、payment/e-sign provider/webhook/action-audit tests、release evidence secret scan tests、release artifact/evidence validation tests、commercial readiness gate 回归测试、Ruff、sandbox evidence preflight 和 mobile/mini local smoke | gate 本身充分；当前预期 FAIL，说明商业证据未齐且交付文件尚未提交复验；GitNexus embedding 只在最终提交前做索引卫生，不再作为开发主线排障项 |
| 静态质量基线采集 | `scripts/static-quality-baseline.sh` 可生成 diff/ruff/mypy/frontend/desktop/release-evidence secret+PII/full-repo secret/mock scan 摘要；当前采集 ruff `0`、mypy `0`、mypy zero-baseline gate `0`、release evidence secret/PII scan `0`、secret scan `0`、mock/fallback scan `0`；全仓 Ruff 与 backend mypy 已清零；`docs/release/evidence/static-quality-baseline.md` 已记录 zero-baseline 规则 | 当前发布静态质量证据充分；后续需保持零回退 |
| GitNexus 索引 | `bash scripts/gitnexus-index.sh` 可重建结构图并显式报告 dirty worktree drift；当前 `.gitnexus/meta.json` 有非零 embeddings，但 direct GitNexus CLI repo 解析/cypher 复验失败且索引落后于最新本地提交，不能作为最新提交放行证据；最终 release 前需重新跑 `GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus bash scripts/gitnexus-index.sh --embeddings --clean-first --skip-context-checks`，并要求 `capabilities.vectorSearch.status=vector-index`、`cypher` 真实计数与 meta embeddings 非零且一致、`status` indexed/current commit 一致、`detect-changes` 返回 `No changes detected` | 当前只可作历史上下文和最终索引卫生；semantic query 不能单独放行；主线开发继续以 `rg`、源码阅读、测试、UI/UX 与发布证据为准 |
| 合同状态机 | 单元/API 测试 + webhook 回写测试 | 充分 |
| 电签 provider 代码级协议 | fake `httpx.AsyncClient` 校验官方 header/body/path | 代码级充分，商业级不足 |
| 电签真实沙箱 | `scripts/sandbox-evidence-runner.py` 已提供配置预检和可选 live 采集入口，预检 artifact 会列出 env 之外的 `runtime_prerequisites` 和 `external_evidence_requirements`，避免签署文件/完成 flow、官方回调、重复幂等、失败重试缺失导致 live 步骤被误当完整；live step validator 会把无 signer URL 标为 `pending`、空签署文件下载标为 `fail`；`backend/tests/test_sandbox_evidence_runner.py` 覆盖 live 确认门、脱敏写出、env 模板同步、runtime prerequisite、外部证据槽输出、honest-gating validators 和外部交接文档 live 参数防漂移；当前本地预检缺少真实账号配置，未运行 live | 不充分 |
| 支付 provider 代码级协议 | provider/client/webhook 单测 | 代码级充分，商业级不足 |
| 支付/电签关键动作审计 | `backend/tests/test_commercial_action_audit.py` 覆盖支付下单、关单、退款与电签发起、取签署链接、取消流程均写入 `AuditLog`；签署链接 URL 不进入审计内容 | 代码级充分；真实沙箱仍需验证外部渠道事件与本地审计可对账 |
| 支付真实沙箱 | `scripts/sandbox-evidence-runner.py` 已提供配置预检和可选 live 采集入口，预检 artifact 会列出 env 之外的 `runtime_prerequisites` 和 `external_evidence_requirements`，避免退款/查单/关单订单 ID、官方回调、重复幂等、失败重试、平台 key/cert 轮换缺失导致 live 步骤被误当完整；live step validator 会把退款 `pending` 和关单/取消 `False` 标为 `pending`，不会误报 `pass`；`backend/tests/test_sandbox_evidence_runner.py` 覆盖 live 确认门、脱敏写出、env 模板同步、runtime prerequisite、外部证据槽输出、honest-gating validators 和外部交接文档 live 参数防漂移；当前本地预检缺少真实渠道配置，未运行 live | 不充分 |
| 文档对象存储 | local backend 单测、迁移测试、上传校验测试 | 本地充分，生产 MinIO/S3 不足 |
| IM 首包鉴权/离线 ACK | 后端和前端测试 | 当前切片充分 |
| 桌面同步 | 后端 sync API/service 切片 `24 passed, 6 warnings`；既有 `desktop-runtime-code-smoke-20260507.json` / `desktop-runtime-ui-smoke-20260507.log` 记录过一次 unsigned debug `.app` self-test/runtime/WebView page-load 代码级通过；后续 fresh local 复跑的 debug `.app` runtime startup 在 AppKit registration 前 `Abort trap: 6`，因此不能把 debug bundle runtime 作为当前稳定 passing evidence；Rust IPC 离线任务/同步状态已改为真实读写本地队列与 `sync_log`，不再伪造空 payload 成功；`SyncStatus` 冲突弹窗、工具栏同步/冲突入口和桌面托盘模式文案已完成代码级专业化收口并有回归测试；`bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` 通过本地 installed-profile keyring/reopen/明文迁移/普通 sqlite3 拒读，并写出 release artifact；`scripts/desktop-sqlite-security-gate.sh` 和 `scripts/desktop-network-surface-gate.sh` 当前通过；`scripts/desktop-release-package.sh --dry-run ...`、`scripts/desktop-release-preflight.sh` 和 unsigned release `.app`/DMG preflight 已生成脱敏 artifact，production APNs entitlement、`hdiutil` / DiskManagement probe、release `.app` exists、release DMG exists 均通过；unsigned `app,dmg` 已在 unsandboxed macOS 环境产出；unsigned release packaged runtime self-test/startup/WebView page-load smoke 已通过；unsigned release packaged-profile plaintext-to-SQLCipher/keyring reopen 和 SQLCipher performance smoke 已通过；最新完整本地门禁中全量 Vitest `13 files / 51 tests passed` | 代码级底座、SQLCipher/keyring 安全门禁、桌面网络面门禁、local installed-profile keyring/reopen、migration SQL、SQLite 性能基线、release unsigned app+DMG build、unsigned release packaged runtime smoke、unsigned release packaged-profile/performance smoke、release package dry-run 和 release preflight 充分；signed/notarized installer、signed packaged-profile 迁移、signed packaged runtime 性能和跨设备连续会话不足 |
| RAG 引用与召回质量 | 后端 RBAC/PII、offline smoke 质量基线、live Qdrant smoke、source + 导出文档/chunk/anchor 巡检、前端引用预览/高亮纯函数测试、Playwright 引用点击/预览/高亮已落地；`eval/export_builtin_legal_full50.py` 已从内建法律语料导出 `42` 个法条 chunk 与 `50` 条非 smoke golden；`eval/rag_live_qdrant_full50.py` 已跑通 built-in full50 preflight 和 live Qdrant collection `rag_eval_full50_builtin_20260507`，写出 `rag-full50-built-in-predictions-20260507.json`；`eval/rag_quality.py` 写出 `rag-full50-built-in-metrics-20260507.json`，recall@10 `1.000`、MRR `1.000`、NDCG@10 `0.997`；`backend/tests/eval/test_rag_full50_runner.py` `8 passed`，`backend/tests/eval/test_rag_quality_smoke.py` `4 passed` | 内建 RAG full50 release evidence complete；外部客户知识库评测可作为上线后扩展 |
| 知识图谱大图性能 | 渲染层 >200 节点自动降采样；1k 节点/2k+ 边 Vitest；桌面+移动 Playwright FPS/canvas/screenshot smoke | 代码级充分；真实业务图谱数据预发复跑不足 |
| 知识管理接口 | `knowledge_management` 读写权限分层、无组织用户 fail-closed、出口脱敏和组织分桶隔离测试 `5 passed` | 代码级安全收口；进程内存存储仍非商业持久化形态 |
| 尽调缓存组织隔离 | `SearchCache.org_id` scope + 编排器/deep research 传递 org；`test_investigation_cache_org_scope.py` `3 passed` | 代码级充分；真实预发数据路径仍需复跑 |
| 风险评分解释性 | `risk_scoring_engine` 顶层 `score/factors/explain` + 确定性/兼容性测试 `2 passed`，`RiskAlertPanel` 支持因子贡献条 | 代码级充分；前端真实合同因子数据仍需联调 |
| 爬虫合规入口 | `crawler_service.fetch()` 统一白名单/robots/UA/host 频控；`crawl4ai_service` 与尽调抓取不再绕过；商业环境下浏览器/爬虫 fetch 已在 robots/http 前要求 DB-backed `browser:fetch` route token，撤销 route 后下一次 fetch fail-closed；`test_crawler_compliance.py` `7 passed` | 代码级充分；真实外网 dry-run 被本机 DNS 私网解析防护阻断，发布前需在预发网络复跑 |
| 调查意图路由 | 200 条 JSONL 离线评测集；`test_due_diligence_intent.py` + `test_chat_due_diligence_routing.py` 组合 `13 passed`；意图准确率 `1.000`、企业名抽取准确率 `1.000`（150 条含企业名）；ChatService 已分流尽调/舆情/法规监测 | 代码级充分；真实用户 query 分布上线后需持续采样复核 |
| 案件/任务 | 案件状态机/终态只读/时间线 event_at 语义、任务 owner/assignee/admin 过滤；`test_case_service.py` + `test_lawyer_matching_and_tasks_api.py` 组合 `46 passed` | 代码级核心充分；全矩阵和 Playwright 全流程仍需发布前扩展 |
| 专业服务市场 P0（律师/律所） | local 模式固定拒绝、投标前利益冲突命中 409、同分律师曝光轮询；`test_lawyer_matching_and_tasks_api.py` `17 passed` | 律师/律所代码级核心充分；律所 RBAC 全矩阵、8 API 打勾、1000 次公平报告仍需补；税务师/税务事务所/财务顾问/会计审计仍为后续扩展验收 |
| 全设备智能助手底座 | 后端 LLM/private LLM/MCP/Skills/knowledge 代码基础、桌面 local LLM/SQLCipher/keyring/本地队列、移动隐私模式语义已存在；agent capability policy 现在覆盖未知工具 fail-closed、agent tool allowlist、订阅 feature、角色 permission、绝密模式、设备信任、通道策略、高风险审批上下文，以及 MCP tool list/filter + runtime 二次判权；Harness `policy/agent/{agent}/tools` 已按相同上下文过滤可用工具，避免能力中心展示当前用户/订阅/隐私模式不可执行的工具，`backend/tests/test_agent_governance_policy.py` `4 passed`；服务层 `CapabilityPolicyEngine` 已把订阅、角色、权限、风险级别、隐私模式、数据范围、设备信任、通道策略、CapabilityRoute 状态和 AgentApproval 审批状态合并为单次可审计决策，并新增五类业务权限回归，`backend/tests/test_capability_policy_engine.py` `11 passed`；`capability_route_service` 已补短期 route-token broker，锁住 hash-only storage、scope 校验、撤销后下一次验证失败、过期/未知/missing token fail-closed 和审计事件，`backend/tests/test_capability_routes.py` `4 passed`；Agent 控制面持久化模型与迁移已补，`backend/tests/test_agent_governance_models.py` `8 passed` 锁住模型注册、CapabilityRoute 不保存真实密钥/原始 token、TokenLease 只保存 hash、组织级 route 唯一约束、复合租户外键、跨组织写入失败、审批/审计上下文、审计不可变监听和迁移无敏感列；DB-backed `AgentGovernanceService` 已补 route-token lease 跨实例验证、组织隔离、consumer/scope 拒绝、consumer mismatch、过期 fail-closed、route 撤销后下一次调用失败，以及组织级 CapabilityRoute 策略更新、policy 递归脱敏、禁用撤销 lease 后下一次 token validate fail-closed，`backend/tests/test_agent_governance_service.py` `7 passed`；DB-backed `AgentApprovalService` 已补高风险审批创建、payload 脱敏、授权角色审批/驳回、pending/approved 校验、action/route mismatch 拒绝、过期/撤销 fail-closed、workspace-control 在运行时未接入前 fail-closed、已批准工作室 artifact list/create/export、artifact 递归脱敏、审批状态不被误改和审计事件，`backend/tests/test_agent_approval_service.py` `8 passed`；`/agent-approvals` API 已补创建、列表/详情、pending count、audit-events、audit-export、workspace-control、approve/reject/revoke、validate 和组织 CapabilityRoute list/update 策略 API，`backend/tests/test_agent_approval_api.py` `7 passed` 锁住未登录拒绝、组织/本人 scope、普通员工自批拒绝、管理员批准/撤销、执行前放行/拒绝、审批审计时间线、审批审计 JSON 导出、运行时未接入时暂停/接管/终止 fail-closed、已批准工作室 artifact list/create/export、payload/artifact 脱敏、普通员工不能改组织 route、管理员禁用 route 后撤销 token；前端最小 `Agent 审批工作台` 已补列表/count、状态筛选、风险动作/payload 预览、批准/驳回/撤销、审批审计时间线、审批审计 JSON 导出、已批准行工作室成果查看/新增/导出、已批准行暂停/接管/终止控制拒绝提示、桌面侧边栏入口和移动协作导航高亮，且能力中心最小面板已按组织角色过滤工具：老板/Owner/超级管理员/admin 类角色看全量，普通员工只见基础能力和可申请项，高风险/full-only 工具隐藏；组织能力策略面板已接入 CapabilityRoute list/update，可由全量角色启用/禁用 route；`frontend/e2e/agent-approval-workspace.spec.ts` `5 passed, 5 skipped` 锁住桌面批准动作、审计导出、能力策略可用/可申请/隐藏边界、员工能力中心角色可见性、组织 route 禁用动作、已批准工作室成果记录/导出、运行时未接入控制 fail-closed 和移动端视口不横向溢出；`backend/tests/test_mcp_route_governance.py` `5 passed` 锁住 MCP 开发态兼容、商业环境缺 route token fail-closed、DB route token 放行、route revoke 后拒绝和 consumer mismatch 拒绝；`backend/tests/test_cli_route.py` `10 passed` 锁住 CLI API Key 基线、商业环境缺 route token fail-closed、DB route token 放行、consumer mismatch 拒绝和 `/cli/route-token` 签发；`backend/tests/test_llm_route_governance.py` `6 passed` 锁住 REST chat LLM runtime 商业环境缺 token fail-closed、DB `llm:chat` route token 放行、route revoke 后模型 HTTP 前拒绝、流式模型调用触网前拒绝和 `/chat/route-token` 用户绑定签发；审批流授权已补批量审批、列表 scope、模板写入/读取/使用、过期审批和 admin org-scope 回归，`backend/tests/test_business_authorization_guards.py -k 'approval or template'` 当前 `7 passed`；`skill_evolution_service` 已补本地 proposal/eval/approval/gray/rollback/audit gate，`SkillService` 可按 governed enabled version 过滤，DB-backed `SkillGovernanceService` 和 `/skill-governance` API 已补 proposal/eval/approval/gray/rollback/enabled-version/audit 持久化、组织隔离、API scope、audit export、migration upgrade/downgrade、append-only audit 和 no raw secret/token storage 回归，五个 skill governance gate tests 合计 `25 passed`；MCP 外部连接已补 stdio/SSE/env/command-line allowlist、子进程最小环境和 tool execution route-token gate；CLI `/execute` 已补 DB-backed route-token gate，桌面端会在 execute 前获取并传递 route token；REST chat LLM runtime 已补 DB-backed `llm:chat` route-token gate，Agent 同步/流式模型调用会在真实 HTTP 前校验 route token；桌面 CLI/sync/Harness IPC、本地同步桥、统一 API fetch、WebView 全局 fetch 与 WebSocket 已补 top-secret data-network guard；Tauri/前端 HTTP 插件面和宽松 CSP 已由桌面网络面门禁移除；`/settings?tab=workstation` 已补最小可见入口、TopSecret-safe action model、本地 LLM/模型数量/离线队列、知识库数量/文档数、MCP 服务/启用/工具缓存只读探针和移动远控安全闸；后端 `/sync/remote-control/*` 已补 DB-backed 远控控制面和 host lifecycle API，覆盖持久化配对请求、桌面确认、CapabilityRoute route-token 签发、命令队列、host 领取、running/completed/failed 状态回传、取消、递归脱敏审计以及本地/绝密/缺 token/高风险未二次确认 fail-closed；桌面 Tauri IPC host 客户端已补确认配对、领取命令、回传状态、单次 safe-probe host cycle 和有间隔/次数/limit 上限的 bounded safe-probe poll，并由 TopSecret guard、登录态 bearer token、route token 和 payload/状态/轮询配置单测锁住；移动端新增 `/desktop-control` 状态、safe-probe 入队、状态刷新、queued/claimed 取消和脱敏审计时间线面，local 模式不发网络请求，hybrid/cloud 读取后端安全闸，confirmed pairing 下先签发 route token 再只入队 `desktop.status_probe`，并显示等待桌面 host 回传；Playwright 已覆盖 workstation/legacy privacy route、URL 写回、非桌面禁用态、模拟桌面运行时探针和移动宽度不越界 | 底座存在但商业证据不足；完整桌面主工作站配置面、真正常驻后台 daemon 与高风险真实执行器、真实移动远控跨设备联调、完整策略编辑器、订阅购买联动、部门申请流、CapabilityRoute/TokenLease/AgentApproval/AgentAuditEvent/SkillGovernance WebSocket LLM、完整 browser automation 和 desktop-control 运行时集成、真实 approved MCP connector 演练、完整 Human-in-the-loop 旁听、真实暂停/接管/终止执行效果、artifact 编辑/跨端恢复和桌面 top-secret signed packaged runtime 出站证据仍需测试 |
| 可信会话与 Skills 进化 | OpenSpec、参考分析、TASK-03 和 TASK-12 已把 Codex/Claude 式工作台体验、Skill lifecycle、SkillEvolutionProposal、eval gate、审批和回滚纳入验收；本地服务和测试已覆盖 agent draft proposal、required eval、越权审批拒绝、授权审批、灰度、回滚、审计和 governed Skill 版本过滤；DB-backed `SkillGovernanceService` 与 `/skill-governance` API 已覆盖 proposal、required eval、授权审批、灰度启用、回滚、enabled version 持久化、组织隔离、API scope、audit export、append-only audit、migration upgrade/downgrade 和 no raw secret/token storage；AgentApproval/AgentAuditEvent 模型、DB-backed AgentApprovalService 和 `/agent-approvals` API 已补，锁住高风险审批创建、组织/本人 scope、payload 脱敏、授权角色审批/驳回、撤销、执行前 validate、过期/撤销 fail-closed、action/route 匹配、审计写入、审批审计时间线、审批审计 JSON 导出和 workspace-control 运行时未接入 fail-closed；前端最小审批工作台已覆盖桌面批准动作、审批审计时间线、审批审计 JSON 导出、已批准行工作室成果查看/新增/导出、已批准行控制动作拒绝提示和移动端不横向溢出 | 仍缺前后端长任务事件、runtime 产物生成、artifact 编辑、跨设备恢复、记忆治理、完整 Human-in-the-loop 旁听、真实暂停/接管/终止执行效果、真实执行链路 route/token 失权和商业发布证据 |

2026-05-08 补充：REST chat LLM runtime 已在商业环境加入 DB-backed `llm:chat` route-token gate，`/chat/route-token` 可按当前用户 consumer 签发短期 token，Agent 同步/流式模型调用在真实 HTTP 前校验；`backend/tests/test_llm_route_governance.py` 当前 `6 passed`，覆盖缺 token、DB token 放行、route revoke、流式触网前拒绝和用户绑定签发。WebSocket LLM token pass-through、完整 browser automation 和 desktop-control runtime 仍待闭环。

2026-05-08 补充：`crawler_service.fetch()` 已在商业环境对浏览器/爬虫 fetch 加入 DB-backed `browser:fetch` route-token gate，授权发生在 robots/http 网络访问前；`backend/tests/test_crawler_compliance.py` 当前 `7 passed`，覆盖缺 token fail-closed、DB route-token 放行、route revoke 后下一次触网前拒绝。该证据只关闭 browser/crawler fetch 入口，不替代完整 LLM、browser automation、desktop-control 和真实 connector runtime 证据。

2026-05-08 补充：`AgentApprovalWorkspace` 已扩展为最小 `Agent 治理工作台`，新增 `frontend/src/lib/api.ts` 的 Harness capability policy、CapabilityRoute 策略和 Skill governance 客户端、按角色过滤的能力策略可用/可申请/隐藏工具面板、组织 route 启用/禁用面板、Skill 提案创建/评测/批准/灰度/审计时间线/审计导出 UI，以及 `frontend/e2e/agent-approval-workspace.spec.ts` 桌面与移动回归；最新局部 Playwright 为 `5 passed, 5 skipped`，新增普通员工只见基础能力和可申请项、高风险/full-only 能力隐藏、管理员可禁用组织 route 的角色边界用例，但它仍是代码级证据，不替代真实 runtime/connector/撤销失权商业证据。
| 移动/小程序 | `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json` 当前通过：mobile Vitest `8 files / 37 tests passed`、mobile tsc、mobile result surface guard、mobile lawyer conversion guard、Expo config/SDK/Metro config guard、`npx expo-doctor` `17/17 checks passed`、mobile production `npm audit --omit=dev` `0`、mini-program tsc、mini-program privacy boundary guard、mini-program navigation boundary guard、Taro weapp build、WeChat DevTools CLI project smoke、refresh auth guard、mobile/mini privacy network guard、fake fallback guard、mini-program design token guard，并写出包含 `mobile_expo_doctor=passed`、`mobile_expo_metro_config=passed` 和 `mobile_lawyer_conversion_guard=passed` 的代码级 artifact 与手工设备证据模板；safe-probe status/cancel/audit timeline hardening 后独立 mobile Vitest 为 `8 files / 37 tests passed`；`mobile_npm_audit` artifact 字段记录 `status=passed/critical=0/high=0/total=0`，并由 validator 锁住；`mobile-ios-simulator-expo-go-smoke-20260508.json` 证明 iPhone 17 Simulator + Expo Go 可完成本地 iOS bundle，但该 artifact 明确 `release_evidence_complete=false`；host probe 已写入 `mobile-device-host-probe-20260508.json`，确认本机 iOS Simulator 当前可用且列出 iOS 26.4 设备、ADB 无连接 Android device、Android emulator CLI 不在 PATH、WeChat DevTools 与 WeChat app 存在；移动端弱网 refresh-token 不误清会话已有单测；移动请求层已透传 `X-Privacy-Mode`，且 local 模式在 fetch 前 fail-closed；移动端桌面控制页 local 模式零网络、hybrid/cloud 经 `/sync/remote-control/status` 读取后端安全闸，confirmed pairing 下可入队、刷新和取消 safe-probe，并展示脱敏审计时间线；移动端尽调和知识库搜索提交后渲染页面内结果摘要卡，不再依赖 Alert-only 反馈；移动端找律师已从纯列表升级为匿名咨询转化链路，支持创建真实 `/lawyer/consultations`、展示 AI 匿名摘要、选择律师、创建 `/anonymous-chat/rooms` 并尝试 `/delegate`，且不再跳转不存在的律师详情路由；小程序请求层已透传 `X-Privacy-Mode`，且 local/top-secret 模式在 `Taro.request` 前 fail-closed，登录入口在 `Taro.login` 前阻断；首页/个人中心主入口已移除空路径和“功能开发中”死胡同，统一跳转 AI 助手并预填业务问题；小程序 refresh-token 已区分认证失效和临时刷新失败；消息详情和任务详情已移除 synthetic fallback 数据；`getDetailLoadErrorMessage` 已补字符串 transport error 和 status 优先级用例；移动/小程序已补最小触控 token 底座；小程序语义 token 层已补并迁移首页/聊天/个人中心与 `app.config.ts`；`docs/design/cross-platform-token-drift.md` 已产出三端 token 漂移清单；`docs/release/mobile-error-state-release-notes.md` 已补错误态发布说明草案 | 代码级与 iOS Simulator 支持性 app-run 充分；品牌主色最终统一仍待定；Android、交互式 WeChat DevTools、真实/官方 iOS 设备故事、移动远控跨设备 host 回传、跨设备连续会话或真机证据仍不足 |

## 3. 发布前新增测试要求

- 支付/电签：先用 `scripts/sandbox-evidence-runner.py` 生成脱敏预检/live JSON，再补每个真实渠道至少 7 天沙箱日志，覆盖成功、失败、重试、撤销/退款，并更新 `docs/release/evidence/payment-sandbox.md` / `esign-sandbox.md`。
- 桌面同步：unsigned `app,dmg`、unsigned release packaged runtime smoke 和 unsigned release packaged-profile/performance smoke 已通过；下一步补齐 Tauri signingIdentity、Apple codesign identity 和 notary credentials，再补 signed/notarized installer packaging、signed packaged-profile plaintext-to-SQLCipher 迁移实录、signed packaged runtime performance 和跨设备连续会话证据，并更新 `docs/release/evidence/desktop-runtime-smoke.md`。
- RAG：内建法律知识库 full50 已闭合；后续如果接入外部客户知识库，需要另建外部语料 golden/corpus、复跑 `eval/rag_live_qdrant_full50.py` 和 `eval/rag_quality.py`，并把它作为上线后质量扩展而不是当前内建 RAG 阻断项。
- 案件/任务：已补核心状态机非法跳转、终态只读、owner/assignee/admin 过滤；仍需 Playwright 全流程和全矩阵。
- 专业服务市场：已补律师/律所 P0 的 local 模式拒绝、历史当事人利益冲突投标阻断和同分曝光轮询；仍需律所 RBAC 全矩阵、8 API 打勾、重复评价，并继续扩展税务/财务服务方模型和验收。
- 全设备智能助手：桌面主工作站最小入口、TopSecret-safe action model、浏览器级 Settings 工作站路由/移动宽度证据、本地 LLM/模型数量/离线队列/知识库/MCP 只读探针、移动远控 DB-backed 控制面、后端 host lifecycle API、桌面 IPC host 客户端、bounded safe-probe poll 和移动端状态入口已补；下一步补完整配置 CRUD、真正常驻后台 daemon 与高风险真实执行器、真实移动远控跨设备联调、任意 LLM/Skills/MCP 配置、approved connector 演练和 signed runtime 出站 fail-closed 测试。
- 可信会话与 Skills 进化：本地和 DB-backed SkillEvolutionProposal/eval gate/审批/灰度/回滚测试已补，AgentApproval/AgentAuditEvent 模型、AgentApprovalService、`/agent-approvals` API、`/skill-governance` API 和最小前端 Agent 治理工作台已补，workspace-control 在真实运行时未接入前已 fail-closed；下一步补长任务事件流、任务时间线、工具状态、runtime 产物生成、artifact 编辑、真实暂停/恢复/接管/终止执行效果、跨设备恢复、记忆治理和真实执行链路失权测试。
- 风险调查：缓存 org 隔离、风险分可解释性、robots/UA/频控入口、200 条意图路由评测已有代码级证据；仍需预发网络真实 dry-run。
- 移动/小程序：按 `docs/design/cross-platform-token-drift.md` 决定品牌主色最终统一方向，并补 iPhone/Android/微信开发者工具关键故事手测记录，再更新 `docs/release/evidence/mobile-device-smoke.md`。

## 4. 当前不应作为完成证据的信号

- GitNexus `impact` 低风险：新文件/新 helper 未必入图。
- GitNexus `query` / semantic search：当前 direct rc binary repo 解析/cypher 复验失败；即便复验恢复，semantic search 仍不能单独作为需求覆盖或风险放行证据，必须与源码阅读和测试互证。
- 全量 pytest 通过：未覆盖真实渠道沙箱和真机。
- 前端 build 通过：不证明业务路径真实可用。
- `cargo check` 通过：不证明 Tauri packaged UI runtime push/pull、冲突管理页、重试和签名安装包 profile 真实可用。
- provider fake client 测试通过：不证明商户后台路径、事件名和证书轮换匹配。
