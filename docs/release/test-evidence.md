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
# frontend build, frontend workstation settings Playwright e2e 9 passed / 1 skipped, frontend agent approval workspace Playwright e2e 5 passed / 5 skipped, desktop cargo check, desktop cargo test 31 passed, desktop network surface gate, desktop installed-profile SQLCipher/keyring smoke, backend mypy zero baseline now 0/0, agent capability policy tests 13 passed, agent governance policy tests 4 passed, unified capability policy engine tests 11 passed, capability route token tests 4 passed, agent governance model tests 8 passed, agent governance service tests 8 passed, agent approval service tests 10 passed, agent approval API tests 9 passed, MCP route governance tests 5 passed, CLI route governance tests 10 passed, LLM route governance tests 6 passed, crawler browser route governance tests 7 passed, approval authorization guard tests 7 passed, MCP connection config policy tests 7 passed, skill governance gate tests 25 passed, RAG full50 runner tests 8 passed,
# RAG quality metrics tests 4 passed, sandbox evidence runner tests 7 passed, payment/e-sign provider/webhook/refund/action-audit tests 62 passed,
# release evidence secret scan tests 2 passed, release worktree inventory tests 2 passed, release evidence artifact validation tests 30 passed,
# commercial readiness gate tests 17 passed, including artifact warning propagation, desktop network gate, workstation e2e gate coverage, Agent approval workspace e2e gate coverage, agent governance gate coverage, unified capability policy engine gate coverage, capability route token gate coverage, agent governance model/service/approval API/MCP/CLI/LLM/browser-crawler route gate coverage, approval authorization gate coverage, and skill evolution gate coverage,
# release evidence validation tests 9 passed, commercial checklist tests 5 passed, commercial delivery lanes tests 3 passed,
# commercial checklist/lane validators + Ruff/JSON smoke, sandbox evidence preflight,
# mobile-device-smoke 8 files / 37 tests + mobile/mini tsc + mobile result-surface/lawyer-conversion guards + Expo config/SDK/Metro config guard + Expo doctor 17/17 + mobile npm audit 0 + mini privacy/navigation boundary + weapp build + WeChat DevTools CLI + refresh-auth/mobile+mini privacy/fake-fallback/design-token guards.
# on a clean baseline, final gate still fails because release docs declare Not ready
```

2026-05-09 desktop strict Clippy gate wiring: `scripts/commercial-readiness-gate.sh --with-local-tests` now runs `desktop strict Clippy`; targeted verification `cd desktop && cargo clippy --all-targets -- -D warnings` passed, and the commercial readiness gate regression suite remains the source of truth for the exact test count.

```bash
bash scripts/agent-governance-smoke.sh --out docs/release/evidence/artifacts/agent-governance-code-smoke-20260509.json
# exit 0; docs scan passed; agent capability policy 13 passed; backend governance regressions 141 passed with local runtime control rehearsal and cross-process revocation rehearsal;
# approval authorization guards 7 passed; MCP connection config policy 7 passed; approved connector local rehearsal 1 passed; cross-process revocation local rehearsal 1 passed; desktop remote-control host 14 passed;
# frontend Skill connector credential model 4 passed; frontend Agent governance workspace Playwright 6 passed / 6 skipped;
# artifact records release_evidence_complete=false
# and runtime_evidence_complete=false, so agent-governance-smoke.md remains Status: pending.
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
- AgentApproval API 已补正式后端契约：`POST /agent-approvals`、列表/详情、`/pending/count`、`/{id}/audit-events`、`/{id}/audit-export`、`/{id}/workspace-control`、approve/reject/revoke 和 validate 覆盖未登录拒绝、组织/本人 scope、普通员工自批拒绝、管理员批准/撤销、执行前放行/拒绝、审批审计时间线、审批审计 JSON 导出、已授权 observe 只读旁听快照、运行时未接入时暂停/接管/终止 fail-closed 和 payload 脱敏；该切片已加入 `scripts/commercial-readiness-gate.sh --with-local-tests`。
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
- `bash scripts/desktop-runtime-smoke.sh --with-app-bundle --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log` -> frontend desktop sync slice `2 files / 12 tests passed`; desktop cargo test `16 passed`; cargo check `0`; SQLite migration SQL smoke passes against fresh and legacy `sync_log` temp DB paths; SQLite 100/500 sync performance smoke P95 `12.4ms` / `14.2ms`; unsigned debug macOS `.app` build outputs `desktop/target/debug/bundle/macos/安心智能助手.app`; debug bundle self-test validates migration/table/security contract; runtime startup smoke exits cleanly; WebView page-load smoke returns `pageLoadFinished=true`, `webviewLabel=main`, `url=tauri://localhost`; structured artifacts written to `docs/release/evidence/artifacts/desktop-runtime-code-smoke-20260507.json` and `docs/release/evidence/artifacts/desktop-runtime-ui-smoke-20260507.log`
- `bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` -> exit `0`; first launch migrates seeded plaintext SQLite to SQLCipher and writes an isolated real keyring key; second launch reopens without explicit DB key; ordinary `sqlite3` read is rejected; report has `mode=desktop_installed_profile_smoke`, `status=passed`, `release_evidence_complete=false`, `keyringRoundTrip=true`, `encryptedReopen=true`, `plaintextBackupPresent=true`, `plaintextOpenBlocked=true`
- `bash scripts/desktop-sqlite-security-gate.sh` -> exit `0`; Rust SQLCipher/keyring dependency, frontend package removal, stale capability removal, and self-test security contract are aligned
- `bash scripts/desktop-network-surface-gate.sh` -> exit `0`; Tauri Rust HTTP plugin dependency/registration, frontend `@tauri-apps/plugin-http`, active `http:*` capability permissions, broad `shell:allow-open` / `opener:*` launch permissions, `script-src 'unsafe-eval'`, broad `img-src https://*` and missing local LLM endpoint guard are absent from the checked desktop/WebView surface
- `bash scripts/desktop-release-package.sh --dry-run --out docs/release/evidence/artifacts/desktop-release-package-dry-run-20260507.json --preflight-out docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` -> exit `0`; redacted artifact has `status=dry_run`, `release_ready=false`, `release_evidence_complete=false`, and confirms release packaging is blocked before live signing/notarization inputs exist
- `bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-20260507.json` -> exit `0`; redacted artifact has `release_ready=false` and blockers `tauri.signing_identity`, `codesign.identities`, `notary.credentials`, `release.app.codesign_verify`, `release.app.signature_authority`; `command.hdiutil=pass`, `dmg.hdiutil_create_probe=pass`, `release.app.exists=pass`, `release.dmg.exists=pass`, and `tauri.entitlements.aps_environment=pass`; supporting debug `.app`, runtime transcript and installed-profile report are present
- `cd desktop && cargo tauri build --ci --bundles app,dmg --no-sign` -> first failed inside the Codex sandbox because `hdiutil` / DiskManagement was blocked; the same command then passed in an unsandboxed macOS environment and produced unsigned `.app` plus `desktop/target/release/bundle/dmg/安心智能助手_1.0.0_aarch64.dmg`.
- `cd desktop && cargo tauri build --ci --bundles app --no-sign` -> exit `0`; unsigned release `.app` was built at `desktop/target/release/bundle/macos/安心智能助手.app`
- `ANXIN_DESKTOP_RELEASE_APP=desktop/target/release/bundle/macos/安心智能助手.app bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-unsigned-20260507.json` -> exit `0`; release `.app` and DMG exist, but `release_ready=false` remains blocked by missing signing identity, codesign identity, notarization credentials, code-sign verification, and signature authority. Supporting artifact: `docs/release/evidence/artifacts/desktop-release-unsigned-local-build-20260507.json`
- `bash scripts/desktop-release-runtime-smoke.sh --out docs/release/evidence/artifacts/desktop-release-runtime-unsigned-smoke-20260509.json --ui-log-out docs/release/evidence/artifacts/desktop-release-runtime-ui-smoke-unsigned-20260509.log` -> exit `0`; unsigned release `.app` binary self-test, packaged sync code smoke, packaged sync loopback smoke, runtime startup, and WebView page-load handshake passed; loopback backend observed bearer-auth push of `2` records, accepted `1`, conflicted `1`, wrote `1` pull record, and advanced cursor to `13`; artifact has `signed_or_notarized=false`, `release_sync_code_smoke=passed`, `release_sync_loopback_smoke=passed`, and remains supporting evidence only
- `bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` -> exit `0` in unsandboxed macOS Keychain context; unsigned release `.app` binary migrates a seeded plaintext profile DB to SQLCipher, creates an isolated real keyring key, reopens without explicit DB key, ordinary `sqlite3` read is rejected, and SQLCipher 100 push / 500 pull performance passes with P95 `3.5ms` / `1.8ms`; artifact has `signed_or_notarized=false` and remains supporting evidence only
- `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json` -> mobile Vitest `8 files / 37 tests passed`; mobile tsc `0`; mobile result surface guard `0`; mobile lawyer conversion guard `0`; Expo config/SDK/Metro config guard `0`; Expo doctor `17/17`; mobile npm audit `critical=0/high=0/total=0`; mini-program tsc `0`; mini-program privacy boundary guard `0`; mini-program navigation boundary guard `0`; mini-program `build:weapp` `0`; WeChat DevTools CLI project smoke `0`; refresh auth guard `0`; mobile/mini privacy network guard `0`; fake fallback guard `0`; mini-program design token guard `0`; code-level JSON artifact and manual device evidence template written
- `bash scripts/mobile-device-smoke.sh --out /tmp/anxin-mobile-mini-code-smoke-gate.json --manual-template-out /tmp/anxin-mobile-device-manual-template-gate.json` -> exit `0`; mobile Vitest `8 files / 37 tests passed`; Expo doctor `17/17`; mobile production `npm audit --omit=dev` `critical=0/high=0/total=0` after adding targeted overrides for `@babel/plugin-transform-modules-systemjs@7.29.4` and `fast-uri@3.1.2`; mini-program TypeScript/privacy/navigation/build/design-token guards pass; WeChat DevTools CLI project smoke exits `0` with `touristappid`; release artifact copied into `docs/release/evidence/artifacts/mobile-mini-code-smoke-20260509.json`.
- `bash scripts/uni-mobile-smoke.sh --out docs/release/evidence/artifacts/uni-mobile-base-smoke-20260509.json` -> exit `0`; `scripts/uni-mobile-migration-guard.sh` passes legacy freeze / uni-app base file / package script checks, `apps/uni-mobile` typecheck, `5 files / 12 tests passed`, production `npm audit --omit=dev` `0`, H5 build, and WeChat Mini Program build pass; artifact records `release_evidence_complete=false` because DCloud App cloud build/signing and real device/DevTools evidence remain pending.
- `bash scripts/cross-device-continuation-smoke.sh --out docs/release/evidence/artifacts/cross-device-continuation-code-smoke-20260509.json` -> exit `0`; backend sync continuation `5 passed`, frontend desktop sync adapter `10 passed`, uni-app sync client contract `5 passed`; artifact records `release_evidence_complete=false` / `runtime_evidence_complete=false` because signed desktop package, real/official iOS/Android, interactive WeChat/DCloud, and shared staging-account continuation evidence remain pending.
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
# 6 passed

