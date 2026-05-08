# 48 小时商业交付倒排计划

> 日期：2026-05-08
> 基线：当前仓库的代码级门禁大多已过，RAG 内建 full50 已闭合，前端和移动 production dependency audit 已清零；真正阻断点集中在支付/电签真实资源、桌面 signed/notarized package 与 packaged runtime、移动真机/交互式验证、桌面主工作站/移动远控/任意 LLM-Skills-MCP 配置证据，以及发布前 clean worktree / GitNexus 复验。
> 规则：没有真实资源就只做预检、代码级收口和证据模板，不用 mock/fake 伪造 live 结果。

## 当前执行快照

| 维度 | 当前事实 | 48 小时内处理口径 |
|---|---|---|
| GitNexus | 当前 `.gitnexus/meta.json` 有非零 embeddings，但 direct CLI repo 解析/cypher 复验失败且索引落后于最新本地提交；精确统计以复跑后的 `.gitnexus/meta.json` 与 `gitnexus cypher` 计数为准，vector gate 要求 meta/Cypher embeddings 非零且一致；历史 dirty snapshot 曾为 `380 files / 6037 symbols / critical`，当前不能把该历史影响面当作最新工作树结论 | 本轮开发继续以 `rg`、源码阅读和测试为主，GitNexus 仅作历史上下文；最终 release 前必须重跑 GitNexus |
| release artifacts | `python3 scripts/validate-release-artifacts.py` -> `PASS (25 JSON artifacts)`；`bash scripts/release-evidence-secret-scan.sh` -> `PASS`；`git diff --check` -> `PASS` | 新增真实证据后立即复跑 artifact validator 和 secret scan |
| 工作树 | 本轮本地交付已有提交，但 GitNexus 尚未重建到最新提交；后续外部证据增量仍只接受可追踪 release artifact | 42-48h 必须复跑 `release-worktree-inventory`，确认 `local_secret=0`、`unknown=0`，并在新增交付文件后重新提交和复验 GitNexus |
| 桌面 | unsigned release `.app` + DMG 已在 unsandboxed macOS 环境构建通过；unsigned release packaged runtime self-test/startup/WebView page-load smoke 已通过；unsigned release packaged-profile plaintext-to-SQLCipher/keyring reopen 和 SQLCipher 100/500 performance smoke 已通过；release preflight 新增 `hdiutil` / DiskManagement probe 且当前通过；preflight 仍缺 signing identity / codesign identity / notarization / code-sign verification / signature authority | 补签名/公证输入和 signed packaged-profile/performance/cross-device evidence |
| 移动/小程序 | 2026-05-08 复跑 `scripts/mobile-device-smoke.sh` 通过：mobile `7 files / 19 tests`、tsc、mobile result surface guard、mobile lawyer conversion guard、Expo doctor `17/17`、mobile npm audit `0`、mini tsc/build、mini privacy boundary guard、WeChat DevTools CLI project smoke、refresh/mobile+mini privacy/fallback/design-token guards，并写出 `mobile-mini-code-smoke-20260508.json` / `mobile-device-manual-template-20260508.json`；移动请求层已透传 `X-Privacy-Mode` 且 local 模式 fetch 前 fail-closed；移动尽调/知识库搜索已有页面内结果摘要；移动找律师已从纯列表升级为匿名咨询/律师选择/匿名聊天室/委托 API 转化链路；小程序请求层已透传 `X-Privacy-Mode`，local/top-secret 在数据请求和登录前 fail-closed；host probe 更新为 `mobile-device-host-probe-20260508.json`，确认 iOS Simulator 可用、Android device/emulator 仍缺 | 代码级已稳；商业证据还缺 iOS app-run、Android、交互式 WeChat DevTools 或真机、跨设备连续会话、移动远控桌面 |
| 全设备智能助手 | LLM/MCP/Skills/knowledge/local LLM 底座已在后端、桌面和移动隐私上下文中存在；2026-05-08 OpenSpec 已把桌面主工作站、移动远控、任意模型/Skills/MCP、独立知识库和本地模型安全列为验收 | 48 小时内先冻结规范和证据模板；真实交付需补配置 UI、权限回归、远控协议和绝密模式出站拦截证据 |
| 可信会话与进化治理 | 2026-05-08 OpenSpec 已补 Codex/Claude 式过程可见、artifact-first、可打断/恢复、能力可发现体验，并把 Skills 进化和 agent 自我改进纳入评测/审批/回滚治理；本地 Skill Evolution Gate 已补 proposal、required eval、授权审批、灰度、回滚、审计和 governed Skill 版本过滤测试 | 48 小时内继续补 release 证据口径；真实交付还需长任务事件流、artifact 编辑、跨设备恢复、持久化 SkillGovernance/记忆治理和真实执行链路失权证据 |
| 商业门禁 | clean baseline 上 `commercial-readiness-gate.sh --quick` 仍 FAIL：Not ready 声明、payment/e-sign/desktop/mobile evidence pending；本轮文档/证据增量提交前也会触发 dirty-worktree 防线 | 失败是正确防线；不能改状态绕过，必须补真实证据或保留 blocker |

