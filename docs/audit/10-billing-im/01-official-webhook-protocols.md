# 官方支付/电签回调协议核查记录

> 日期：2026-05-06
> 目标：记录支付/电签官方回调协议的代码级落地边界，避免把通用 HMAC 底座误认为真实渠道闭环。

## 1. 官方资料来源

- 微信支付商户文档《支付成功回调通知_JSAPI支付》：https://pay.wechatpay.cn/doc/v3/merchant/4012791861。回调请求头包含 `Wechatpay-Serial`、`Wechatpay-Signature`、`Wechatpay-Timestamp`、`Wechatpay-Nonce`；验签后需在 5 秒内应答，回调资源为 `AEAD_AES_256_GCM` 加密资源；未成功应答会按微信支付重试策略重复通知。
- 微信支付商户文档《总述-APIv3如何签名和验签》：https://pay.wechatpay.cn/doc/v3/merchant/4012365342。微信支付 APIv3 的请求应答场景和回调场景均需要验签。
- 微信支付商户文档《下载平台证书》：https://pay.wechatpay.cn/doc/v3/merchant/4012551764。平台证书需定期更新，接口返回加密证书供验签使用。
- 支付宝开放平台文档《Verifying the Signature》：https://developer.alibaba.com/docs/doc.htm?articleId=104613&docType=1&treeId=140。支付宝 JSON 响应验签需要提取响应 JSON 对象内容并使用支付宝公钥校验顶层 `sign`。
- 支付宝 Global 开发者帮助《What is asynchronous notification?》：https://global.alipay.com/developer/helpcenter/detail?_route=sg&categoryId=67617&knowId=201602452303&sceneCode=AC_DEV。异步通知处理完成后必须输出 `success`；验签需要使用支付宝返回的所有参数，但排除 `sign` 和 `sign_type`；同一异步通知重试时 `notify_id` 不变。
- e签宝开放平台《存证服务回调通知接收说明》：https://open.esign.cn/doc/opendoc/evidence_3/nqtb4mtv4g9xpemg/。回调签名按 `HmacSHA256(timestamp + appendParams(queryParams) + body, secret)` 校验，回调头包含 `X-Tsign-Open-SIGNATURE-ALGORITHM: hmac-sha256` 等签名信息；具体 Action 事件仍需按当前应用订阅事件映射。
- 法大大 FASC OpenAPI V5.1 资料需要以商户后台/官方文档为准；本轮代码级实现参考公开 FASC SDK/source：签名使用排序参数、`timestamp` 派生 HMAC key、`bizContent` 和 `X-FASC-*` 头，端点覆盖 `/service/get-access-token`、`/sign-task/create`、`/sign-task/actor/get-url`、`/sign-task/app/get-detail`、`/sign-task/owner/get-download-url`、`/sign-task/cancel`。生产前仍需商户后台确认账号版本、事件名和路径。

## 2. 已落代码

- `backend/src/services/official_webhook_security.py`
  - 微信支付 v3：`Wechatpay-*` 头 RSA-SHA256 验签、平台公钥/公钥路径读取、序列号校验、时间戳新鲜度校验。
  - 微信支付 v3：`AEAD_AES_256_GCM` resource 解密，使用 `WECHAT_PAY_API_V3_KEY`。
  - 支付宝：同步 JSON 响应提取业务响应对象并校验顶层 `sign`。
  - 支付宝：异步通知 RSA2 验签，构造待验签串时排除 `sign` / `sign_type`。
  - e签宝：`X-Tsign-Open-*` 头 HMAC-SHA256 验签，按 `timestamp + 排序后的 query 参数值 + body` 构造签名内容，校验 app id、时间戳新鲜度与十六进制/base64 签名。
  - 法大大：FASC 表单 webhook 验签，校验 `X-FASC-App-Id`、`X-FASC-Sign-Type`、`X-FASC-Sign`、`X-FASC-Timestamp`、`X-FASC-Nonce`、`X-FASC-Event`，解析 `bizContent` 后再进入业务回写。
- `backend/src/api/routes/payments.py`
  - `WECHAT_PAY_OFFICIAL_WEBHOOK_ENABLED=true` 时启用微信官方验签/解密路径。
  - `ALIPAY_OFFICIAL_WEBHOOK_ENABLED=true` 时启用支付宝 RSA2 验签路径。
  - 未开启官方路径时保留通用 HMAC 回归路径，避免当前测试和开发联调断裂。
- `backend/src/api/routes/esign.py`
  - `ESIGN_OFFICIAL_WEBHOOK_ENABLED=true` 时启用 e签宝官方 HMAC 回调验签路径；检测到 `X-FASC-App-Id` 时切入法大大 FASC 回调验签路径。
  - 未开启官方路径时保留 `ESIGN_WEBHOOK_SECRET` 通用 HMAC 回归路径。
- `backend/src/services/esign_service.py`
  - e签宝：创建/启动签署流程、签署链接、状态查询、下载、撤销，所有请求使用 `X-Tsign-Open-*` 签名头与 `Content-MD5`。
  - 法大大：access token、签署任务创建、actor 签署链接、状态详情、下载 URL、取消，所有请求使用 FASC V5.1 签名 form 协议。