cd desktop && cargo test sync
# 7 passed
```

覆盖增量：

- `DocumentDiff` 删除静态演示合同条款，只渲染当前会话传入的真实 diff 数据；`AnalysisView` 和 `ContextPane` 已传入真实数据。
- 移动端尽调和知识库搜索入口去掉 `console.log`/伪提交，改为真实 API 调用、加载态和错误态。
- Rust 后台 `SyncEngine` 云同步数据面未启用时不再返回 `Ok(0)` 假成功，改为同步状态 Error + 明确错误；Rust IPC `trigger_sync` fallback 已补代码级 SQLCipher push/pull 数据面，失败进入退避/人工处理，不再只返回 unsupported。

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
- 仍不能把桌面主工作站称为完成态：缺 approved MCP connector runtime 证据、移动远控设备配对、signed packaged runtime UI/出站复验证据。

2026-05-09 goal-driven 桌面优先补充：

```bash
cd frontend && npm test -- desktopWorkstationModel.test.ts
# 1 file / 4 tests passed

cd frontend && npm run lint
# exit 0

cd frontend && npm exec tsc -- --noEmit
# exit 0

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile
# 11 passed, 1 skipped

cd frontend && npm run build
# exit 0; 保留既有 lottie eval / dynamic import / large chunk warnings

cd desktop && cargo check
# exit 0

cd desktop && cargo test app_mode
# 2 passed; 31 filtered out
```

覆盖增量：

- 新增 `docs/release/goal-contract-commercial-readiness.md`，把桌面优先、功能优先、外部 API 可替换测试数据、Done/Stop 条款写成持久目标契约。
- `DesktopWorkstationPanel` 新增“工作站配置”写入面：桌面 runtime 可切换绝密/混合/云端模式，保存后端环境地址；非桌面预览保持只读。
- `desktopWorkstationModel` 与 `desktop/src/commands/app_mode.rs` 均新增后端 URL 校验，只接受完整 http/https 地址，拒绝 `local://api` 等运行时占位地址；IPC 直接调用也不能绕过前端。
- Playwright 覆盖桌面 runtime mock 下的模式切换、后端地址保存、绝密模式远控阻断和移动宽度回归。
- 这只关闭最小桌面配置写入面；真实 approved MCP connector runtime 证据、signed packaged runtime 和跨设备真机证据仍保持阻断。

2026-05-09 桌面远控 host 可见控制面补充：

```bash
cd frontend && npm test -- desktopWorkstationModel.test.ts
# 1 file / 9 tests passed

cd frontend && npm exec tsc -- --noEmit
# exit 0

cd frontend && npm run lint
# exit 0

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium
# 7 passed, 1 skipped

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=mobile
# 8 passed
```

覆盖增量：

- `/settings?tab=workstation` 新增桌面“移动远控 host”可见控制面，展示配对、权限范围、执行状态、取消入口和脱敏审计时间线。
- 待确认 pairing 只能启用“确认配对”，通过 Tauri IPC `remote_control_confirm_pairing` 走桌面 host 客户端；已确认 pairing 只能先申请短期 `desktop:control` route token，再通过 `remote_control_run_host_cycle` 执行 safe-probe host cycle。
- queued/claimed 命令取消入口只从审计事件中定位未终态 command id，不展示 route token、不渲染命令 payload/metadata 原文；终态命令不会启用取消。
- TopSecret 和非桌面预览保持所有 host 操作 disabled，避免浏览器预览或绝密模式误触远控出站动作。
- 该证据是 mock runtime / 浏览器级控制面证据，不替代 signed runtime daemon 常驻运行、真实跨设备 host callback、高风险真实执行器或真机证据。

2026-05-09 桌面运行配置持久化补充：

```bash
cd desktop && cargo test runtime_config
# 5 passed; 33 filtered out

cd desktop && cargo test app_mode
# 2 passed; 36 filtered out

cd desktop && cargo check
# exit 0
```

覆盖增量：

- 新增 `desktop/src/services/runtime_config.rs`，把桌面运行模式与后端环境地址保存到 Tauri app data 下的 secret-free `runtime-config.json`，并支持 `ANXIN_DESKTOP_RUNTIME_CONFIG_PATH` 便于本地/CI 隔离验证。
- `desktop/src/lib.rs` 启动时加载该配置并同步到 Rust 共享状态；`desktop/src/commands/app_mode.rs` 的模式切换和后端地址保存会先校验、落盘，再更新内存状态。
- 单测锁住 http/https 规范化、拒绝 `local://api`/`file://`、配置 round-trip 不含 token/secret 字段，以及 TopSecret 加载后同步状态为 `Offline`。
- 这只关闭桌面工作站模式/后端环境的跨重启持久化；第三方 connector 真实密钥联调、signed packaged runtime 和跨设备证据仍保持阻断。

2026-05-09 桌面工作站配置档 CRUD 补充：

```bash
cd desktop && cargo test runtime_config
# 8 passed; 33 filtered out

cd desktop && cargo test app_mode
# 2 passed; 38 filtered out

cd desktop && cargo check
# exit 0

cd frontend && npm test -- desktopWorkstationModel.test.ts
# 1 file / 4 tests passed

cd frontend && npm exec tsc -- --noEmit
# exit 0

cd frontend && npm run lint
# exit 0

cd frontend && npm run build
# exit 0; 保留既有 lottie eval / dynamic import / large chunk warnings

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile
# 11 passed, 1 skipped
```

覆盖增量：

- `desktop/src/services/runtime_config.rs` 在旧 `runtime-config.json` schema 上向后兼容新增 `profiles`，支持最多 20 个 secret-free 工作站环境配置档；每个配置档只保存 `id/name/mode/backendUrl`，保存/读取时统一校验 http/https 后端地址、配置档 ID、名称长度和重复 ID。
- `desktop/src/commands/app_mode.rs` 新增 `list/create/update/delete/apply_workstation_profile` Tauri IPC；直接切换模式或保存后端地址时会保留已有 profiles，不会因更新当前环境丢失配置档。
- `frontend/src/lib/tauri-bridge.ts` 与 `DesktopWorkstationPanel` 接入配置档 CRUD：桌面 runtime 可创建、编辑、应用、删除常用环境组合；非桌面预览仍只读；配置档 UI 明确不保存密钥、Token 或证书。
- Playwright 在模拟桌面 runtime 下覆盖配置档保存、编辑为云端、应用到当前状态、删除回空列表，并继续覆盖移动宽度不横向溢出。
- 这关闭的是桌面主工作站“环境 profile”本地 CRUD；真实 LLM/MCP/Skills connector 密钥联调、真实 approved connector runtime、signed runtime 和跨设备真机证据仍保持阻断。

2026-05-09 桌面本地模型管理补充：

```bash
cd desktop && cargo test runtime_config
# 10 passed; 51 filtered out

cd desktop && cargo test local_llm
# 3 passed; 76 filtered out

cd frontend && npm test -- desktopWorkstationModel.test.ts
# 1 file / 11 tests passed

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile
# 15 passed, 1 skipped

bash scripts/desktop-mvp-local-gate.sh
# Desktop MVP local gate: PASS
```

覆盖增量：

- `desktop/src/services/runtime_config.rs` 新增 secret-free `localModel` 字段，旧 `runtime-config.json` 无该字段时继续兼容；保存时只持久化模型名称，不保存 API key、token、证书或 connector secret。
- `desktop/src/commands/local_llm.rs` 新增 `get_local_llm_config` / `set_default_local_model`，并让 `local_llm_chat` 在未显式传入模型时读取桌面默认模型；模型名称只允许安全字符集，拒绝空值、空格和 shell-like 内容。
- `desktop/src/commands/local_llm.rs` 新增本地模型端点 guard：`OLLAMA_URL` 只允许 `localhost`、loopback、私网 IP 或 `.local` 主机，拒绝公网地址、凭据、路径、查询参数和非 http/https scheme，避免“本地 LLM”在绝密/本地语义下被环境变量指向外部服务。
- `frontend/src/components/desktop/DesktopWorkstationPanel.tsx` 新增“本地模型管理”面板，桌面 runtime 可查看 Ollama/兼容端点、已检测模型数量、选择或手填默认模型并保存；非桌面预览保持不可写。
- Playwright 已覆盖模拟桌面 runtime 下保存 `llama3.1:8b` 为默认模型；Quick Query 真实模型 smoke、模型下载/安装、packaged runtime 和 signed runtime 证据仍保持阻断。

2026-05-09 桌面本机通知补充：

```bash
cd desktop && cargo test native_notification
# 7 passed; 61 filtered out

cd frontend && npm test -- desktopWorkstationModel.test.ts
# 1 file / 12 tests passed

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile
# 15 passed, 1 skipped
```

覆盖增量：

