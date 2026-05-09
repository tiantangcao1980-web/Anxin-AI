# 商业发布证据并行采集 Runbook

> 日期：2026-05-07
> 状态：执行清单已就绪；真实外部证据仍未齐。本文不保存任何密钥、账号密码、手机号、身份证号或合同原文。

## 1. 执行原则

- 所有真实渠道证据先写入 `docs/release/evidence/artifacts/` 的脱敏 JSON、日志摘要或截图索引，再回填对应 evidence 文件。
- `docs/release/evidence/*.md` 只有在该文件 Required Scope 的每一行都有真实 artifact reference 后，才允许从 `Status: pending` 改为 `Status: complete`。
- 外部账号、证书、设备、语料和 release 包输入清单集中维护在 `docs/release/external-inputs-checklist.md`。
- 外部资源到位后的执行交接单维护在 `docs/release/external-resource-handoff.md`。
- 多智能体或多人并行时，每条线只更新自己的 evidence 文件和 artifact，最后由发布主控统一跑 `scripts/commercial-readiness-gate.sh`。
- 并行 lane 的机器清单维护在 `docs/release/commercial-delivery-lanes.json`；任何 lane 拆分或写入范围变化后，先跑 `node scripts/validate-commercial-delivery-lanes.cjs`。
- 新增真实日志后必须跑 `bash scripts/release-evidence-secret-scan.sh`，避免把商户私钥、access token、手机号、身份证号或合同内容写入仓库。

## 2. 并行分工矩阵

| 线 | 可并行负责范围 | 前置输入 | 首个命令 | 完成判定 |
|---|---|---|---|---|
| 支付 | 微信支付、支付宝沙箱和 webhook 重试证据 | 公网 callback URL、WeChat Pay app/merchant/key/cert 配置、Alipay app/key 配置、官方 webhook enable | `python3 scripts/sandbox-evidence-runner.py --scope payment --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json` | `docs/release/evidence/payment-sandbox.md` 所有行均有真实 artifact reference |
| 电签 | e签宝、法大大签署、撤销、下载、回调证据 | e签宝/法大大 sandbox app ID/secret、官方 webhook enable、可公开访问的测试合同文件或文件 ID | `python3 scripts/sandbox-evidence-runner.py --scope esign --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json` | `docs/release/evidence/esign-sandbox.md` 所有行均有真实 artifact reference |
| 桌面发布 | signed/notarized `.app`/DMG、packaged UI interaction、packaged profile migration、packaged runtime 性能 | Tauri signingIdentity、Apple codesign identity、notarytool credential、release build host；production APNs entitlement 已在仓库内配置；unsigned release runtime/profile/performance 支撑证据已有 | `bash scripts/desktop-release-package.sh --dry-run --out docs/release/evidence/artifacts/desktop-release-package-dry-run-YYYYMMDD.json --preflight-out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json`；本地支撑复验可跑 `bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-YYYYMMDD.json` | package dry-run/preflight `release_ready=true`，且 `desktop-runtime-smoke.md` 的 signed packaged runtime/profile 行全部完成 |
| RAG full50 | 真实业务语料、商业 golden、live Qdrant metrics | 无 `smoke: true` 的 commercial full50 golden、覆盖全部 relevant chunk 的业务语料 JSON/JSONL、staging/live Qdrant | `python3 eval/rag_live_qdrant_full50.py --golden <commercial-full50-golden.jsonl> --corpus <business-corpus.jsonl> --preflight-only` | 生成 `eval/rag_live_predictions_full50.json` 和 `eval/rag_live_baseline_full50.json`，并更新 `rag-full50-live-baseline.md` |
| 移动/小程序 | iOS、Android、微信开发者工具或真机路径 | TestFlight/Android build 或 dev client、小程序开发者工具、测试账号、后端环境 | `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-YYYYMMDD.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-YYYYMMDD.json` | `mobile-device-smoke.md` 记录设备、OS、build、截图/日志和跨设备连续会话 |

## 3. 支付线操作顺序

1. 以 `.env.example` 或 `backend/.env.example` 为模板，在 secret manager 或本地受控环境设置支付配置，不写入仓库；两个模板均显式列出了 `scripts/sandbox-evidence-runner.py` 所需的 WeChat Pay / Alipay 字段。
2. 运行预检：