- `backend/src/services/payment_service.py`
  - 微信支付 v3：Native 下单、商户订单号查询、关闭订单、退款申请请求签名与调用；非空同步响应会先校验 `Wechatpay-*` RSA-SHA256 签名再解析。
  - 支付宝：`alipay.trade.page.pay` 签名支付 URL、`alipay.trade.query`、`alipay.trade.refund`、`alipay.trade.close` 请求签名与调用；query/refund/close 同步响应会校验顶层 `sign` 后再解析。
  - 支付订单号对接：渠道侧使用 32 位 UUID hex，回调回写可映射回本地 UUID 主键。
- `backend/src/services/webhook_events.py`
  - 支付：`PaymentWebhookEvent` 稳定承载 provider、order_id、状态、provider_status、transaction_id、event_id、event_type。
  - 电签：`ESignWebhookEvent` 稳定承载 contract_id / flow_id、目标合同状态、provider_status、签署日期、event_id、event_type。
- `.env.example` / `backend/.env.example`
  - 已补微信平台公钥、公钥路径、平台序列号、API v3 key、支付宝公钥、e签宝 app/api/path、法大大 app/api/path/access token 与 `ESIGN_OFFICIAL_WEBHOOK_ENABLED` 配置项。

## 3. 已跑验证

```bash
cd backend && ./.venv/bin/pytest -q tests/test_official_webhook_security.py tests/test_external_surface_guards.py -k 'webhook or metrics'
# 17 passed, 9 deselected

cd backend && ./.venv/bin/pytest -q tests/test_refund_idempotency.py tests/test_payment_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py -k 'refund or payment or webhook or metrics or provider or event or esignbao'
# 36 passed, 8 deselected

cd backend && ./.venv/bin/pytest -q tests/test_subscription_state_machine.py tests/test_refund_idempotency.py tests/test_payment_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py tests/test_mode_subscription_guards.py tests/test_im_offline_messages.py tests/test_im_websocket_auth.py -k 'subscription or refund or payment or webhook or metrics or provider or event or esignbao or mode or im or websocket'
# 58 passed, 6 deselected in 11.79s

cd backend && ./.venv/bin/pytest -q tests/test_official_webhook_security.py -k 'esignbao_official'
# 1 passed, 3 deselected

cd backend && ./.venv/bin/pytest -q tests/test_webhook_business_events.py
# 5 passed

cd backend && ./.venv/bin/pytest -q tests/test_payment_provider_clients.py tests/test_official_webhook_security.py -k 'payment or webhook or response or provider'
# 8 passed

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_external_surface_guards.py -k 'esign or fadada'
# 9 passed, 20 deselected, 6 warnings

cd backend && ./.venv/bin/pytest -q tests/test_esign_provider_clients.py tests/test_official_webhook_security.py tests/test_webhook_business_events.py tests/test_external_surface_guards.py tests/test_contract_state_machine.py tests/test_contract_review_workflow.py -k 'esign or webhook or contract or provider'
# 56 passed, 8 deselected, 6 warnings

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/payment_service.py src/services/refund_service.py src/api/routes/payments.py src/services/webhook_events.py src/services/payment_webhook_service.py src/services/esign_webhook_service.py src/core/config.py src/services/official_webhook_security.py tests/test_payment_provider_clients.py tests/test_official_webhook_security.py tests/test_external_surface_guards.py tests/test_webhook_business_events.py
# All checks passed

cd backend && ./.venv/bin/ruff check --select F401,I001,UP041 src/services/esign_service.py src/api/routes/esign.py src/services/esign_webhook_service.py src/services/official_webhook_security.py src/core/config.py src/models/audit.py tests/test_esign_provider_clients.py tests/test_external_surface_guards.py
# All checks passed

cd backend && ./.venv/bin/pytest -q
# 430 passed, 1 skipped, 10 warnings in 46.41s

cd frontend && npm test
# 16 passed

cd frontend && npm run lint && npm run build
# exit 0; build 仅保留既有 lottie eval / chunk size / api.ts dynamic+static import warning
```

## 4. 仍阻断商业交付

- 没有真实商户沙箱凭据，无法完成官方沙箱回归、证书/公钥轮换、公钥序列号轮换和支付平台重试策略验证。
- 微信支付当前实现 Native 扫码支付；JSAPI/H5/小程序调起参数还未补。
- 支付宝当前实现 PC page.pay；WAP/APP 调起参数还未补。
- e签宝 provider 与官方回调 HMAC 验签已按公开文档落地；仍缺当前账号订阅事件映射、沙箱回归和灰度证据。
- 法大大 provider 与 FASC webhook 验签已按公开 SDK/source 落地；仍缺当前商户后台文档确认、账号事件映射、沙箱回归和灰度证据。
- 统一 `webhook_handler.py`、稳定 `PaymentWebhookEvent` / `ESignWebhookEvent` 与官方通知 id 幂等已落；真实渠道沙箱和证书/事件轮换仍未收口。
