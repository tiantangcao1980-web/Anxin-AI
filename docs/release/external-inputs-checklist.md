# 商业发布外部输入清单

> 日期：2026-05-09
> 状态：等待外部输入。本文只列输入名称和交付口径，不保存密钥、账号密码、手机号、身份证号或合同原文。
> 责任边界：开发侧先用本地 mock、沙箱样例和脱敏测试数据完成代码级闭环；真实 API key、证书、签名身份、真机和后台账号由业务侧准备后再填入 secret manager / 本地未追踪 `.env` 做联调。

## 使用方式

- 外部输入只进入 secret manager、本地 `.env`、测试设备或合规 artifact store，不直接写入仓库。
- 拿到输入后，先按 `docs/release/evidence-collection-runbook.md` 跑对应 preflight/live 命令。
- 操作性交接单见 `docs/release/external-resource-handoff.md`；它列出每条线拿到输入后的命令和完成证据。
- 面向用户准备资料的完整第三方 API 清单见 `docs/release/third-party-api-preparation.md`。
- evidence 文件转 `Status: complete` 前，必须通过 `scripts/validate-release-evidence.py` 和 `scripts/release-evidence-secret-scan.sh`。

## 支付线

| 输入 | 用途 | 对应字段或 artifact | 当前状态 |
|---|---|---|---|
| 公网 callback base URL | 接收微信/支付宝异步通知 | `PAYMENT_NOTIFY_BASE_URL` | 缺 |
| 微信支付 app ID | 微信支付下单/回调 | `WECHAT_PAY_APP_ID` | 缺 |
| 微信支付商户号 | 微信支付下单/查单/退款 | `WECHAT_PAY_MCH_ID` | 缺 |
| 微信支付商户证书序列号 | 请求签名与平台验签 | `WECHAT_PAY_MERCHANT_SERIAL_NO` | 缺 |
| 微信支付商户私钥或私钥文件路径 | 请求签名 | `WECHAT_PAY_MERCHANT_PRIVATE_KEY` 或 `WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH` | 缺 |
| 微信支付平台证书/公钥序列号 | 回调/同步响应验签 | `WECHAT_PAY_PLATFORM_SERIAL` | 缺 |
| 微信支付平台公钥或公钥文件路径 | 回调/同步响应验签 | `WECHAT_PAY_PLATFORM_PUBLIC_KEY` 或 `WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH` | 缺 |
| 微信支付 API v3 key | 回调 resource 解密 | `WECHAT_PAY_API_V3_KEY` | 缺 |
| 微信支付官方 webhook 开关 | 启用官方验签路径 | `WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED=true` | 缺 |
| 支付宝 app ID | 支付宝 page.pay/query/refund/close | `ALIPAY_APP_ID` | 缺 |
| 支付宝应用私钥或文件路径 | 请求签名 | `ALIPAY_PRIVATE_KEY` 或 `ALIPAY_PRIVATE_KEY_PATH` | 缺 |
| 支付宝公钥或文件路径 | 同步响应/异步通知验签 | `ALIPAY_PUBLIC_KEY` 或 `ALIPAY_PUBLIC_KEY_PATH` | 缺 |
| 支付宝网关 | 沙箱或预发网关 | `ALIPAY_GATEWAY_URL` | 待确认 |
| 支付宝官方 webhook 开关 | 启用 RSA2 通知验签 | `ALIPAY_OFFICIAL_WEBHOOK_ENABLED=true` | 缺 |
| 渠道后台脱敏截图/日志 | 证明订单、退款、关闭、异步通知、失败重试、证书轮换 | `docs/release/evidence/artifacts/*payment*.json` 或截图索引 | 缺 |
| 已支付/待关闭沙箱订单 ID | live runner 查单、退款、关单运行时前置物；缺少时对应 live 步骤会 skipped | `--wechat-refund-order-id`、`--alipay-query-order-id`、`--alipay-refund-order-id`、`--alipay-close-order-id` | 缺 |
| 微信已支付订单原始金额 | 微信退款接口需要原订单总额；缺少时退款 live 不能形成完整证据 | `--refund-total-amount` | 缺 |

## 电签线

| 输入 | 用途 | 对应字段或 artifact | 当前状态 |
|---|---|---|---|
| e签宝 app ID | 创建/启动签署流程 | `ESIGN_BAO_APP_ID` | 缺 |
| e签宝 app secret | 请求签名与官方回调验签 | `ESIGN_BAO_APP_SECRET` | 缺 |
| e签宝 API URL | 沙箱或预发 API | `ESIGN_BAO_API_URL` | 待确认 |
| 法大大 app ID | access token、签署任务 | `FADADA_APP_ID` | 缺 |
| 法大大 app secret | access token、FASC 回调验签 | `FADADA_APP_SECRET` | 缺 |
| 法大大 API URL | 沙箱或预发 API | `FADADA_API_URL` | 待确认 |
| 电签官方 webhook 开关 | 启用官方回调验签路径 | `ESIGN_OFFICIAL_WEBHOOK_ENABLED=true` | 缺 |
| 沙箱测试合同文件或文件 ID | live 签署流程输入 | `--esign-document-url` | 缺 |
| provider 后台脱敏截图/日志 | 证明创建、启动、链接、状态、下载、撤销、回调、重试 | `docs/release/evidence/artifacts/*esign*.json` 或截图索引 | 缺 |
| 已完成沙箱签署 flow ID | live runner 下载完成签署文档运行时前置物；缺少时下载步骤会 skipped | `--esignbao-completed-flow-id`、`--fadada-completed-flow-id` | 缺 |