- `desktop/src/commands/native_notification.rs` 新增 `preview_desktop_notification` / `send_desktop_notification`，把案件进展、风险预警、系统和同步状态通知收口到 Tauri 本机通知插件；发送前会压缩换行/空白、限制 OS 通知长度，并拒绝空标题/内容和带控制字符的关联 ID。
- `desktop/src/commands/native_notification.rs` 继续补齐 `get_desktop_notification_permission` / `request_desktop_notification_permission`，把桌面通知权限状态和授权请求纳入同一 local-only / safe-in-top-secret 响应契约，不保存或传递外部推送凭据。
- `frontend/src/lib/tauri-bridge.ts` 新增 typed notification IPC wrapper；`DesktopWorkstationPanel` 新增“本机通知”面板、`native-notification-permission-action` 权限按钮和 `native-notification-test` 测试按钮，TopSecret 模式仍标记为 local-only / safe-in-top-secret，不接入 APNs、FCM 或服务端推送。
- Playwright 已覆盖模拟桌面 runtime 下触发 `send_desktop_notification`，并继续覆盖非桌面禁用态和移动宽度不横向溢出。
- 该证据只关闭桌面本机通知的代码级链路；Tauri 桌面插件当前把 permission API 视为 granted，signed packaged runtime 的系统偏好权限弹窗/设置页截图、托盘/后台触发、真实案件事件驱动和跨设备/服务端推送证据仍待闭环。

2026-05-09 桌面离线队列管理补充：

```bash
cd desktop && cargo test offline_
# 11 passed; 66 filtered out

cd frontend && npm exec tsc -- --noEmit
# exit 0

cd frontend && npm run lint
# exit 0

cd frontend && npx playwright test e2e/settings-workstation.spec.ts --project=chromium --project=mobile
# 15 passed, 1 skipped

cd desktop && cargo clippy --all-targets -- -D warnings
# exit 0

bash scripts/desktop-mvp-local-gate.sh
# Desktop MVP local gate: PASS

node scripts/validate-product-status-consistency.cjs
# Product status consistency: OK
```

覆盖增量：

- `desktop/src/commands/offline_tasks.rs` 新增 `list_offline_tasks` / `retry_failed_offline_tasks`，最近任务摘要会把桌面文件拖入任务的完整本地路径留在加密 SQLCipher 队列内，只暴露文件名和动作摘要。
- `desktop/src/services/offline_queue.rs` 新增最近任务查询和 failed -> queued 重新入队 SQL；重新入队只更新本机队列，不触发网络同步，绝密模式下仍属于 local-only 操作。
- `desktop/src/commands/offline_tasks.rs` 继续新增 `process_local_offline_tasks`，当前只处理桌面文件拖入的 `.txt/.md` `document_summary`：读取本机 UTF-8 文本、生成 `desktop_builtin_text_summary_v1` 规则摘要并写入 `local_result`，将任务推进到 `local_completed`；该过程不调用外部模型、云端 API 或同步。
- 最近任务摘要只会对 `desktop_builtin_text_summary_v1` 且 `localOnly/safeInTopSecret=true` 的结果暴露 `local_result_preview`，不会把任意历史 `local_result` 或本地文件路径渲染到前端。
- `frontend/src/lib/tauri-bridge.ts` 新增 typed offline queue IPC wrapper；`DesktopWorkstationPanel` 新增“离线队列”面板，可查看待处理/本机完成/失败/总量、最近任务、失败重入队、本机处理动作和安全结果预览。
- 该证据关闭的是本机离线队列可观测、修复入口和文本摘要本机处理闭环；PDF/DOCX 本机解析、shared-staging 同步、跨设备连续会话、signed packaged runtime 和完整脱网业务闭环仍待补证。

2026-05-09 桌面 PrivacyContext 门控对齐补充：

```bash
cd frontend && npm test -- PrivacyContext.test.ts
# 1 file / 3 tests passed

cd frontend && npm exec tsc -- --noEmit
# exit 0

cd frontend && npm run lint
# exit 0

cd frontend && npm run build
# exit 0; 保留既有 lottie eval / dynamic import / large chunk warnings

backend/.venv/bin/pytest -q backend/tests/test_external_surface_guards.py -k "mcp_server_update_preserves_masked_env_when_omitted or mcp_server_create_writes_masked_audit_log"
# 2 passed, 32 deselected

backend/.venv/bin/ruff check backend/tests/test_external_surface_guards.py
# All checks passed
```

覆盖增量：

- `frontend/src/context/PrivacyContext.tsx` 在桌面 Tauri 环境中监听 `useAppModeStore`，把 `top-secret` 映射为旧业务门控识别的 `PrivacyMode.LOCAL`，避免 Rust 已恢复绝密模式但 `ModeGate` 仍按 HYBRID 放开云端/混合入口。
- `frontend/src/context/PrivacyContext.test.ts` 锁住 `top-secret -> LOCAL`、`hybrid -> HYBRID`、`cloud -> CLOUD` 和未知值回退 HYBRID。
- 这只关闭桌面运行模式到前端业务门控的一致性缺口；仍不代表真实出站联调、订阅购买链路或第三方 connector 凭据完成。

2026-05-09 MCP connector 凭据保留与遮罩补充：

```bash
cd frontend && npm test -- mcpSettingsModel.test.ts
# 1 file / 3 tests passed

cd frontend && npm exec tsc -- --noEmit
# exit 0

cd frontend && npm run lint
# exit 0

cd frontend && npm run build
# exit 0; 保留既有 lottie eval / dynamic import / large chunk warnings
```

覆盖增量：

- `frontend/src/pages/mcpSettingsModel.ts` 新增保存 payload 规则：创建 connector 或显式替换环境变量时才提交 `env`；编辑既有 connector 的名称、描述、命令、启用状态等元数据时默认不发送 `env`，避免把后端已保存的密钥清空。
- `frontend/src/pages/Settings.tsx` 的 MCP 编辑弹窗只展示后端返回的 `env_keys`，不显示 env 值；新增“替换环境变量”显式入口，新输入的 secret 使用 password input 且列表中只显示“已填写/待填写”。
- `frontend/src/lib/api.ts` 补齐 `McpServerConfig.env_keys` 类型，与后端 masked response 对齐。
- `backend/tests/test_external_surface_guards.py` 新增后端回归：创建带 secret env 的 MCP connector 后，只更新元数据时响应仍只返回 `env_keys`、数据库 env 保留、审计日志不含 secret。
- 这降低本地 connector 配置 CRUD 的凭据丢失/泄露风险；真实 approved MCP connector 连接演练、外部 provider 凭据、route-token runtime 证据仍保持阻断。

2026-05-09 LLM 配置组织级 CRUD 边界补充：

```bash
backend/.venv/bin/pytest -q backend/tests/test_llm_org_isolation.py
# 10 passed

backend/.venv/bin/ruff check backend/src/api/routes/llm.py backend/src/services/llm_service.py backend/tests/test_llm_org_isolation.py
# All checks passed

cd backend && ./.venv/bin/mypy src/api/routes/llm.py src/services/llm_service.py
# Success: no issues found in 2 source files
```

覆盖增量：

- `backend/src/api/routes/llm.py` 的 LLM 配置创建会把非 superuser 管理员创建的配置绑定到当前组织；响应仍只返回 `api_key_masked`，不返回明文 `api_key`。
- LLM 配置读取、更新、删除、设为默认、启停和“测试已保存配置”现在都先按组织 scope 查找；跨组织或无组织管理员会 fail-closed 为 404/403。
- `backend/src/services/llm_service.py` 的默认配置查询与 `set_default` 支持组织过滤；设置当前组织默认 LLM 不再清掉其他组织的默认配置。
- `backend/tests/test_llm_org_isolation.py` 新增回归覆盖创建绑定 org、跨组织管理拒绝、默认配置按 org 查询、创建/更新/设默认仅清同组织配置。
- 这关闭的是 LLM provider/endpoint/model/key CRUD 的组织隔离和遮罩边界；真实 provider 密钥联调、route-token runtime 证据、完整前端配置体验和真实 approved connector runtime 仍保持阻断。

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
- `/sync/remote-control/commands` 只在已配对、已授权、已二次确认的前提下写入队列；后端入队阶段会规范化 `command_type` 并只允许 `ping/status_probe/desktop.ping/desktop.status_probe` safe-probe 命令，非 safe-probe 会在写队列前 403 拒绝并写入 `unsupported_command_type` 审计；`/commands/{command_id}/cancel` 可撤销 queued 命令；审计事件会脱敏 token/secret 类字段。
- `/sync/remote-control/commands/claim` 允许桌面 host 在配对和 route token 有效时领取 queued 命令；`/commands/{command_id}/status` 支持 running/completed/failed 状态回传，结果摘要和嵌套 token/secret 字段会递归脱敏。
- `desktop/src/services/remote_control_host.rs` 和 `desktop/src/commands/remote_control.rs` 新增桌面 Tauri IPC host 客户端：确认配对、领取命令、回传 running/completed/failed 状态均使用登录态 bearer token、后端 URL、pairing-scoped route token 和 TopSecret data-network guard；本地测试锁住 URL/payload/状态值、claim 响应解析、safe probe completed、未知命令 failed/unsupported、有间隔/次数/limit 上限的 bounded safe-probe host poll 配置与汇总，以及 env-gated 后台 safe-probe daemon 配置、TopSecret daemon 阻断、未登录/无测试 bearer 时网络前阻断，以及本地 mock 后端 claim -> running -> completed 成功回路与 `result_summary` 不泄露 route/bearer token。
- `mobile/app/desktop-control.tsx`、`mobile/src/services/api.ts` 和 `mobile/src/features/desktop-control/model.ts` 新增移动端 safe-probe 入队/状态/取消/审计时间线面：只有 confirmed pairing 同时返回 `desktop_device_id` 与 `pairing_id` 时才启用；点击后先申请短期 route token，再只下发 `desktop.status_probe` / `l2` / 120 秒过期命令；local 模式仍在 fetch 前 fail-closed；UI 显示“入队等待桌面 host 回传”，可刷新命令状态、取消 queued/claimed 探针，并展示脱敏审计时间线，不声明已执行且不渲染命令 payload/metadata 原文。
- 这仍不是远控完成态：当前只证明后端 host lifecycle API、safe-probe-only 队列、桌面 IPC host 客户端、受限 safe-probe poll 配置、env-gated 后台 safe-probe daemon 基础、本地 mock 后端安全探针回路、移动端安全探针入队和审计边界，不证明 signed runtime 下的常驻 daemon、高风险真实桌面执行、跨设备连续会话、真实移动设备或 signed desktop runtime。