## 约定

| 标签 | 含义 |
|---|---|
| 本地可完成 | 不依赖外部密钥、证书、真机、第三方后台或真实语料即可完成 |
| 需用户申请后给密钥/证书 | 需要用户/运营/安全先申请并交付，拿到后才能进入 live 或签名步骤 |
| 需真机/交互式验证 | 需要 iOS、Android、WeChat DevTools、已签名桌面包或人工点击才能完成 |

## 支付/电签在无真实资源时的处理口径

- 功能完成的口径是代码和协议闭环，不是 live 渠道闭环。
- 先完成本地代码级验证：请求签名、响应验签、幂等、回调验签、失败重试、状态回写、证据模板。
- `docs/release/evidence/payment-sandbox.md` 和 `docs/release/evidence/esign-sandbox.md` 保持 `Status: pending`，直到真实 sandbox/pre-production 资源到位。
- `python3 scripts/sandbox-evidence-runner.py --scope payment|esign --out ...` 只做预检；没有 `--live --confirm-live-side-effects` 就不要把结果当作商业证据。
- 任何 mock/fake 成功截图、伪造 callback、伪造订单 ID 都不计入 release evidence。
- 等待资源期间，支付/电签 lane 继续保留为阻断项，但其他 lane 可以并行推进。

## 0-6h

| 项目 | 内容 |
|---|---|
| 负责人 | 发布主控；各 lane 负责人先不等资源，先把缺口锁死 |
| 本地可完成 | 跑 `release-worktree-inventory`、secret scan、static quality baseline，确认当前只剩已知阻断；把支付、电签、桌面、移动、全设备智能助手配置/远控、可信会话与 Skill 进化证据状态逐项复核；RAG 内建 full50 证据保持 complete |
| 需用户申请后给密钥/证书 | 统一向用户提交资源申请单：支付 callback URL / 商户号 / 证书 / 私钥 / 平台公钥 / API v3 key；电签 app ID / secret / API URL / 测试合同；桌面 signing identity / Apple code signing identity / notary credential；移动测试设备与测试账号 |
| 需真机/交互式验证 | 暂不进入，只预留设备和人工窗口 |
| 产物 | `release-worktree-inventory` 摘要、secret scan 结果、外部输入申请清单、各 lane 缺口清单、待办顺序 |
| 验证命令 | `python3 scripts/release-worktree-inventory.py --json`<br>`git diff --check`<br>`bash scripts/release-evidence-secret-scan.sh`<br>`bash scripts/static-quality-baseline.sh --out /tmp/anxin-static-quality-baseline.md` |
| 退出标准 | 已明确当前阻断项且没有新增 unknown/local_secret；外部资源申请已发出；本地命令无新增回退 |

当前执行快照：历史大 dirty snapshot 已被上一轮提交收束；本轮审计新增/更新的 release 文档和 host probe 必须继续保持 `unknown=0`、`local_secret=0`。前端和移动 production dependency audit 均已清零；支付/电签 runner 已补 live honest-gating，退款 `pending`、关单/取消 `False`、无 signer URL、空签署文件下载不再被误报为完成；artifact validator、release evidence secret scan 和 `git diff --check` 当前通过；clean baseline 上 `commercial-readiness-gate.sh --quick` 仍正确失败于 Not ready 声明和 payment/e-sign/desktop/mobile evidence pending。