## 桌面发布线

| 输入 | 用途 | 对应字段或 artifact | 当前状态 |
|---|---|---|---|
| Tauri macOS signing identity | release `.app` 签名 | `desktop/tauri.conf.json` / `bundle.macOS.signingIdentity` | 缺 |
| Production APNs entitlement | macOS release push entitlement | `desktop/Entitlements.plist` / `com.apple.developer.aps-environment=production` | 已配置 |
| Apple code signing identity | `codesign --verify` | 本机 keychain identity | 缺 |
| Notarization credential | Apple notarization | `NOTARYTOOL_KEYCHAIN_PROFILE` 或 Apple ID / App Store Connect API key flow | 缺 |
| release `.app` | signed packaged runtime smoke | `ANXIN_DESKTOP_RELEASE_APP` | unsigned artifact 已有；signed 缺 |
| release DMG | 用户安装包证据 | release artifact path | unsigned artifact 已有；signed/notarized 缺 |
| packaged profile migration transcript | 证明 plaintext-to-SQLCipher migration in package | `docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` | unsigned 支撑证据已完成；signed/notarized 缺 |
| packaged runtime performance transcript | 证明 100 push / 500 pull 性能 | `docs/release/evidence/artifacts/desktop-release-profile-unsigned-smoke-20260508.json` | unsigned 支撑证据已完成；signed/notarized 缺 |
| 跨端连续会话证据 | desktop/web/mobile 不丢/不重同步 | screenshot/log artifact | 缺 |

## RAG Full50 线

| 输入 | 用途 | 对应字段或 artifact | 当前状态 |
|---|---|---|---|
| 内建 full50 golden | 50 条内建法律问题，不含 `smoke: true` | `eval/legal_full50_golden.jsonl` | 已完成 |
| 内建法律语料导出 | 覆盖每个 `relevant_chunk_id` | `eval/legal_full50_corpus.jsonl` | 已完成 |
| law_ref/source_url metadata | 召回和引用健康检查 | corpus metadata | 已完成 |
| Qdrant collection | live baseline | `rag_eval_full50_builtin_20260507` | 已完成 |
| predictions artifact | 召回结果 | `docs/release/evidence/artifacts/rag-full50-built-in-predictions-20260507.json` | 已完成 |
| metrics artifact | recall@10、MRR、NDCG@10 | `docs/release/evidence/artifacts/rag-full50-built-in-metrics-20260507.json` | 已完成 |
| 权限/PII/引用回链截图或日志 | 证明 RAG 安全边界 | release artifact store | 已完成；外部客户知识库评测另列上线后扩展 |

## 移动/小程序线

| 输入 | 用途 | 对应字段或 artifact | 当前状态 |
|---|---|---|---|
| iOS 测试构建 | 真机、TestFlight 或 iOS Simulator app-run smoke | build hash + device transcript | 缺正式/真机证据；legacy Expo Go iOS Simulator 支持性 app-run 已有，uni-app signed/TestFlight 仍缺 |
| Android 测试构建 | 真机 smoke | build hash + device transcript | 缺；ADB 可启动但当前无连接设备，`emulator` CLI 不在 PATH |
| 微信开发者工具或真机环境 | 小程序 smoke | DevTools/project transcript | 本机 WeChat DevTools CLI project smoke 已通过；交互式/真机证据仍缺 |
| DCloud/uni-app 账号与应用 AppID | 新移动/小程序统一基座、云打包、插件和 uniPush 准备 | DCloud app id / cloud build transcript | 缺外部账号与云打包证据；`apps/uni-mobile` 本地基座已可 typecheck/test/build H5/微信小程序，旧 Expo/Taro 仅作 legacy 参考 |
| iOS/Android 包名与证书策略 | uni-app App 打包和上架 | Bundle ID / package name / signing profile label | 缺 |
| 测试账号 | 登录、审批、消息、任务、聊天延续 | redacted tester/account role | 缺 |
| 后端 staging 环境 | 真机 API 指向 | environment URL label only | 缺 |
| 截图/视频/日志索引 | 证明登录、审批、消息/任务详情、错误态、跨设备连续会话 | `docs/release/evidence/artifacts/*mobile*` 或合规 artifact store | 缺 |
| 移动 npm audit 处置 | Expo CLI/Metro production audit findings | 已通过定向 overrides 清零，后续 SDK/package 变更需复跑 audit 与 Expo doctor | 已完成 |

## 汇总放行输入

| 输入 | 用途 | 当前状态 |
|---|---|---|
| 已整理提交的 release 分支 | GitNexus commit-scoped 复验 | 缺 |
| 重跑后的 GitNexus metadata | 知识图覆盖最终提交 | 本地 direct CLI 复验路径已可用；最终 release 前必须复跑，并确保 `lastCommit` 等于当前 `HEAD`，否则 commercial quick gate 会阻断 |
| `scripts/commercial-readiness-gate.sh --quick` PASS transcript | 商业 Go 证据 | 缺 |
| `scripts/commercial-readiness-gate.sh --with-local-tests` PASS transcript | 代码级 + 商业证据双闭环 | 缺 |