## 2. 证据覆盖矩阵

| 能力 | 当前证据 | 覆盖是否充分 |
|---|---|---|
| 静态质量基线采集 | `scripts/static-quality-baseline.sh` 可生成 diff/ruff/mypy/frontend/desktop/release-evidence secret+PII/full-repo secret/mock scan 摘要；当前采集 ruff `0`、mypy `0`、mypy zero-baseline gate `0`、release evidence secret/PII scan `0`、secret scan `0`、mock/fallback scan `0`；全仓 Ruff 与 backend mypy 已清零；`docs/release/evidence/static-quality-baseline.md` 已记录 zero-baseline 规则 | 当前发布静态质量证据充分；后续需保持零回退 |
| 合同状态机 | 单元/API 测试 + webhook 回写测试 | 充分 |
| 电签 provider 代码级协议 | fake `httpx.AsyncClient` 校验官方 header/body/path | 代码级充分，商业级不足 |
| 电签真实沙箱 | `scripts/sandbox-evidence-runner.py` 已提供配置预检和可选 live 采集入口，预检 artifact 会列出 env 之外的 `runtime_prerequisites` 和 `external_evidence_requirements`，避免签署文件/完成 flow、官方回调、重复幂等、失败重试缺失导致 live 步骤被误当完整；live step validator 会把无 signer URL 标为 `pending`、空签署文件下载标为 `fail`；`backend/tests/test_sandbox_evidence_runner.py` 覆盖 live 确认门、脱敏写出、env 模板同步、runtime prerequisite、外部证据槽输出、honest-gating validators 和外部交接文档 live 参数防漂移；当前本地预检缺少真实账号配置，未运行 live | 不充分 |
| 支付 provider 代码级协议 | provider/client/webhook 单测 | 代码级充分，商业级不足 |
| 支付/电签关键动作审计 | `backend/tests/test_commercial_action_audit.py` 覆盖支付下单、关单、退款与电签发起、取签署链接、取消流程均写入 `AuditLog`；签署链接 URL 不进入审计内容 | 代码级充分；真实沙箱仍需验证外部渠道事件与本地审计可对账 |
| 支付真实沙箱 | `scripts/sandbox-evidence-runner.py` 已提供配置预检和可选 live 采集入口，预检 artifact 会列出 env 之外的 `runtime_prerequisites` 和 `external_evidence_requirements`，避免退款/查单/关单订单 ID、官方回调、重复幂等、失败重试、平台 key/cert 轮换缺失导致 live 步骤被误当完整；live step validator 会把退款 `pending` 和关单/取消 `False` 标为 `pending`，不会误报 `pass`；`backend/tests/test_sandbox_evidence_runner.py` 覆盖 live 确认门、脱敏写出、env 模板同步、runtime prerequisite、外部证据槽输出、honest-gating validators 和外部交接文档 live 参数防漂移；当前本地预检缺少真实渠道配置，未运行 live | 不充分 |
| 文档对象存储 | local backend 单测、迁移测试、上传校验测试 | 本地充分，生产 MinIO/S3 不足 |
| IM 首包鉴权/离线 ACK | 后端和前端测试 | 当前切片充分 |
| 桌面同步 | 后端 sync API/service 切片 `24 passed, 6 warnings`；`desktop-runtime-code-smoke-20260509-debug-local.json` / `desktop-runtime-ui-smoke-20260509-debug-local.log` 记录 fresh unsigned debug `.app` self-test/runtime/WebView page-load 代码级通过；本轮修复 `scripts/desktop-runtime-smoke.sh` 的 macOS `mktemp` 后缀兼容性问题后，debug bundle runtime startup 和 UI page-load 均可稳定跑到真实 `.app` 进程；Rust IPC 离线任务/同步状态已改为真实读写本地队列与 `sync_log`，不再伪造空 payload 成功；`desktop-rust-ipc-sync-code-smoke-20260509.json` 记录 Rust IPC `trigger_sync` fallback 已补 SQLCipher pending/failed push、accepted/conflict/failed 写回、pull 本地表写回和 cursor 更新时间的代码级测试证据；`--sync-code-smoke` packaged-binary entrypoint 已补，`--sync-loopback-smoke` packaged-binary entrypoint 已补，`desktop-release-runtime-unsigned-smoke-20260509.json` 证明 unsigned release `.app` 二进制可验证 migration、pending/deferred/conflict/needs_human、push payload、冲突 accepted 过滤、retry needs_human、pull response 解码，并通过本地 loopback HTTP 后端观察 bearer-auth push `2` 条记录、accepted `1`、conflict `1`、pull 写回 `1` 条远端文档和 cursor `13`；`desktop-clippy-gate-20260509.json` 记录 `cargo clippy --all-targets -- -D warnings` 已通过；`SyncStatus` 冲突弹窗、工具栏同步/冲突入口和桌面托盘模式文案已完成代码级专业化收口并有回归测试；`bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-20260507.json` 通过本地 installed-profile keyring/reopen/明文迁移/普通 sqlite3 拒读，并写出 release artifact；`scripts/desktop-sqlite-security-gate.sh` 和 `scripts/desktop-network-surface-gate.sh` 当前通过；`scripts/desktop-release-package.sh --dry-run ...`、`scripts/desktop-release-preflight.sh` 和 unsigned release `.app`/DMG preflight 已生成脱敏 artifact，production APNs entitlement、`hdiutil` / DiskManagement probe、release `.app` exists、release DMG exists 均通过；unsigned `app,dmg` 已在 unsandboxed macOS 环境产出；unsigned release packaged runtime self-test/startup/WebView page-load/sync loopback smoke 已通过；unsigned release packaged-profile plaintext-to-SQLCipher/keyring reopen 和 SQLCipher performance smoke 已通过；`cross-device-continuation-code-smoke-20260509.json` 证明桌面发起、web/mobile 拉取、uni-mobile 回复、桌面增量拉取无丢失/重复；最新完整本地门禁中全量 Vitest `13 files / 51 tests passed` | 代码级底座、Rust IPC fallback、packaged-binary sync code smoke、packaged-binary sync loopback smoke、desktop strict Clippy、SQLCipher/keyring 安全门禁、桌面网络面门禁、fresh debug bundle runtime/UI、local installed-profile keyring/reopen、migration SQL、SQLite 性能基线、release unsigned app+DMG build、unsigned release packaged runtime smoke、unsigned release packaged-profile/performance smoke、release package dry-run、release preflight 和跨设备续接代码级 rehearsal 充分；signed/notarized installer、signed packaged-profile 迁移、signed packaged runtime 性能、共享预发后端真实 push/pull/conflict/retry 和跨设备连续会话真实签名/设备证据不足 |
| RAG 引用与召回质量 | 后端 RBAC/PII、offline smoke 质量基线、live Qdrant smoke、source + 导出文档/chunk/anchor 巡检、前端引用预览/高亮纯函数测试、Playwright 引用点击/预览/高亮已落地；`eval/export_builtin_legal_full50.py` 已从内建法律语料导出 `42` 个法条 chunk 与 `50` 条非 smoke golden；`eval/rag_live_qdrant_full50.py` 已跑通 built-in full50 preflight 和 live Qdrant collection `rag_eval_full50_builtin_20260507`，写出 `rag-full50-built-in-predictions-20260507.json`；`eval/rag_quality.py` 写出 `rag-full50-built-in-metrics-20260507.json`，recall@10 `1.000`、MRR `1.000`、NDCG@10 `0.997`；`backend/tests/eval/test_rag_full50_runner.py` `8 passed`，`backend/tests/eval/test_rag_quality_smoke.py` `4 passed` | 内建 RAG full50 release evidence complete；外部客户知识库评测可作为上线后扩展 |
| 知识图谱大图性能 | 渲染层 >200 节点自动降采样；1k 节点/2k+ 边 Vitest；桌面+移动 Playwright FPS/canvas/screenshot smoke | 代码级充分；真实业务图谱数据预发复跑不足 |
| 知识管理接口 | `knowledge_management` 读写权限分层、无组织用户 fail-closed、出口脱敏和组织分桶隔离测试 `5 passed` | 代码级安全收口；进程内存存储仍非商业持久化形态 |
| 尽调缓存组织隔离 | `SearchCache.org_id` scope + 编排器/deep research 传递 org；`test_investigation_cache_org_scope.py` `3 passed` | 代码级充分；真实预发数据路径仍需复跑 |
| 风险评分解释性 | `risk_scoring_engine` 顶层 `score/factors/explain` + 确定性/兼容性测试 `2 passed`，`RiskAlertPanel` 支持因子贡献条 | 代码级充分；前端真实合同因子数据仍需联调 |
| 爬虫合规入口 | `crawler_service.fetch()` 统一白名单/robots/UA/host 频控；`crawl4ai_service` 与尽调抓取不再绕过，尽调执行信息/信用中国/裁判文书查询已移除直接 Playwright fallback，只走合规 crawl service 或返回无外部证据；商业环境下浏览器/爬虫 fetch 已在 robots/http 前要求 DB-backed `browser:fetch` route token，撤销 route 后下一次 fetch fail-closed；`test_crawler_compliance.py` `7 passed`，`test_due_diligence_intent.py` + `test_chat_due_diligence_routing.py` 当前 `21 passed` | 代码级充分；真实外网 dry-run 被本机 DNS 私网解析防护阻断，发布前需在预发网络复跑 |
| 调查意图路由 | 200 条 JSONL 离线评测集；`test_due_diligence_intent.py` + `test_chat_due_diligence_routing.py` 组合 `13 passed`；意图准确率 `1.000`、企业名抽取准确率 `1.000`（150 条含企业名）；ChatService 已分流尽调/舆情/法规监测 | 代码级充分；真实用户 query 分布上线后需持续采样复核 |
| 案件/任务 | 案件状态机/终态只读/时间线 event_at 语义、任务 owner/assignee/admin 过滤；`test_case_service.py` + `test_lawyer_matching_and_tasks_api.py` 组合 `46 passed` | 代码级核心充分；全矩阵和 Playwright 全流程仍需发布前扩展 |
| 专业服务市场 P0（律师/律所） | local 模式固定拒绝、投标前利益冲突命中 409、同分律师曝光轮询；`test_lawyer_matching_and_tasks_api.py` `17 passed` | 律师/律所代码级核心充分；律所 RBAC 全矩阵、8 API 打勾、1000 次公平报告仍需补；税务师/税务事务所/财务顾问/会计审计仍为后续扩展验收 |
| 全设备智能助手底座 | 后端 LLM/private LLM/MCP/Skills/knowledge 代码基础、桌面 local LLM/SQLCipher/keyring/本地队列、移动隐私模式语义已存在；LLM provider 配置 API 已补组织级 CRUD 边界、同组织默认配置隔离、跨组织管理 fail-closed 和 API key 遮罩响应；前端组织级模型配置入口已收束到治理后台“模型治理”，遮罩展示已保存密钥，编辑元数据时不回传 `api_key`，新增或显式替换时才发送密钥，`我的设置`不再承载组织级 LLM/MCP 凭据 CRUD，MCP/工具连接迁入治理后台“系统集成”，`backend/tests/test_llm_org_isolation.py` `10 passed`；agent capability policy 现在覆盖未知工具 fail-closed、agent tool allowlist、订阅 feature、角色 permission、绝密模式、设备信任、通道策略、高风险审批上下文，以及 MCP tool list/filter + runtime 二次判权；Harness `policy/agent/{agent}/tools` 已按相同上下文过滤可用工具，避免能力中心展示当前用户/订阅/隐私模式不可执行的工具，`backend/tests/test_agent_governance_policy.py` `4 passed`；服务层 `CapabilityPolicyEngine` 已把订阅、角色、权限、风险级别、隐私模式、数据范围、设备信任、通道策略、CapabilityRoute 状态和 AgentApproval 审批状态合并为单次可审计决策，并新增五类业务权限回归，`backend/tests/test_capability_policy_engine.py` `11 passed`；`capability_route_service` 已补短期 route-token broker，锁住 hash-only storage、scope 校验、撤销后下一次验证失败、过期/未知/missing token fail-closed 和审计事件，`backend/tests/test_capability_routes.py` `4 passed`；Agent 控制面持久化模型与迁移已补，`backend/tests/test_agent_governance_models.py` `8 passed` 锁住模型注册、CapabilityRoute 不保存真实密钥/原始 token、TokenLease 只保存 hash、组织级 route 唯一约束、复合租户外键、跨组织写入失败、审批/审计上下文、审计不可变监听和迁移无敏感列；DB-backed `AgentGovernanceService` 已补 route-token lease 跨实例验证、跨服务实例撤销后长生命周期 worker session 刷新、组织隔离、consumer/scope 拒绝、consumer mismatch、过期 fail-closed、route 撤销后下一次调用失败，以及组织级 CapabilityRoute 策略更新、policy 递归脱敏、禁用撤销 lease 后下一次 token validate fail-closed，`backend/tests/test_agent_governance_service.py` `8 passed`；DB-backed `AgentApprovalService` 已补高风险审批创建、payload 脱敏、授权角色审批/驳回、pending/approved 校验、action/route mismatch 拒绝、过期/撤销 fail-closed、observe 只读旁听快照、workspace-control 默认在运行时未接入前对暂停/接管/终止 fail-closed、显式 `workspace_runtime.mode=local_rehearsal` 本地 pause/takeover/terminate rehearsal、已批准工作室 artifact list/create/revise/export、artifact 递归脱敏和 append-only revision audit、审批状态不被误改和审计事件，`backend/tests/test_agent_approval_service.py` `10 passed`；`/agent-approvals` API 已补创建、列表/详情、pending count、audit-events、audit-export、workspace-control、approve/reject/revoke、validate 和组织 CapabilityRoute list/update 策略 API，`backend/tests/test_agent_approval_api.py` `9 passed` 锁住未登录拒绝、组织/本人 scope、普通员工自批拒绝、管理员批准/撤销、执行前放行/拒绝、审批审计时间线、审批审计 JSON 导出、已授权 observe 只读旁听快照、默认运行时未接入时暂停/接管/终止 fail-closed、本地 takeover rehearsal、已批准工作室 artifact list/create/revise/export、payload/artifact 脱敏、普通员工不能改组织 route、管理员禁用 route 后撤销 token；前端最小 `Agent 审批工作台` 已补列表/count、状态筛选、风险动作/payload 预览、批准/驳回/撤销、审批审计时间线、审批审计 JSON 导出、已批准行工作室成果查看/新增/复核/导出、已批准行 observe 旁听快照、暂停/接管/终止控制拒绝提示、桌面侧边栏入口和移动协作导航高亮，且能力中心最小面板已按组织角色过滤工具：老板/Owner/超级管理员/admin 类角色看全量，普通员工只见基础能力和可申请项，高风险/full-only 工具隐藏；组织能力策略面板已接入 CapabilityRoute list/update，可由全量角色启用/禁用 route；Skill 连接器凭据面板已接入 `/skill-governance/connectors`，管理员可在同一治理工作台创建、编辑、清空、替换或删除连接器配置，界面只展示 `credential_keys`，编辑元数据默认不回传已保存密钥；`frontend/e2e/agent-approval-workspace.spec.ts` `6 passed, 6 skipped` 锁住桌面批准动作、审计导出、能力策略可用/可申请/隐藏边界、员工能力中心角色可见性、组织 route 禁用动作、Skill connector 凭据保留/新增/替换/删除且不渲染明文密钥、已批准工作室成果记录/复核/导出、observe 旁听快照、运行时未接入控制 fail-closed 和移动端视口不横向溢出；`backend/tests/test_mcp_route_governance.py` `5 passed` 锁住 MCP 开发态兼容、商业环境缺 route token fail-closed、DB route token 放行、route revoke 后拒绝和 consumer mismatch 拒绝；`backend/tests/test_cli_route.py` `10 passed` 锁住 CLI API Key 基线、商业环境缺 route token fail-closed、DB route-token 放行、consumer mismatch 拒绝和 `/cli/route-token` 签发；`backend/tests/test_llm_route_governance.py` `11 passed` 锁住 REST/SSE/WebSocket Chat Agent LLM runtime 商业环境缺 token fail-closed、DB `llm:chat` route token 放行、route revoke 后模型 HTTP 前拒绝、流式模型调用触网前拒绝、WebSocket route-token 透传/contextvar 流式传递、`/chat/route-token` 用户绑定签发，以及 RAG direct LLM 缺 token 触网前拒绝/DB token 放行；审批流授权已补批量审批、列表 scope、模板写入/读取/使用、过期审批和 admin org-scope 回归，`backend/tests/test_business_authorization_guards.py -k 'approval or template'` 当前 `7 passed`；`skill_evolution_service` 已补本地 proposal/eval/approval/gray/rollback/audit gate，`SkillService` 可按 governed enabled version 过滤，DB-backed `SkillGovernanceService` 和 `/skill-governance` API 已补 proposal/eval/approval/gray/rollback/enabled-version/audit 持久化、组织隔离、API scope、audit export、migration upgrade/downgrade、append-only audit 和 no raw secret/token storage 回归，五个 skill governance gate tests 合计 `25 passed`；MCP 外部连接已补 stdio/SSE/env/command-line allowlist、子进程最小环境和 tool execution route-token gate；CLI `/execute` 已补 DB-backed route-token gate，桌面端会在 execute 前获取并传递 route token；REST/SSE/WebSocket Chat Agent LLM runtime 与 RAG direct LLM 已补 DB-backed `llm:chat` route-token gate，Agent 同步/流式模型调用以及 RAG generation/query expansion/entity extraction/stream generation 会在真实 HTTP/本地模型调用前校验 route token；桌面 CLI/sync/Harness IPC、本地同步桥、统一 API fetch、WebView 全局 fetch 与 WebSocket 已补 top-secret data-network guard；Tauri/前端 HTTP 插件面和宽松 CSP 已由桌面网络面门禁移除；`/settings?tab=workstation` 已补最小可见入口、TopSecret-safe action model、本地 LLM/模型数量/离线队列、知识库数量/文档数、MCP 服务/启用/工具缓存只读探针、移动远控安全闸和 secret-free 环境配置档 CRUD；后端 `/sync/remote-control/*` 已补 DB-backed 远控控制面和 host lifecycle API，覆盖持久化配对请求、桌面确认、CapabilityRoute route-token 签发、命令队列、host 领取、running/completed/failed 状态回传、取消、递归脱敏审计以及本地/绝密/缺 token/高风险未二次确认 fail-closed；桌面 Tauri IPC host 客户端已补确认配对、领取命令、回传状态、单次 safe-probe host cycle、有间隔/次数/limit 上限的 bounded safe-probe poll 和 env-gated 后台 safe-probe daemon 基础，并由 TopSecret guard、登录态 bearer token、route token、payload/状态/轮询配置和 daemon 网络前阻断单测锁住；移动端新增 `/desktop-control` 状态、safe-probe 入队、状态刷新、queued/claimed 取消和脱敏审计时间线面，local 模式不发网络请求，hybrid/cloud 读取后端安全闸，confirmed pairing 下先签发 route token 再只入队 `desktop.status_probe`，并显示等待桌面 host 回传；Playwright 已覆盖 workstation/legacy privacy route、URL 写回、非桌面禁用态、模拟桌面运行时探针、环境配置档保存/编辑/应用/删除和移动宽度不越界 | 底座存在但商业证据不足；真实 provider 密钥联调、signed runtime daemon 运行证据与高风险真实执行器、真实移动远控跨设备联调、完整策略编辑器、订阅购买联动、部门申请流、CapabilityRoute/TokenLease/AgentApproval/AgentAuditEvent/SkillGovernance 完整 browser automation 和 desktop-control 运行时集成、真实 approved MCP connector runtime 证据、完整 Human-in-the-loop runtime、真实暂停/接管/终止执行效果、跨端恢复和桌面 top-secret signed packaged runtime 出站证据仍需测试 |
| 可信会话与 Skills 进化 | OpenSpec、参考分析、TASK-03 和 TASK-12 已把 Codex/Claude 式工作台体验、Skill lifecycle、SkillEvolutionProposal、eval gate、审批和回滚纳入验收；本地服务和测试已覆盖 agent draft proposal、required eval、越权审批拒绝、授权审批、灰度、回滚、审计和 governed Skill 版本过滤；DB-backed `SkillGovernanceService` 与 `/skill-governance` API 已覆盖 proposal、required eval、授权审批、灰度启用、回滚、enabled version 持久化、组织隔离、API scope、audit export、append-only audit、migration upgrade/downgrade 和 no raw secret/token storage；AgentApproval/AgentAuditEvent 模型、DB-backed AgentApprovalService 和 `/agent-approvals` API 已补，锁住高风险审批创建、组织/本人 scope、payload 脱敏、授权角色审批/驳回、撤销、执行前 validate、过期/撤销 fail-closed、action/route 匹配、审计写入、审批审计时间线、审批审计 JSON 导出、observe 只读旁听快照、默认 workspace-control 运行时未接入 fail-closed，以及显式 `workspace_runtime.mode=local_rehearsal` 的本地 pause/takeover/terminate rehearsal；已批准工作室成果 list/create/revise/export 采用 append-only revision audit 并递归脱敏；长任务 runtime summary artifact event 已补，`backend/tests/test_workforce.py -k runtime_workspace_artifact` `1 passed` 锁住脱敏和 ready-for-review 时间线，`frontend/src/lib/workspaceArtifacts.test.ts` `2 passed` 锁住事件归一化，`frontend/e2e/right-panel.spec.ts --project=chromium -g workspace_artifact_created` `1 passed` 锁住桌面工作台展示；`MemoryLayer.set_governed_session_artifact` 已补 local/top-secret 拒绝、org/user/consent gate、artifact payload 递归脱敏和治理元数据，`backend/tests/test_memory_governance.py` `3 passed`；前端最小审批工作台已覆盖桌面批准动作、审批审计时间线、审批审计 JSON 导出、已批准行工作室成果查看/新增/复核/导出、已批准行控制动作拒绝提示和移动端不横向溢出 | 仍缺签名/商业 runtime 长任务 replay、跨设备恢复、完整记忆治理 UI/运行时接入、完整 Human-in-the-loop runtime、真实暂停/接管/终止执行效果、真实执行链路 route/token 失权和商业发布证据 |

