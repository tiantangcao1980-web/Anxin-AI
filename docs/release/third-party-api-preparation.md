# 第三方 API 接入资料准备清单

> 日期：2026-05-09
> 状态：资料准备中
> 规则：本文只列资料项和验收口径，不保存密钥、证书、私钥、手机号、身份证号、合同原文或后台截图原图。真实 secret 放入 secret manager 或本地未追踪 `.env`。
> 当前顺序：开发先聚焦桌面端本地可执行功能；第三方 API 资料可并行准备。未拿到真实密钥前，代码以本地 mock、沙箱样例、脱敏测试数据和 provider preflight 完成功能级验证，真实密钥只用于最后联调和 release evidence。
> 机器清单：`docs/release/external-resource-requirements.json` 是自动校验来源；本文是给资料准备方阅读的版本。

## 交付方式

| 类型 | 交付方式 | 备注 |
|---|---|---|
| API key / secret / 私钥 | secret manager 或本地 `.env` | 不要发到聊天、文档或 Git |
| 证书 / 公钥 / 私钥文件 | 加密压缩包或 secret manager 文件项 | 文件名可记录，文件内容不入仓 |
| 后台截图 / 回调日志 | 脱敏后放入合规 artifact store | 仓库只记录 artifact 路径 |
| 测试账号 | 只给角色、环境、账号标签 | 密码走单独密钥通道 |
| 商务/资质材料 | 线下归档 | 仓库只记录“已具备/缺失”状态 |

## P0：商业交付阻断项

### 支付：微信支付 + 支付宝

| Provider | 需要准备 | 用途 | 对应配置 |
|---|---|---|---|
| 通用 | 公网 HTTPS callback base URL | 接收支付异步通知 | `PAYMENT_NOTIFY_BASE_URL` |
| 微信支付 | 商户号、AppID、商户证书序列号 | 下单、查单、退款、关单 | `WECHAT_PAY_MCH_ID`、`WECHAT_PAY_APP_ID`、`WECHAT_PAY_MERCHANT_SERIAL_NO` |
| 微信支付 | 商户私钥或私钥文件 | 请求签名 | `WECHAT_PAY_MERCHANT_PRIVATE_KEY` / `WECHAT_PAY_MERCHANT_PRIVATE_KEY_PATH` |
| 微信支付 | 平台证书/公钥序列号、平台公钥 | 回调和同步响应验签 | `WECHAT_PAY_PLATFORM_SERIAL`、`WECHAT_PAY_PLATFORM_PUBLIC_KEY` / `WECHAT_PAY_PLATFORM_PUBLIC_KEY_PATH` |
| 微信支付 | API v3 key | 回调 resource 解密 | `WECHAT_PAY_API_V3_KEY` |
| 微信支付 | 已支付沙箱订单 ID、原订单金额 | 退款 live runner | `--wechat-refund-order-id`、`--refund-total-amount` |
| 支付宝 | AppID、应用私钥、支付宝公钥 | page.pay、query、refund、close、异步通知验签 | `ALIPAY_APP_ID`、`ALIPAY_PRIVATE_KEY` / `ALIPAY_PRIVATE_KEY_PATH`、`ALIPAY_PUBLIC_KEY` / `ALIPAY_PUBLIC_KEY_PATH` |
| 支付宝 | 沙箱或预发网关 | 区分沙箱/生产 | `ALIPAY_GATEWAY_URL` |
| 支付宝 | 待查询、待退款、待关闭沙箱订单 ID | live runner | `--alipay-query-order-id`、`--alipay-refund-order-id`、`--alipay-close-order-id` |

验收证据：成功支付、失败支付、退款、关单、官方异步通知、重复通知幂等、证书/公钥轮换或刷新记录。

### 电签：e签宝 + 法大大

| Provider | 需要准备 | 用途 | 对应配置 |
|---|---|---|---|
| e签宝 | AppID、AppSecret、沙箱/预发 API URL | 创建/启动签署、链接、状态、下载、撤销、回调验签 | `ESIGN_BAO_APP_ID`、`ESIGN_BAO_APP_SECRET`、`ESIGN_BAO_API_URL` |
| 法大大 | AppID、AppSecret、沙箱/预发 API URL | access token、签署任务、链接、状态、下载、取消、FASC 回调验签 | `FADADA_APP_ID`、`FADADA_APP_SECRET`、`FADADA_API_URL` |
| 通用 | 测试合同文件 URL 或文件 ID | live 签署流程输入 | `--esign-document-url` |
| 通用 | 已完成沙箱 flow/task ID | 下载完成签署文件 | `--esignbao-completed-flow-id`、`--fadada-completed-flow-id` |
| 通用 | provider 后台脱敏截图/回调日志 | 证明状态流转和重试 | artifact store 路径 |

验收证据：创建/启动、签署链接、状态查询、撤销/取消、完成文件下载、官方回调、重复回调幂等、失败回调重试。

### 移动 App / 小程序 / uni-app 发布资源