## 6-18h

| 项目 | 内容 |
|---|---|
| 负责人 | 支付 lane 负责人、电签 lane 负责人、资源申请责任人、发布主控 |
| 本地可完成 | 先跑支付/电签 preflight，更新证据模板结构，准备 live 运行参数；同时保持后端回归、前端构建和 release gate 的可重复执行 |
| 需用户申请后给密钥/证书 | 真实支付 sandbox/pre-production 配置和 callback URL；真实电签 sandbox/pre-production 配置和测试合同；如果桌面签名资源已到，也要同步收齐 signing / notarization 输入 |
| 需真机/交互式验证 | 先预约，不执行；这段时间只确认设备可用窗口、账号角色、WeChat DevTools 环境和测试后端地址 |
| 产物 | `payment-sandbox-preflight-YYYYMMDD.json`、`esign-sandbox-preflight-YYYYMMDD.json`、资源到位/未到位对照表、支付和电签的 live 运行参数清单 |
| 验证命令 | `python3 scripts/sandbox-evidence-runner.py --scope payment --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json`<br>`python3 scripts/sandbox-evidence-runner.py --scope esign --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json`<br>`cd backend && ./.venv/bin/pytest -q tests/test_payment_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_refund_idempotency.py`<br>`cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py` |
| 退出标准 | 两条 lane 的 preflight 已落盘；runner 会把非终态 live 结果诚实标为 pending/fail；如果资源没到，证据文件仍保持 pending，但缺口已被清楚记录；如果资源到了，已能直接切 live |

## 18-30h

| 项目 | 内容 |
|---|---|
| 负责人 | 支付 lane 负责人、电签 lane 负责人、桌面 lane 负责人、发布主控 |
| 本地可完成 | 在资源到位前先完成所有本地回归；资源到位后优先执行支付和电签 live；桌面 unsigned app+DMG、unsigned packaged runtime、unsigned packaged-profile migration 和 unsigned packaged SQLCipher performance 已验证，下一步聚焦签名/公证输入、signed packaged-profile、signed runtime performance 和 cross-device evidence；RAG 内建 full50 只需守住 artifact 验证 |
| 需用户申请后给密钥/证书 | 支付真实沙箱密钥和证书、官方 webhook 开关；电签 app ID / secret / webhook 开关；桌面 signing identity / Apple code signing / notary credential |
| 需真机/交互式验证 | 若桌面 signed app 已产出，则开始交互式安装/启动验证；若移动设备已预约，则准备进入手测 |
| 产物 | 支付 live artifact、e 签 live artifact、桌面 preflight JSON、首轮真实 callback / retry / download / revoke 记录 |
| 验证命令 | `python3 scripts/sandbox-evidence-runner.py --scope wechat_pay --live --confirm-live-side-effects --wechat-refund-order-id <paid-order> --refund-amount 0.01 --refund-total-amount <original-total> --out docs/release/evidence/artifacts/wechat-pay-live-YYYYMMDD.json`<br>`python3 scripts/sandbox-evidence-runner.py --scope alipay --live --confirm-live-side-effects --alipay-query-order-id <query-order> --alipay-refund-order-id <paid-order> --alipay-close-order-id <open-order> --refund-amount 0.01 --out docs/release/evidence/artifacts/alipay-live-YYYYMMDD.json`<br>`python3 scripts/sandbox-evidence-runner.py --scope esignbao --live --confirm-live-side-effects --esign-document-url <sandbox-file-id-or-doc-url> --esignbao-completed-flow-id <completed-flow> --out docs/release/evidence/artifacts/esignbao-live-YYYYMMDD.json`<br>`python3 scripts/sandbox-evidence-runner.py --scope fadada --live --confirm-live-side-effects --esign-document-url <sandbox-doc-id-or-url> --fadada-completed-flow-id <completed-flow> --out docs/release/evidence/artifacts/fadada-live-YYYYMMDD.json`<br>`cd desktop && cargo tauri build --ci --bundles app,dmg --no-sign`<br>`bash scripts/desktop-release-preflight.sh --out docs/release/evidence/artifacts/desktop-release-preflight-YYYYMMDD.json` |
| 退出标准 | 支付和电签至少完成一轮真实 live 采集或明确记录“资源未到、保持 pending”；桌面 preflight 已列出签名/公证缺失输入，不允许空转 |