2026-05-08 补充：REST/SSE/WebSocket Chat Agent LLM runtime 与 RAG direct LLM 已在商业环境加入 DB-backed `llm:chat` route-token gate，`/chat/route-token` 可按当前用户 consumer 签发短期 token，WebSocket 可从 auth 首包、连接 header 或单条消息 payload 透传 route-token，REST Knowledge RAG、同步 Chat RAG 和 WebSocket RAG 会传递 route context，Agent 同步/流式模型调用以及 RAG generation/query expansion/entity extraction/stream generation 在真实 HTTP/本地模型调用前校验；`backend/tests/test_llm_route_governance.py` 当前 `11 passed`，覆盖缺 token、DB token 放行、route revoke、流式触网前拒绝、WebSocket route-token 透传、用户绑定签发，以及 RAG direct LLM 缺 token 拒绝/DB token 放行/撤销后拒绝。完整 browser automation 和 desktop-control runtime 仍待闭环。

2026-05-09 补充：前端 LLM 凭据体验已补 code + browser evidence。`frontend/src/pages/llmSettingsModel.ts` 统一构造保存 payload，编辑已有 provider 的名称、模型和 URL 时不会把遮罩值或空密码框回传成 `api_key`，只有新增配置或显式替换密钥才发送 `api_key`；`frontend/src/pages/Settings.tsx` 的 LLM 面板只展示 `api_key_masked` 摘要，编辑弹窗保留“已保存”提示但密码输入为空；`frontend/src/pages/admin/AdminAIConfig.tsx` 移除旧的 transient system config 表单，复用同一个组织级 `/llm/configs` 面板；`frontend/e2e/helpers/session.ts` 已补 LLM mock route。验证：`cd frontend && npm test -- llmSettingsModel.test.ts` -> `3 passed`，`npm exec tsc -- --noEmit` -> passed，`npm run lint` -> passed，`npx playwright test e2e/settings-llm.spec.ts --project=chromium --project=mobile` -> `8 passed`，`npm run build` -> passed with existing lottie eval / dynamic import / chunk warnings。该证据只关闭前端 LLM 凭据 UX 代码级缺口；真实 provider 密钥 live test 和真实 approved connector runtime 仍待闭环。

