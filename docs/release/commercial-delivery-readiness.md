# 商业交付就绪评估

> 日期：2026-05-07
> 判定：Not ready for commercial launch.
> 口径：代码级绿灯不等于商业交付绿灯。发布需要真实渠道、真机、回滚和运营证据。

## 1. 发布判定

| 维度 | 当前状态 | 发布判定 |
|---|---|---|
| 后端默认回归 | `467 passed, 1 skipped, 17 warnings in 36.11s` | 通过代码级门槛 |
| 前端 lint/build/test/security | lint/tsc 通过、Vitest `10 files / 34 tests passed`，生产依赖 `npm audit --omit=dev` 已写入 `docs/release/evidence/artifacts/frontend-npm-audit-prod-20260507.json` 且 `0` vulnerabilities；保留既有 Vite chunk/eval warning 作为性能/打包优化项 | 通过当前门槛 |
| GitNexus 知识图 | 当前提交级索引已重建，`.gitnexus/meta.json` 为 `1181 files / 30003 nodes / 54587 edges / 300 flows / 28219 embeddings`，`capabilities.vectorSearch.status=vector-index`；`npx -y gitnexus@latest status` 显示 up-to-date；direct rc binary 的 `cypher/context/query` smoke 已通过且 `query` timing 显示 vector/BM25 路径可读 | embeddings gate 已过；semantic/context 可做导航，但不能替代源码和测试证据 |
| 支付真实渠道 | 微信/支付宝代码级协议已落，`scripts/sandbox-evidence-runner.py` 已提供脱敏预检/live 采集入口，runner 安全测试已覆盖 live 确认门和脱敏写出，缺沙箱/证书轮换/重试证据 | 阻断 |
| 电签真实渠道 | e签宝/法大大代码级协议已落，`scripts/sandbox-evidence-runner.py` 已提供脱敏预检/live 采集入口，runner 安全测试已覆盖 live 确认门和脱敏写出，缺商户沙箱/事件目录/灰度证据 | 阻断 |
| 桌面同步 | 后端 `SyncLog` 持久化增量日志 + Rust SQLCipher/keyring 本地库 + 注入式同步闭环测试 + SQLite migration SQL fresh/legacy temp DB smoke + local installed-profile keyring/reopen smoke + SQLite 100/500 本地性能基线 + debug binary self-test + 冲突管理页 + 代码级重试退避 + `scripts/desktop-sqlite-security-gate.sh` 安全门禁通过；既有 artifact 记录过 unsigned debug macOS `.app` bundle self-test/runtime/WebView page-load，但 fresh local 复跑当前 AppKit abort，不能作为稳定 passing evidence；`desktop/Entitlements.plist` 已切到 production APNs entitlement；`scripts/desktop-release-package.sh --dry-run` 和 `scripts/desktop-release-preflight.sh` 已写出脱敏预检并新增 `hdiutil` / DiskManagement probe；unsigned release `.app` + DMG 已在 unsandboxed macOS 环境构建通过；unsigned release packaged runtime self-test/startup/WebView page-load smoke 已通过；unsigned release packaged-profile plaintext-to-SQLCipher/keyring reopen 和 SQLCipher 100/500 performance smoke 已通过；签名/公证、signed installer/signed packaged-profile migration/signed packaged runtime 性能/跨端连续会话未闭环 | 阻断 |
| RAG/案件/市场/风险 | RAG P0-2 引用回链已有代码级闭环，live Qdrant smoke 已跑，内建法律知识库 full50 已跑通 `42` chunks / `50` questions / recall@10 `1.000` / MRR `1.000` / NDCG@10 `0.997`，`knowledge_management` RBAC/PII 已补，图谱 1k 降采样/FPS smoke 已补；案件状态机/任务 owner、律师市场 local guard/冲突阻断/公平轮询、尽调缓存 org 隔离、风险评分解释性、爬虫合规入口、200 条意图路由评测已补；知识管理持久化、案件/市场全矩阵与真实流程证据仍未闭合 | 部分完成 |
| 移动/小程序真机 | `scripts/mobile-device-smoke.sh` 已通过本地门禁：移动端测试/tsc、Expo config/SDK dependency guard、小程序 tsc/build、WeChat DevTools CLI project smoke、refresh auth guard、fake fallback guard、mini-program design token guard；`npx expo-doctor` `17/17 checks passed`；messages/tasks 详情页已移除静默假数据兜底；移动/小程序 refresh-token 已避免弱网误清会话；移动 production `npm audit --omit=dev` 已清零并写入 `mobile_npm_audit.status=passed,total=0`；缺完整真机/交互式验收 | 阻断 |
| 发布证据脱敏 | `scripts/release-evidence-secret-scan.sh` 已纳入商业门禁，当前 `docs/release/evidence/` 未发现明文私钥、access/refresh token、手机号或身份证号 | 通过当前门槛；后续新增真实日志/JSON 后必须复跑 |

## 2. 必须补齐的商业证据

### 渠道沙箱

- 微信支付：下单、查单、关单、退款、支付成功回调、平台证书/公钥轮换、失败重试。
- 支付宝：page.pay、query、refund、close、异步通知、notify_id 重试。
- e签宝：创建/启动流程、签署链接、状态查询、签署完成回调、撤销、签署文件下载。
- 法大大：access token、sign-task create、actor url、detail、download url、cancel、FASC 回调事件。

### 产品闭环