## 30-42h

| 项目 | 内容 |
|---|---|
| 负责人 | 移动/小程序真机负责人、桌面负责人、发布主控 |
| 本地可完成 | 复跑所有失败项，更新 evidence 文件中的 artifact reference，补 secret scan，补必要的 release notes / runbook 引用；移动/小程序代码级 smoke 已通过，后续只补真实设备/交互式证据 |
| 需用户申请后给密钥/证书 | 若桌面签名仍缺证书，这一窗必须把签名/公证输入补齐；若支付/电签仍缺 sandbox 信息，继续保持 pending，不用替代品 |
| 需真机/交互式验证 | iOS、Android、WeChat DevTools 或真机路径，桌面已签名包安装/启动，支付/电签后台人工确认 callback / retry / 状态流转 |
| 产物 | `mobile-mini-code-smoke` 和手工设备证据、桌面 runtime / installed-profile / signed package 证据、支付/电签的 callback / retry / idempotency 证据 |
| 验证命令 | `bash scripts/mobile-device-smoke.sh --out docs/release/evidence/artifacts/mobile-mini-code-smoke-YYYYMMDD.json --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-YYYYMMDD.json`<br>`bash scripts/desktop-runtime-smoke.sh --with-app-bundle --out docs/release/evidence/artifacts/desktop-runtime-code-smoke-YYYYMMDD.json --ui-log-out docs/release/evidence/artifacts/desktop-runtime-ui-smoke-YYYYMMDD.log`<br>`bash scripts/desktop-installed-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-installed-profile-smoke-YYYYMMDD.json`<br>`bash scripts/desktop-release-profile-smoke.sh --out docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-YYYYMMDD.json`<br>`bash scripts/release-evidence-secret-scan.sh` |
| 退出标准 | iOS / Android / WeChat / 桌面 的真实证据已分别落盘；全设备智能助手相关能力没有假完成描述；所有 evidence 文件只保留真实 artifact reference；任何仍缺的 lane 必须明确写成 blocker |

## 42-48h

| 项目 | 内容 |
|---|---|
| 负责人 | 发布主控 + 最终审批人（用户） |
| 本地可完成 | 最终整理工作树、补提交说明、跑商业门禁和 GitNexus 复验，确认没有新的 secret / unknown / not-ready 漏洞 |
| 需用户申请后给密钥/证书 | 不新增资源；这段只做收口与签字 |
| 需真机/交互式验证 | 只做最后一次人工确认：关键截图、签名包、callback 日志、设备记录、release evidence 状态 |
| 产物 | 最终 gate transcript、clean worktree 证据、所有 evidence 文件 `Status: complete` 或明确保留的阻断说明、发布决策记录 |
| 验证命令 | `python3 scripts/release-worktree-inventory.py --json`<br>`git diff --check`<br>`bash scripts/release-evidence-secret-scan.sh`<br>`node scripts/validate-commercial-delivery-lanes.cjs`<br>`GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus bash scripts/commercial-readiness-gate.sh --quick`<br>`GITNEXUS_BIN=/Users/pengchengkeji/.npm/_npx/ce85571ede75641e/node_modules/.bin/gitnexus bash scripts/commercial-readiness-gate.sh --with-local-tests` |
| 退出标准 | 商业门禁通过，或门禁仍失败但失败原因只剩下明确列出的外部资源缺口；工作树可追踪、证据可追踪、没有假完成 |

## 48 小时结束时的判断

- 能发 Go 的条件：支付、电签、桌面、移动的证据都是真实 artifact，RAG 内建 full50 evidence 保持 complete，所有 release evidence 文件都能被验证为 complete，最终商业门禁通过。
- 不能发 Go 的条件：任一 lane 仍靠 mock/fake 结果，或 evidence 文件仍有 pending/TBD/空 artifact reference，或 `commercial-readiness-gate.sh` 仍失败于真实阻断。