2026-05-09 补充：Skills connector credential backend CRUD 已补 code evidence。`backend/alembic/versions/044_add_skill_connector_configs.py` 新增 `skill_connector_configs` 组织级表，保存 connector 元数据与 `encrypted_fields`，迁移和模型回归均禁止 raw secret/token/api_key 列；`SkillGovernanceService` 新增 list/create/update/delete connector config，创建与显式替换会加密凭据，元数据更新默认保留已保存密钥，审计 snapshot 只记录 `credential_keys`；`/skill-governance/connectors` 只允许管理员访问，响应不返回 credentials 或 `encrypted_fields`。验证：`backend/.venv/bin/pytest -q backend/tests/test_skill_governance_models.py backend/tests/test_skill_governance_service.py backend/tests/test_skill_governance_api.py backend/tests/test_skill_evolution_service.py backend/tests/test_skill_service.py` -> `31 passed`；`backend/.venv/bin/ruff check backend/src/models/agent_governance.py backend/src/models/__init__.py backend/src/services/skill_governance_service.py backend/src/api/routes/skill_governance.py backend/tests/test_skill_governance_models.py backend/tests/test_skill_governance_service.py backend/tests/test_skill_governance_api.py backend/alembic/versions/044_add_skill_connector_configs.py` -> `All checks passed`；`cd backend && ./.venv/bin/mypy src/models/agent_governance.py src/services/skill_governance_service.py src/api/routes/skill_governance.py` -> `Success`。该证据只关闭 Skills connector 凭据后台 CRUD 代码级缺口；真实 provider 密钥 live test 和真实 approved connector runtime 仍待闭环。

2026-05-09 补充：Skills connector 前端凭据体验已补 code + browser evidence。`frontend/src/pages/skillConnectorSettingsModel.ts` 统一构造连接器 payload，编辑已有连接器默认 `preserve` 且省略 `credentials`，显式 `replace` 才提交解析后的 `KEY=value` 凭据，显式 `clear` 提交空 credentials；`frontend/src/pages/AgentApprovalWorkspace.tsx` 在 Agent 治理工作台加入管理员级 Skill 连接器面板，支持按 Skill 查看、创建、编辑、替换/清空凭据、启停和删除，界面只展示 `credential_keys` 且不会渲染明文 secret；`frontend/e2e/helpers/session.ts` 已补 `/skill-governance/connectors` mock route。验证：`cd frontend && npm test -- skillConnectorSettingsModel.test.ts` -> `4 passed`，`npm exec tsc -- --noEmit` -> passed，`npm run lint` -> passed，`npx playwright test e2e/agent-approval-workspace.spec.ts --project=chromium --project=mobile` -> `6 passed, 6 skipped`。该证据关闭 admin-facing Skills connector 前端凭据 UX 代码级缺口；真实 provider 密钥 live test、真实 approved connector runtime、signed runtime、商业多进程撤销运行时证据和跨设备真机证据仍待闭环。

2026-05-09 补充：approved MCP connector 本地演练已补 code evidence。`backend/src/services/agent_governance_service.py` 的 route-token validate 增加 `required_route_key`，`backend/src/services/mcp_client_service.py` 在 MCP tool call 前把 token 绑定到当前 MCP server，避免一个 connector 的 `mcp:call` token 横向调用另一个 server；`backend/tests/test_agent_connector_runtime_rehearsal.py` 使用 local mock MCP session 验证 route-token issue、connector-bound tool call、route revoke、撤销 token 下一次调用 fail-closed、审计事件和 raw token 不入审计；`scripts/agent-connector-rehearsal.sh` 可写出 `agent-connector-local-rehearsal-20260509.json`。验证：`cd backend && ./.venv/bin/pytest -q tests/test_mcp_route_governance.py tests/test_agent_connector_runtime_rehearsal.py` -> passed；`bash scripts/agent-connector-rehearsal.sh --out docs/release/evidence/artifacts/agent-connector-local-rehearsal-20260509.json` -> passed。该证据只关闭本地 mock runtime rehearsal；真实 provider credentials、provider dashboard/log、signed packaged runtime outbound 和商业多进程撤销运行时证据仍待闭环。

2026-05-09 补充：Agent route-token 跨进程撤销本地演练已补 code evidence。`backend/src/services/agent_governance_service.py` 在 route-token validate 查询中使用 `populate_existing` 刷新 DB-backed lease/route，避免长生命周期 worker session 在管理员进程撤销后继续读取 identity-map 旧状态；`backend/tests/test_agent_governance_service.py` 新增文件型 SQLite rehearsal，分别用 issuer/worker/admin 独立 session 签发、首次放行、管理员撤销、同一 worker session 下一次调用 fail-closed，并校验 lease hash-only 与审计不含 raw token；`scripts/agent-cross-process-revocation-rehearsal.sh` 可写出 `agent-cross-process-revocation-rehearsal-20260509.json`。验证：`bash scripts/agent-cross-process-revocation-rehearsal.sh --out docs/release/evidence/artifacts/agent-cross-process-revocation-rehearsal-20260509.json` -> `1 passed, 7 deselected`。该证据关闭本地跨服务实例撤销刷新缺口；signed packaged runtime、真实 provider 执行链、生产观测日志和商业多进程运行时证据仍待闭环。

2026-05-09 补充：外部资源交接已补机器清单和本地 gate。`docs/release/external-resource-requirements.json` 结构化列出支付、电签、桌面签名/公证、uni-app/DCloud/iOS/Android/微信小程序真机、LLM/Embedding/search/storage/notification/CAPTCHA/MCP/RTC 等外部输入，只保存 env/runner/artifact/account/device 引用，不保存真实值；`scripts/validate-external-resource-requirements.cjs` 校验资源唯一性、P0 env 覆盖、`.env.example`/`backend/.env.example` 模板同步、handoff 文档存在和禁止 `value/api_key/private_key/token/session_key` 等真实值字段。验证：`node scripts/validate-external-resource-requirements.cjs` -> OK；`node scripts/validate-commercial-delivery-checklist.cjs` -> OK；`node scripts/validate-commercial-delivery-lanes.cjs` -> OK；`cd backend && ./.venv/bin/pytest -q tests/test_external_resource_requirements.py tests/test_commercial_delivery_checklist.py tests/test_commercial_delivery_lanes.py tests/test_commercial_readiness_gate.py` -> `39 passed`；`bash scripts/commercial-readiness-gate.sh --quick` 已纳入该检查并仍因真实外部证据 pending 而失败。