```bash
python3 scripts/sandbox-evidence-runner.py --scope payment \
  --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json
```

3. 预检显示 WeChat Pay 和 Alipay 均 `configured=true` 后，检查 artifact 中的 `runtime_prerequisites` 和 `external_evidence_requirements`。退款、查单和关单需要已存在的沙箱订单 ID；官方回调、重复幂等、失败重试和平台 key/cert 轮换需要渠道后台或 callback/retry 日志 artifact；缺少这些运行时前置物时，live 会把对应步骤标为 `skipped`，不能作为完整商业证据。
4. 分别运行 live：

```bash
python3 scripts/sandbox-evidence-runner.py --scope wechat_pay --live --confirm-live-side-effects \
  --wechat-refund-order-id <paid-sandbox-order-id> \
  --refund-amount 0.01 \
  --refund-total-amount <original-order-amount> \
  --out docs/release/evidence/artifacts/wechat-pay-live-YYYYMMDD.json

python3 scripts/sandbox-evidence-runner.py --scope alipay --live --confirm-live-side-effects \
  --alipay-query-order-id <existing-sandbox-order-id> \
  --alipay-refund-order-id <paid-sandbox-order-id> \
  --alipay-close-order-id <open-sandbox-order-id> \
  --refund-amount 0.01 \
  --out docs/release/evidence/artifacts/alipay-live-YYYYMMDD.json
```

5. 从渠道后台导出或截图订单、退款、关闭、异步通知、失败重试和证书/公钥轮换记录，逐项回填 artifact 中 `external_evidence_requirements[].artifact_ref` 的脱敏 artifact reference。
6. 更新 `docs/release/evidence/payment-sandbox.md`，每一行保留可追溯 artifact reference。

## 4. 电签线操作顺序

1. 以 `.env.example` 或 `backend/.env.example` 为模板配置 e签宝/法大大 app ID、app secret、API URL 和官方 webhook 开关；真实 secret 只写入本地 `.env` 或 secret manager。
2. 准备沙箱合同文件，确保文件内容无真实客户 PII。
3. 运行预检：

```bash
python3 scripts/sandbox-evidence-runner.py --scope esign \
  --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json
```

4. 预检显示 e签宝和法大大均 `configured=true` 后，检查 artifact 中的 `runtime_prerequisites` 和 `external_evidence_requirements`。创建签署流需要沙箱合同文件 URL 或 file ID；下载完成合同需要已完成签署的 flow ID；官方回调、重复幂等和失败重试需要 provider callback/retry 日志 artifact。缺少这些运行时前置物时，live 会把对应步骤标为 `skipped`，不能作为完整商业证据。
5. 分别运行 live：

```bash
python3 scripts/sandbox-evidence-runner.py --scope esignbao --live --confirm-live-side-effects \
  --esign-document-url <sandbox-file-id-or-doc-url> \
  --esignbao-completed-flow-id <completed-sandbox-flow-id> \
  --out docs/release/evidence/artifacts/esignbao-live-YYYYMMDD.json

python3 scripts/sandbox-evidence-runner.py --scope fadada --live --confirm-live-side-effects \
  --esign-document-url <sandbox-doc-id-or-url> \
  --fadada-completed-flow-id <completed-sandbox-flow-id> \
  --out docs/release/evidence/artifacts/fadada-live-YYYYMMDD.json
```

6. 补签署完成、撤销、下载、官方回调、重复回调幂等和失败重试 evidence。
7. 更新 `docs/release/evidence/esign-sandbox.md`。

## 5. 桌面发布线操作顺序

1. 配置 Tauri `signingIdentity`、Apple code signing identity、notarization credential，并确认 `desktop/Entitlements.plist` 的 `com.apple.developer.aps-environment` 保持 `production`。
2. 先采集 repo 内 debug `.app` 支撑证据；`desktop-release-preflight.sh` 会优先读取这些 repo artifact，再回退到环境变量或 `/tmp`：

```bash
bash scripts/desktop-runtime-smoke.sh --with-app-bundle \
  --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-YYYYMMDD.json \
  --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-YYYYMMDD.log
```