| 平台 | 需要准备 | 用途 | 当前影响 |
|---|---|---|---|
| DCloud / uni-app | DCloud 账号、应用 AppID、云打包权限、证书配置入口 | uni-app App 打包、插件、uniPush/原生能力 | 新 uni-app 基座必须具备 |
| iOS | Apple Developer Team、Bundle ID、证书、Profiles、TestFlight 权限 | iOS 真机/TestFlight 验收 | 商业交付阻断 |
| Android | 应用包名、签名 keystore、渠道包策略、目标应用市场账号 | Android 真机和上架 | 商业交付阻断 |
| 微信小程序 | 小程序 AppID/AppSecret、开发者权限、request/upload/download/socket/web-view 合法域名 | `wx.login -> code2session`、API 调用、文件上传、WebView | 商业交付阻断 |
| 推送 | APNs key/cert、Android 厂商推送或 uniPush 配置 | 审批、任务、签署通知 | P1，但影响真实运营 |
| 测试 | iOS/Android 真机、微信开发者工具、测试账号、staging 后端 URL | 登录、审批、聊天延续、错误态、桌面远控 | release evidence 必需 |

### 桌面签名与分发

| 需要准备 | 用途 | 对应配置 |
|---|---|---|
| macOS signing identity | Tauri `.app` 签名 | `desktop/tauri.conf.json` / Keychain |
| Apple code signing identity | `codesign --verify` | 本机 Keychain |
| Notarization credential | Apple notarization | `NOTARYTOOL_KEYCHAIN_PROFILE` 或 App Store Connect API key |
| 已签名 `.app` / DMG | packaged runtime smoke | `ANXIN_DESKTOP_RELEASE_APP` / release artifact |

## P1：上线体验和运营项

| 类别 | 需要准备 | 对应配置/说明 |
|---|---|---|
| LLM | 默认模型 provider、API key、base URL、模型名、数据处理协议、调用额度 | `LLM_PROVIDER`、`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` |
| Embedding | embedding key、base URL、模型名、维度、额度 | `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL`、`EMBEDDING_MODEL`、`EMBEDDING_DIMENSIONS` |
| 搜索/尽调 | Perplexity/search key、企查查/天眼查/爱企查/信用中国账号、IP 白名单、QPS、合规授权 | `SEARCH_API_KEY`、`QICHACHA_API_KEY`、`TIANYANCHA_API_KEY`、`AIQICHA_API_KEY`、`CREDIT_CHINA_API_KEY` |
| 对象存储 | OSS/S3/MinIO endpoint、bucket、region、access key、CORS、加密/保留策略 | `STORAGE_BACKEND`、`MINIO_*` 或云厂商等价配置 |
| 邮件 | 阿里云 DM 账号、发信域名、发信地址、模板 | `ALIYUN_EMAIL_*` |
| 短信 | 阿里云 Dysmsapi access key、签名、模板 ID | `ALIYUN_SMS_*` |
| CAPTCHA | Cloudflare Turnstile site key / secret key、域名绑定 | `CAPTCHA_PROVIDER=turnstile`、`TURNSTILE_SITE_KEY`、`TURNSTILE_SECRET_KEY` |
| MCP 外部连接 | 允许的 SSE host、stdio 命令/完整命令行/env key allowlist、每个 connector 的业务负责人 | `MCP_SSE_ALLOWED_HOSTS`、`MCP_STDIO_ALLOWED_*` |
| RTC/语音转写 | LiveKit / 阿里云实时语音相关账号 | 仅在启用语音/会议能力时需要 |

## P2：灰度后扩展项

| 类别 | 需要准备 | 说明 |
|---|---|---|
| 多模型供应商 | DeepSeek、OpenAI-compatible、私有 vLLM/Xinference/Ollama endpoint | 需纳入 CapabilityRoute 与 route token gate |
| 企业微信/飞书/钉钉 | OAuth、消息、审批、机器人或小程序应用凭据 | 先做只读/通知，后做高风险动作审批 |
| App Store / 应用市场材料 | 隐私政策、用户协议、软著/资质、ICP备案、截图、审核账号 | 不进代码仓库，只在发布清单中记录状态 |

## 你可以先准备的最小资料包

1. 支付：微信支付商户资料 + 支付宝沙箱应用资料 + callback 公网域名。
2. 电签：e签宝或法大大二选一先给沙箱 AppID/Secret/API URL + 测试合同文件。
3. 小程序：微信小程序 AppID/AppSecret + 合法域名配置权限 + 开发者工具可登录账号。
4. 移动：DCloud 账号/AppID + Apple Developer Team + Android keystore/包名。
5. AI：默认 LLM 和 embedding provider 的 key、base URL、模型名、额度说明。
6. 测试：staging 后端 URL、老板/管理员/普通员工/服务方四类测试账号标签。

## 拿到资料后的本地命令

```bash
python3 scripts/sandbox-evidence-runner.py --scope payment \
  --out docs/release/evidence/artifacts/payment-sandbox-preflight-YYYYMMDD.json

python3 scripts/sandbox-evidence-runner.py --scope esign \
  --out docs/release/evidence/artifacts/esign-sandbox-preflight-YYYYMMDD.json

bash scripts/mobile-device-smoke.sh \
  --out docs/release/evidence/artifacts/mobile-mini-code-smoke-YYYYMMDD.json \
  --manual-template-out docs/release/evidence/artifacts/mobile-device-manual-template-YYYYMMDD.json

bash scripts/uni-mobile-migration-guard.sh

bash scripts/uni-mobile-smoke.sh \
  --out docs/release/evidence/artifacts/uni-mobile-base-smoke-YYYYMMDD.json
```

完成 live 或真机证据后，再运行：

```bash
python3 scripts/validate-release-artifacts.py
bash scripts/release-evidence-secret-scan.sh
bash scripts/commercial-readiness-gate.sh --quick
```