2026-05-09 补充：产品路线图/项目状态一致性已纳入商业 quick gate。`scripts/validate-product-status-consistency.cjs` 会要求 `PRODUCT_ROADMAP.md`、`PROJECT_STATUS.md` 和平台审计文档保留桌面优先、uni-app、代码级/unsigned 支撑证据与商业证据分层，同时拒绝“Mobile Edition, Tauri iOS/Android”“桌面同步已完成”“2026-04-15 已完成能力”等过期叙述。验证：`node scripts/validate-product-status-consistency.cjs` -> OK；`cd backend && ./.venv/bin/pytest -q tests/test_commercial_readiness_gate.py` -> `28 passed`；`bash scripts/commercial-readiness-gate.sh --quick` 已打印 `Product status consistency: OK`，并仍只因真实外部/签名/真机/runtime evidence pending 而失败。

2026-05-09 补充：桌面快问 P0-2 已补 code + browser evidence。`desktop/src/commands/quick_query.rs` 定义 `quick-query` 独立窗口合约，`desktop/src/lib.rs` 的 Cmd/Ctrl+Shift+Space 改为切换 420x540、无标题栏、always-on-top 的 `/desktop/quick-query` 窗口；`frontend/src/pages/QuickQuery.tsx` 支持 top-secret/hybrid 桌面模式调用本地 `local_llm_chat`，cloud/web fallback 复用 chat stream/send API，并通过 `hide_quick_query_window` 支持关闭、ESC、失焦和完成后自动隐藏。验证：`cd desktop && cargo test quick_query` -> `2 passed`，`cd frontend && npm test -- quickQueryModel.test.ts` -> `4 passed`，`cd frontend && npx playwright test e2e/quick-query.spec.ts --project=chromium` -> `1 passed`。该证据只关闭桌面快问代码级主链路；packaged runtime 快捷键实测、200ms 呼出性能、真实本地模型手测和 signed runtime 证据仍待闭环。

2026-05-09 补充：桌面文件拖入分析 P0-3 已补 code evidence。`desktop/src/commands/file_drop.rs` 新增 `queue_file_drop_paths`，将 `.pdf/.doc/.docx` 分类为 `contract_review`，将 `.txt/.md` 分类为 `document_summary`，并写入 Rust SQLCipher/keyring 管理的 `offline_tasks` 队列；完整本地路径仅进入加密队列 payload，`desktop://file-queued` 事件和返回值只暴露文件名、task id、task type 和动作标签。`frontend/src/lib/tauri-bridge.ts` 新增 `queueFileDropPaths` typed bridge。验证：`cd desktop && cargo test file_drop` -> `4 passed`。该证据只关闭文件类型路由与本地入队底座；真实托盘 drop 手势、前端 toast、500ms 提示性能、packaged runtime 和 signed runtime 证据仍待闭环。

2026-05-09 补充：桌面文件拖入 toast 可见反馈已补 code evidence。`frontend/src/lib/tauri-bridge.ts` 新增 `listenFileDropQueued` typed listener，复用既有 `listenEvent` Tauri 事件封装监听 `desktop://file-queued`；`frontend/src/App.tsx` 在 Tauri 桌面环境注册全局监听并用 Sonner 展示入队/部分入队/不支持文件提示；`frontend/src/lib/desktopFileDropEvents.ts` 抽出 toast 摘要模型，确保 UI 反馈只显示文件名、动作和数量，不暴露完整本地路径。验证：`cd frontend && npm test -- desktopFileDropEvents.test.ts` -> `4 passed`，`npm exec tsc -- --noEmit` -> passed，`npm run lint` -> passed。该证据关闭前端 toast 代码级缺口；真实托盘 drop 手势、500ms 提示性能、packaged runtime 和 signed runtime 证据仍待闭环。

2026-05-09 补充：桌面主窗口 WebView 文件 drop 已接入 code evidence。`frontend/src/lib/tauri-bridge.ts` 新增 `listenDesktopFileDrops`，通过 Tauri v2 `getCurrentWebview().onDragDropEvent` 监听主窗口文件 drop 并调用 `queueFileDropPaths`；成功入队继续复用 `desktop://file-queued` toast，入队失败展示错误 toast；`frontend/src/lib/desktopFileDropEvents.ts` 新增 `extractDesktopFileDropPaths`，只处理 `type="drop"` payload 并过滤非字符串/空路径。验证：`cd frontend && npm test -- desktopFileDropEvents.test.ts` -> `5 passed`，`npm exec tsc -- --noEmit` -> passed，`npm run lint` -> passed。该证据关闭“拖到桌面主窗口即可入队”的代码级链路；真实托盘图标 drop、500ms packaged runtime 提示性能、signed runtime 和跨平台手测证据仍待闭环。

2026-05-09 补充：桌面标题栏基础已补 code evidence。`desktop/src/lib.rs` 在 Windows/Linux 启动时对主窗口调用 `set_decorations(false)`，macOS 继续使用 Tauri Overlay + 原生交通灯；`frontend/src/components/desktop/TitleBar.tsx` 新增非 macOS 最小化、最大化/还原和关闭按钮，并由 `frontend/src/components/Layout.tsx` 嵌入现有顶部拖拽栏；`frontend/src/lib/tauri-bridge.ts` 新增窗口控制 wrapper，`desktop/capabilities/default.json` 和 `desktop/gen/schemas/capabilities.json` 增补 `core:window:allow-toggle-maximize`。验证：`cd desktop && cargo fmt`、`cd desktop && cargo check`、`cd frontend && npm exec tsc -- --noEmit`、`cd frontend && npm run lint` -> passed。该证据关闭 P0-4 代码级基础；macOS/Windows 实机截图、双击最大化、vibrancy/acrylic、packaged runtime 和 signed runtime 证据仍待闭环。

2026-05-09 补充：桌面标题栏双击最大化已补 code evidence。`frontend/src/components/desktop/titleBarModel.ts` 新增非 macOS Tauri 自绘标题栏渲染判断和双击最大化判定，避免 button/link/input/select/textarea 或其交互祖先误触；`frontend/src/components/Layout.tsx` 在顶部拖拽栏 `onDoubleClick` 调用 `handleDesktopTitleBarDoubleClick`，最终走 `toggleMaximizeCurrentWindow`。验证：`cd frontend && npm test -- titleBarModel.test.ts` -> `2 passed`，`npm exec tsc -- --noEmit` -> passed，`npm run lint` -> passed。该证据关闭双击交互代码级缺口；Windows 实机点击、packaged runtime、vibrancy/acrylic 和 signed runtime 证据仍待闭环。

2026-05-10 补充：工作站/治理后台信息架构去冗余已补前端切片。`我的设置`收束为个人中心、本机运行和通知偏好，不再承载组织级 LLM/MCP 凭据 CRUD；旧 `/settings?tab=llm` 与 `/settings?tab=mcp` 回落个人中心，避免形成第二套后台；模型连接保留在治理后台“模型治理”，MCP/工具连接迁入治理后台“系统集成”，本机运行 Skills/MCP 卡片改为跳转 Agent 治理工作台。验证：`cd frontend && npm test -- settingsTabs.test.ts desktopWorkstationModel.test.ts llmSettingsModel.test.ts mcpSettingsModel.test.ts` -> `4 files / 22 tests passed`；`cd frontend && npm exec tsc -- --noEmit` -> passed；`cd frontend && npm run lint` -> passed；`cd frontend && npx playwright test e2e/settings-workstation.spec.ts e2e/settings-llm.spec.ts --project=chromium` -> `12 passed, 1 skipped`；`node scripts/validate-product-status-consistency.cjs` -> OK。该证据只关闭入口定位和交互冗余，不替代真实 provider 密钥、approved connector runtime、signed runtime 和真机证据。

2026-05-10 补充：后端启动 schema 漂移 fail-fast 已补代码级证据。`backend/src/api/main.py` 在 `init_db()` 失败时改为记录 error 并阻止 FastAPI lifespan 继续启动，避免旧库缺 `users.department`、`users.user_type` 等列时服务带病启动后在登录查询阶段报 `UndefinedColumnError`；`backend/tests/test_database_schema_compatibility.py` 新增用户登录相关增量列回归，并锁住 lifespan 在数据库初始化失败时 fail-fast。验证：`cd backend && ./.venv/bin/pytest -q tests/test_database_schema_compatibility.py` -> `4 passed`；`cd backend && ./.venv/bin/ruff check src/api/main.py tests/test_database_schema_compatibility.py` -> passed；`cd backend && ./.venv/bin/pytest -q tests/test_auth_roles_permissions.py tests/test_auth_surface_hardening.py` -> `25 passed`；`cd backend && ./.venv/bin/pytest -q tests/test_commercial_readiness_gate.py -k "product_status_consistency or does_not_depend_on_removed_code_index_tool"` -> `2 passed, 26 deselected`。该证据关闭启动阶段静默跳过 DB 初始化的本地可靠性缺口；真实生产数据库迁移执行日志仍需随预发/生产部署证据补齐。

2026-05-09 补充：桌面窗口 chrome 本地门禁已补 code evidence。`docs/desktop/window-styling.md` 记录 macOS Overlay、Windows/Linux 自绘标题栏、顶部拖拽栏、窗口控制、capability 和待补实机证据；`scripts/desktop-window-chrome-gate.sh` 校验 Tauri 主窗口 overlay/traffic light 配置、非 macOS `set_decorations(false)`、前端窗口控制/双击模型、titleBarModel 单测和文档存在。验证：`bash scripts/desktop-window-chrome-gate.sh` -> `PASS`。该证据提升 P0-1/P0-4 的本地治理门禁；macOS/Windows 实机截图、vibrancy/acrylic、packaged runtime 和 signed runtime 证据仍待闭环。