3. 运行 release package dry-run 和 preflight：

```bash
bash scripts/desktop-release-package.sh --dry-run \
  --out docs/release/evidence/artifacts/desktop-release-package-dry-run-YYYYMMDD.json \
  --preflight-out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json

bash scripts/desktop-release-preflight.sh \
  --out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json
```

4. 当 package dry-run/preflight `release_ready=true` 后，去掉 `--dry-run` 构建 signed/notarized release `.app` 和 DMG。
5. 使用 packaged app 复跑 SQLCipher/keyring reopen、plaintext migration、push/pull、conflict、retry/backoff、100/500 性能和 cross-device continuation。
6. 更新 `docs/release/evidence/desktop-runtime-smoke.md`。

## 6. RAG Full50 线操作顺序

1. 导出商业 full50 golden，禁止 `smoke: true` 行。
2. 导出真实业务语料，确保包含每个 golden `relevant_chunk_id` 和预期 `law_ref`。
3. 先跑覆盖预检：

```bash
python3 eval/rag_live_qdrant_full50.py \
  --golden <commercial-full50-golden.jsonl> \
  --corpus <business-corpus.jsonl> \
  --preflight-only \
  --out docs/release/evidence/artifacts/rag-full50-preflight-YYYYMMDD.json
```

4. 预检通过后跑 live Qdrant：

```bash
./backend/.venv/bin/python eval/rag_live_qdrant_full50.py \
  --golden <commercial-full50-golden.jsonl> \
  --corpus <business-corpus.jsonl> \
  --out eval/rag_live_predictions_full50.json \
  --collection rag_eval_full50_live \
  --run-label commercial-full50-YYYYMMDD

python3 eval/rag_quality.py \
  --golden <commercial-full50-golden.jsonl> \
  --predictions eval/rag_live_predictions_full50.json \
  --out eval/rag_live_baseline_full50.json \
  --run-label commercial-full50-YYYYMMDD
```

5. 确认 predictions 与 metrics artifact 都带 `commercial_provenance`，且 `non_commercial_override_count=0`、`smoke_question_count=0`。`--allow-fixture-corpus`、`--allow-smoke-golden`、`--allow-missing-law-refs` 只允许配合 `--preflight-only` 做非商业 dry run，不能生成 release evidence。
6. 更新 `docs/release/evidence/rag-full50-live-baseline.md`。

## 7. 移动/小程序线操作顺序

1. 先跑本地代码级门禁：

```bash
bash scripts/mobile-device-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-mini-code-smoke-YYYYMMDD.json \
  --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-YYYYMMDD.json
```

2. 使用 `mobile-device-manual-template-YYYYMMDD.json` 的字段记录 iOS、Android、微信开发者工具或真机证据，分别覆盖登录、审批详情、消息详情、任务详情、聊天延续、设置错误态、小程序 `wx.login -> code2session`、假资讯 fallback 清理和跨设备连续会话。
3. 记录设备型号、OS、build hash、后端环境、测试账号角色、截图或日志 artifact reference；截图、视频、日志必须先脱敏，不写手机号、身份证号、真实合同内容或 access token。
4. 更新 `docs/release/evidence/mobile-device-smoke.md`，再运行 `python3 scripts/validate-release-evidence.py docs/release/evidence/mobile-device-smoke.md|mobile-device-smoke` 与 `bash scripts/release-evidence-secret-scan.sh`。

## 8. 汇总放行

所有线完成后由发布主控顺序运行：

```bash
python3 scripts/release-worktree-inventory.py
git diff --check
bash scripts/release-evidence-secret-scan.sh
GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus \
  bash scripts/commercial-readiness-gate.sh --quick
```

如果商业门禁仍失败，不能把任何 evidence 文件标记为 complete。若工作树仍有未提交/未跟踪交付文件，先用 `release-worktree-inventory.py` 确认没有 `local_secret` 或 `unknown` 分类；`generated_or_runtime` 分类必须由发布主控逐项确认是否纳入提交。整理提交后，再重跑 GitNexus 和商业门禁；`commercial-readiness-gate.sh --quick` 会拒绝 `.gitnexus/meta.json` 缺失或落后于当前 `HEAD` 的 `lastCommit`。