- 桌面端本地数据 push/pull 已有 Rust SQLCipher/keyring 代码路径、注入式 push/pull/retry 测试、SQLite migration SQL fresh/legacy temp DB smoke、SQLCipher plaintext migration 单测、local installed-profile keyring/reopen smoke、SQLite 100/500 本地性能基线、debug binary migration/table/security self-test、冲突管理页、代码级 retry/backoff、桌面 SQLite 安全门禁、production APNs entitlement、release package dry-run、signed/notarized release preflight、unsigned release `.app`/DMG build、unsigned release packaged runtime smoke、unsigned release packaged-profile migration smoke 和 unsigned release packaged SQLCipher performance smoke；还需配置签名/公证身份，产出 signed/notarized release `.app`/DMG、补 signed packaged-profile plaintext migration 实装证据、signed packaged runtime 性能和跨端连续会话证据。
- RAG 权限过滤、PII 脱敏、source 字段、前端引用预览/高亮、Playwright 点击证据、导出文档/chunk/anchor 巡检、live Qdrant smoke 和内建法律知识库 full50 live baseline 已有证据。
- 案件状态机、任务 owner、律师市场 local guard/利益冲突/公平轮询已有核心正反向测试；仍需律所 RBAC 全矩阵、案源市场 8 API 打勾和 Playwright 三角联通。
- 风险调查已补尽调缓存 org 隔离、风险评分解释性、crawler 合规入口和 200 条意图路由评测；仍需在预发网络补真实 dry-run 日志。
- 移动端和小程序真机覆盖登录、审批、消息/任务详情、会话延续、错误态；本地 fake fallback guard 已过，但真机和跨设备证据仍需补齐。

## 3. 发布前必须通过的命令

```bash
cd backend && ./.venv/bin/pytest -q
cd backend && ./.venv/bin/ruff check src tests
cd backend && ./.venv/bin/mypy src
cd frontend && npm run lint
cd frontend && npm test
cd frontend && npm run build
cd frontend && npx playwright test e2e/role-access.spec.ts e2e/document-flows.spec.ts e2e/contract-lifecycle.spec.ts --project=chromium
bash scripts/mobile-device-smoke.sh
python3 scripts/sandbox-evidence-runner.py --scope payment --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json
python3 scripts/sandbox-evidence-runner.py --scope esign --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json
bash scripts/release-evidence-secret-scan.sh
cd desktop && cargo check
cd desktop && cargo test
bash scripts/desktop-sqlite-security-gate.sh
bash scripts/desktop-runtime-smoke.sh --with-app-bundle \
  --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-YYYYMMDD.json \
  --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-YYYYMMDD.log
bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-YYYYMMDD.json
bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-YYYYMMDD.json
bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json
```

当前 Ruff 与 backend mypy 均已清零；`scripts/mypy-baseline-check.sh` 默认 ceiling 已降为 `0`，任何新增 mypy 错误都应阻断发布。`docs/release/evidence/static-quality-baseline.md` 已记录当前 owner、2026-05-20 过期策略和零回退规则。

## 4. 当前完成度审计

最新 prompt-to-artifact 审计见 `docs/release/completion-audit.md`。该审计明确当前目标尚未完成，阻断项集中在支付/电签真实沙箱、桌面 signed/packaged runtime 和移动/小程序真机。

商业发布 gate：

```bash
bash scripts/commercial-readiness-gate.sh --quick
```

当前该命令应当失败；GitNexus embeddings 零值阻断已解除，RAG 内建 full50、桌面 SQLCipher/keyring 代码级门禁、unsigned release `.app`/DMG build、unsigned release packaged runtime smoke、unsigned release packaged-profile/performance smoke 和 signed/notarized release preflight 已通过，但只有当外部证据、桌面 signed/packaged-profile/performance/cross-device 证据、移动真机和全仓质量基线全部补齐后才允许转 Go。
当前工作树仍有未提交/未跟踪改动；GitNexus metadata 是 commit-scoped，`scripts/commercial-readiness-gate.sh` 会将 dirty worktree 作为 release-blocking failure。发布 Go 前必须将交付文件纳入版本控制并重新运行 GitNexus 复验。

外部证据模板位于 `docs/release/evidence/`，每份模板只有在对应真实证据齐全后才能把 `Status: pending` 改为 `Status: complete`。
并行采集执行清单见 `docs/release/evidence-collection-runbook.md`；支付、电签、桌面、RAG 和移动/小程序可以并行采集，但最终必须统一回到本文件和 `scripts/commercial-readiness-gate.sh`。
外部输入缺口集中见 `docs/release/external-inputs-checklist.md`，用于拆给支付/电签/桌面/RAG/真机负责人并行准备。
商业门禁会拒绝“顶部已标 complete，但 Owner/Environment/Date range 仍是 TBD、Required Scope 表格仍含 pending/TBD/缺失信号，或 artifact reference 为空”的 evidence 文件；不能只改状态行绕过验收。

## 5. Go/No-Go 标准

Go 条件：

- 所有 P0 任务关闭，且每项有测试/沙箱/真机证据。
- release 文档齐全并与当前代码一致。
- 支付、电签、对象存储、同步均有失败/重试/幂等/回滚测试。
- 生产密钥轮换、日志脱敏、审计和监控告警已演练。

No-Go 条件：

- 任一真实渠道仅有 mock/fake client 证据。
- GitNexus 图谱显示低风险但 `rg`/源码显示新增未入图符号。
- GitNexus metadata up-to-date 但工作树仍有未提交或未跟踪交付文件。
- 任一移动/小程序/桌面关键路径仍通过静默 fallback 掩盖后端错误。
- 数据迁移无 downgrade 或恢复演练。