2026-05-08 补充：`crawler_service.fetch()` 已在商业环境对浏览器/爬虫 fetch 加入 DB-backed `browser:fetch` route-token gate，授权发生在 robots/http 网络访问前；`backend/tests/test_crawler_compliance.py` 当前 `7 passed`，覆盖缺 token fail-closed、DB route-token 放行、route revoke 后下一次触网前拒绝。该证据只关闭 browser/crawler fetch 入口，不替代完整 browser automation、desktop-control 和真实 connector runtime 证据。

2026-05-08 补充：`AgentApprovalWorkspace` 已扩展为最小 `Agent 治理工作台`，新增 `frontend/src/lib/api.ts` 的 Harness capability policy、CapabilityRoute 策略和 Skill governance 客户端、按角色过滤的能力策略可用/可申请/隐藏工具面板、组织 route 启用/禁用面板、Skill 提案创建/评测/批准/灰度/审计时间线/审计导出 UI，以及 `frontend/e2e/agent-approval-workspace.spec.ts` 桌面与移动回归；最新局部 Playwright 为 `5 passed, 5 skipped`，新增普通员工只见基础能力和可申请项、高风险/full-only 能力隐藏、管理员可禁用组织 route 的角色边界用例，但它仍是代码级证据，不替代真实 runtime/connector/撤销失权商业证据。
| 移动/小程序 | `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-20260508.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-20260508.json` 当前通过：mobile Vitest `8 files / 37 tests passed`、mobile tsc、mobile result surface guard、mobile lawyer conversion guard、Expo config/SDK/Metro config guard、`npx expo-doctor` `17/17 checks passed`、mobile production `npm audit --omit=dev` `0`、mini-program tsc、mini-program privacy boundary guard、mini-program navigation boundary guard、Taro weapp build、WeChat DevTools CLI project smoke、refresh auth guard、mobile/mini privacy network guard、fake fallback guard、mini-program design token guard，并写出包含 `mobile_expo_doctor=passed`、`mobile_expo_metro_config=passed` 和 `mobile_lawyer_conversion_guard=passed` 的代码级 artifact 与手工设备证据模板；safe-probe status/cancel/audit timeline hardening 后独立 mobile Vitest 为 `8 files / 37 tests passed`；`mobile_npm_audit` artifact 字段记录 `status=passed/critical=0/high=0/total=0`，并由 validator 锁住；`mobile-ios-simulator-expo-go-smoke-20260508.json` 证明 iPhone 17 Simulator + Expo Go 可完成本地 iOS bundle，但该 artifact 明确 `release_evidence_complete=false`；`uni-mobile-base-smoke-20260509.json` 证明 `apps/uni-mobile` typecheck、`5 files / 12 tests`、production audit `0`、H5 build 和 WeChat Mini Program build 通过；`cross-device-continuation-code-smoke-20260509.json` 证明后端/桌面 adapter/uni-app sync client 的跨设备续接代码级 rehearsal 通过；host probe 已写入 `mobile-device-host-probe-20260508.json`，确认本机 iOS Simulator 当前可用且列出 iOS 26.4 设备、ADB 无连接 Android device、Android emulator CLI 不在 PATH、WeChat DevTools 与 WeChat app 存在；移动端弱网 refresh-token 不误清会话已有单测；移动请求层已透传 `X-Privacy-Mode`，且 local 模式在 fetch 前 fail-closed；移动端桌面控制页 local 模式零网络、hybrid/cloud 经 `/sync/remote-control/status` 读取后端安全闸，confirmed pairing 下可入队、刷新和取消 safe-probe，并展示脱敏审计时间线；移动端尽调和知识库搜索提交后渲染页面内结果摘要卡，不再依赖 Alert-only 反馈；移动端找律师已从纯列表升级为匿名咨询转化链路，支持创建真实 `/lawyer/consultations`、展示 AI 匿名摘要、选择律师、创建 `/anonymous-chat/rooms` 并尝试 `/delegate`，且不再跳转不存在的律师详情路由；小程序请求层已透传 `X-Privacy-Mode`，且 local/top-secret 模式在 `Taro.request` 前 fail-closed，登录入口在 `Taro.login` 前阻断；首页/个人中心主入口已移除空路径和“功能开发中”死胡同，统一跳转 AI 助手并预填业务问题；小程序 refresh-token 已区分认证失效和临时刷新失败；消息详情和任务详情已移除 synthetic fallback 数据；`getDetailLoadErrorMessage` 已补字符串 transport error 和 status 优先级用例；移动/小程序已补最小触控 token 底座；小程序语义 token 层已补并迁移首页/聊天/个人中心与 `app.config.ts`；`docs/design/cross-platform-token-drift.md` 已产出三端 token 漂移清单；`docs/release/mobile-error-state-release-notes.md` 已补错误态发布说明草案 | 代码级、uni-app 基座、跨设备续接 rehearsal 与 iOS Simulator 支持性 app-run 已具备；品牌主色最终统一仍待定；Android、交互式 WeChat DevTools、真实/官方 iOS 设备故事、DCloud App 云打包/签名、移动远控跨设备 host 回传、共享预发账号跨设备连续会话或真机证据仍不足 |

## 3. 发布前新增测试要求

- 外部资源交接：新增或变更支付/电签/签名/真机/connector 资料项时，先更新 `docs/release/external-resource-requirements.json`，再跑 `node scripts/validate-external-resource-requirements.cjs`、`node scripts/validate-commercial-delivery-checklist.cjs`、`node scripts/validate-commercial-delivery-lanes.cjs` 和 `bash scripts/commercial-readiness-gate.sh --quick`。
- 支付/电签：先用 `scripts/sandbox-evidence-runner.py` 生成脱敏预检/live JSON，再补每个真实渠道至少 7 天沙箱日志，覆盖成功、失败、重试、撤销/退款，并更新 `docs/release/evidence/payment-sandbox.md` / `esign-sandbox.md`。
- 桌面同步：unsigned `app,dmg`、unsigned release packaged runtime smoke（含 packaged-binary sync loopback）、unsigned release packaged-profile/performance smoke 和 cross-device code rehearsal 已通过；下一步补齐 Tauri signingIdentity、Apple codesign identity 和 notary credentials，再补 signed/notarized installer packaging、signed packaged-profile plaintext-to-SQLCipher 迁移实录、signed packaged runtime performance、共享预发后端 sync transcript 和共享预发账号跨设备连续会话证据，并更新 `docs/release/evidence/desktop-runtime-smoke.md`。
- RAG：内建法律知识库 full50 已闭合；后续如果接入外部客户知识库，需要另建外部语料 golden/corpus、复跑 `eval/rag_live_qdrant_full50.py` 和 `eval/rag_quality.py`，并把它作为上线后质量扩展而不是当前内建 RAG 阻断项。
- 案件/任务：已补核心状态机非法跳转、终态只读、owner/assignee/admin 过滤；仍需 Playwright 全流程和全矩阵。
- 专业服务市场：已补律师/律所 P0 的 local 模式拒绝、历史当事人利益冲突投标阻断和同分曝光轮询；仍需律所 RBAC 全矩阵、8 API 打勾、重复评价，并继续扩展税务/财务服务方模型和验收。
- 全设备智能助手：桌面主工作站最小入口、TopSecret-safe action model、浏览器级 Settings 工作站路由/移动宽度证据、本地 LLM/模型数量/离线队列/知识库/MCP 只读探针、secret-free 环境配置档 CRUD、桌面快问独立窗口 code/browser evidence、`我的设置`/`治理后台`入口去冗余、LLM 配置组织级 CRUD/API key 遮罩边界、治理后台模型配置入口、MCP/工具连接治理入口、Skills connector 后端组织级凭据 CRUD/credential_keys 遮罩/审计脱敏、Skills connector 前端凭据保留/新增/替换/删除体验、移动远控 DB-backed 控制面、后端 host lifecycle API、桌面 IPC host 客户端、bounded safe-probe poll、env-gated 后台 safe-probe daemon 基础和移动端状态入口已补；下一步补真实 provider 密钥联调、signed runtime daemon 运行证据与高风险真实执行器、真实移动远控跨设备联调、真实 approved connector runtime、商业多进程撤销运行时证据、packaged runtime 快捷键实测和 signed runtime 出站 fail-closed 测试。
- 可信会话与 Skills 进化：本地和 DB-backed SkillEvolutionProposal/eval gate/审批/灰度/回滚测试已补，AgentApproval/AgentAuditEvent 模型、AgentApprovalService、`/agent-approvals` API、`/skill-governance` API、最小前端 Agent 治理工作台和 governed session artifact 记忆写入门禁已补，workspace-control 默认在真实运行时未接入前 fail-closed，observe 已有代码级只读旁听快照，显式 `workspace_runtime.mode=local_rehearsal` 可完成本地 pause/takeover/terminate rehearsal，已批准工作室成果 list/create/revise/export 已有 append-only revision audit，桌面聊天工作台已有长任务 runtime summary artifact event 展示/缓存代码级闭环；下一步补完整工具状态/证据引用、签名/商业 runtime 长任务 replay、真实暂停/恢复/接管/终止执行效果、跨设备恢复、完整记忆治理 UI/运行时接入和真实执行链路失权测试。
- 风险调查：缓存 org 隔离、风险分可解释性、robots/UA/频控入口、200 条意图路由评测已有代码级证据；仍需预发网络真实 dry-run。
- 移动/小程序：按 `docs/design/cross-platform-token-drift.md` 决定品牌主色最终统一方向，并补 iPhone/Android/微信开发者工具关键故事、DCloud App 云打包/签名和共享预发账号跨设备续接手测记录，再更新 `docs/release/evidence/mobile-device-smoke.md`。

## 4. 当前不应作为完成证据的信号

- 全量 pytest 通过：未覆盖真实渠道沙箱和真机。
- 前端 build 通过：不证明业务路径真实可用。
- `cargo check` 通过：不证明 Tauri packaged UI runtime push/pull、冲突管理页、重试和签名安装包 profile 真实可用。
- provider fake client 测试通过：不证明商户后台路径、事件名和证书轮换匹配。
