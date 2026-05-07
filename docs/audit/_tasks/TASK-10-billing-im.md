# 任务 10 — 订阅 + 计费 + 支付 + IM/RTC + 通知收口

> 波次：3 / 工时估：5-6 天（含 webhook 业务回写）/ 负责人：待分配
> 必读前置：../PLAN.md、../00-platform/01-prd-reality-gap.md、../00-platform/03-cross-cutting-gaps.md（缺口 B）

## 1. 范围

### 要碰的文件

- 后端商业化：
  - `backend/src/services/subscription_service.py`
  - `backend/src/services/billing_service.py`
  - `backend/src/services/payment_service.py`（重点 235-247 行）
  - `backend/src/services/refund_service.py`
  - `backend/src/api/routes/billing.py`
  - `backend/src/api/routes/payments.py`（重点 308 / 334 行）
  - **新建** `backend/src/services/webhook_handler.py`（缺口 B 骨架）
  - ✅ 已新建 `webhook_received` 表的 alembic 迁移（`030_webhook_received`）
- 后端 IM / RTC / 通知：
  - `backend/src/services/im_service.py`
  - `backend/src/services/im_hub.py`
  - `backend/src/services/rtc_service.py`
  - `backend/src/services/livekit_transcriber.py`
  - `backend/src/services/meeting_assistant_service.py`
  - `backend/src/services/notification_service.py`
  - `backend/src/api/routes/im.py`
  - `backend/src/api/routes/rtc.py`
  - `backend/src/api/routes/notifications.py`
  - `backend/src/api/routes/meeting_assistant.py`
- 前端：
  - `frontend/src/pages/Pricing.tsx`
  - `frontend/src/pages/MySubscription.tsx`
  - `frontend/src/pages/Messages.tsx`
  - `frontend/src/components/subscription/`
  - `frontend/src/components/im/`
  - `frontend/src/components/rtc/`
  - `frontend/src/components/settings/`
  - `frontend/src/hooks/useIMWebSocket.ts`（重点 71 行）
- 测试：
  - `backend/tests/test_payment_*.py`、`test_subscription_*.py`、`test_billing_*.py`、`test_refund_*.py`、`test_webhook_*.py`、`test_im_*.py`、`test_rtc_*.py`、`test_notification_*.py`
  - `frontend/e2e/pricing.spec.ts`、`subscription.spec.ts`、`im.spec.ts`（如缺则补）

### 明确不要碰的文件

- `backend/src/services/esign_service.py`（属任务 05；电签 webhook 接到本任务的 webhook_handler 时由任务 05 自行接管渠道层）
- `backend/src/services/document_service.py` / `object_storage_service.py`（属任务 06；IM 文件消息真正落盘等待 storage_service）
- `backend/src/services/llm_service.py`、`backend/src/api/routes/llm.py`（属任务 02）
- `backend/src/api/routes/anonymous_chat.py`（属任务 09）
- `backend/src/prompts/`（任何 prompt 改动需用户预审）
- `frontend/src/lib/store.ts` 中 auth 持久化部分（属任务 01）

## 2. 必修 P0（带文件:行号）

- [x] **P0-1a 支付 webhook 通用 HMAC 后业务回写**
  - 现状：`backend/src/api/routes/payments.py` 微信/支付宝通用 webhook 已调用 `payment_webhook_service.py`，可推进订单状态并在订阅订单中更新订阅状态。
  - 文件：`payments.py`、`payment_webhook_service.py`
- [ ] **P0-1b 统一 webhook handler + 官方协议适配**
  - 现状：支付/电签回写已通过 `webhook_handler.py` 统一幂等、业务回写、失败记录与提交边界；`webhook_received` 表、基础幂等、Admin `/admin/webhooks` 查询/手动重试、Prometheus webhook 指标、失败自动重试/backoff、稳定 `PaymentWebhookEvent` / `ESignWebhookEvent`、微信支付 v3/支付宝 RSA2 回调验签、e签宝 provider/官方 HMAC 回调、法大大 FASC provider/webhook 代码级协议已完成，但未覆盖真实渠道沙箱闭环、账号事件映射和灰度证据。
  - 期望：
    - 已完成：新建 `backend/src/services/webhook_handler.py` 统一三段式中的 **幂等查重 → 业务回写 → failed/processed 记录**
    - 已完成：`webhook_received` 表（字段：`id`、`scope`、`idempotency_key`、`payload`、`status`、`processed_at`、`error`、`retry_count`、`last_retry_at`、`next_retry_at`），唯一索引 `(scope, idempotency_key)`，并有 `next_retry_at` 调度索引
    - 已完成：支付/电签路由改调 `handle_verified_webhook(scope=..., payload=..., idempotency_key=...)`
    - 业务回写：触发订单状态机推进（`pending → paid / failed / refunded`），订阅生效，IM/邮件/推送通知
  - 文件：`payments.py`、`esign.py`、`webhook_handler.py`、alembic 迁移
- [ ] **P0-2 微信支付 v3 协议接入（PROJECT_STATUS S5）**
  - 现状：Native 下单、商户单号查询、关闭、退款请求、同步响应验签与回调验签已补；仍缺真实沙箱回归、JSAPI/H5 调起参数与证书/公钥轮换验证。
  - 期望：补 JSAPI / H5 调起参数、沙箱凭据回归和证书/公钥轮换；密钥从环境变量读取；
  - 文件：`backend/src/services/payment_service.py`
- [ ] **P0-3 支付宝 RSA2 协议接入**
  - 现状：PC page.pay 签名 URL、query/refund/close 请求、同步响应验签与异步通知 RSA2 验签已补；仍缺 WAP/APP 与真实沙箱回归。
  - 期望：实现 WAP / APP 调起参数和沙箱回归
  - 文件：`backend/src/services/payment_service.py`
- [x] **P0-4 IM URL token 改为首包 token 鉴权或短期 ticket（PROJECT_STATUS S8）**
  - 2026-05-06 已修：`frontend/src/hooks/useIMWebSocket.ts` 建连 URL 不再携带 token；`backend/src/api/routes/im.py` 要求 10s 内发送 `auth` 首包，成功返回 `auth_ok`。
  - 期望：
    - 前端：建立 WS 不带 query token；连接成功后立即发送首包 `{type:"auth", data:{token}}`
    - 后端：`im` 路由首包鉴权，超时/非 auth/无效 token 均 4001 关闭
  - 文件：`frontend/src/hooks/useIMWebSocket.ts`、`backend/src/api/routes/im.py`、`backend/src/services/im_hub.py`、`backend/tests/test_im_websocket_auth.py`
- [x] **P0-5 退款幂等**
  - 2026-05-06 已修：`refund_service.refund(order_id, idempotency_key)` 同一 key 多次调用结果一致；`refunds.idempotency_key` 唯一索引 + 同 key 进程内锁兜底；`/payments/orders/{id}/refund` 支持 `Idempotency-Key` 头 / body key；`/billing/refunds` 支持申请层 idempotency key；测试覆盖同 key 重放、跨订单复用拒绝、同 key 100 并发只生成 1 笔退款。
  - 文件：`backend/src/services/refund_service.py`、`backend/src/api/routes/payments.py`（退款入口）
- [x] **P0-6 订阅状态机覆盖**
  - 2026-05-06 已修：`SubscriptionService` 新增 `pending/trial/active/past_due/cancelled/expired` 显式转换矩阵；创建付费订阅先落 `pending`，支付成功激活或续费，退款回调转 `expired` 并关闭续费；非法终态取消返回真实 HTTP 409；状态变更写入 `subscription_events` 审计表。
  - 证据：`backend/tests/test_subscription_state_machine.py` 覆盖创建待支付、试用转付费、续费幂等、退款过期和非法取消 409。
  - 文件：`backend/src/services/subscription_service.py`、`backend/src/services/payment_webhook_service.py`、`backend/src/api/routes/billing.py`、`backend/src/models/billing.py`、`backend/alembic/versions/034_add_subscription_events.py`
- [x] **P0-7 V2 双客户端独立计费**
  - 2026-05-06 已修：`SubscriptionService.create_subscription(..., client_type=...)` 在服务层直接写入 `needer/provider` 维度并校验套餐 `client_type`，不再由 V2 路由创建后补写；同一用户的需求方和服务方订阅可并存，provider 端支付/退款只影响 provider 订阅和事件日志。
  - 前端已接入：`MySubscription` 将订阅列表按 `needer/provider` 双栏展示，不再只取第一条订阅；空端侧展示独立未订阅状态，订单/退款响应也通过归一化函数兼容现有后端结构。`Pricing` 会按当前端侧过滤 `client_type` / `both` 套餐，避免展示后端会拒绝的跨端套餐。
  - 证据：`test_dual_client_subscriptions_are_isolated`、`test_create_subscription_rejects_wrong_client_plan`、`frontend/src/pages/MySubscription.test.ts`、`frontend/src/pages/Pricing.test.ts`。
  - 文件：`backend/src/services/subscription_service.py`、`backend/src/api/routes/billing.py`、`backend/tests/test_subscription_state_machine.py`、`frontend/src/pages/MySubscription.tsx`、`frontend/src/pages/MySubscription.test.ts`、`frontend/src/pages/Pricing.tsx`、`frontend/src/pages/Pricing.test.ts`
- [x] **P0-8 IM 离线消息可达**
  - 2026-05-06 已修：`im_messages.sequence` 提供 conversation 内递增游标；WebSocket `auth.data.last_ack_message_id` 认证后返回 `offline_messages`；客户端可发 `{type:"ack", message_id}` 推进 `IMParticipant.last_read_at`、`unread_count` 与消息 `read_by`。
  - 前端已接入：`useIMWebSocket` 认证首包会按用户携带本地 ACK 游标；收到实时 `message` / `offline_messages` 后自动发送 `ack`；收到服务端 `ack_ok` 后才持久化用户维度游标。
  - 证据：`test_im_offline_messages_after_ack_and_ack_updates_read_state`、`test_im_ack_rejects_non_participant_message`、`test_im_websocket_sends_offline_messages_after_auth`、`frontend/src/hooks/useIMWebSocket.test.ts`。
  - 文件：`backend/src/services/im_service.py`、`backend/src/api/routes/im.py`、`backend/src/models/im.py`、`backend/alembic/versions/035_add_im_message_sequence.py`、`backend/tests/test_im_offline_messages.py`、`backend/tests/test_im_websocket_auth.py`、`frontend/src/hooks/useIMWebSocket.ts`、`frontend/src/hooks/useIMWebSocket.test.ts`

## 3. 流程

### Step 0 — PRD vs 现实差分
读 `../00-platform/01-prd-reality-gap.md` 中 S5（webhook）/ S8（IM token），以及 `../00-platform/03-cross-cutting-gaps.md` 缺口 B；写 `docs/audit/10-billing-im/00-prd-reality-gap.md`。

### Step 1 — hierarchical-memory find-bugfix / find-feature
关键词：`webhook idempotent business writeback`、`wechatpay v3 sdk`、`alipay rsa2 verify`、`websocket auth first frame ticket`、`refund idempotency`、`subscription state machine`、`im offline queue ack`。命中即复用。

### Step 2 — 分层读取（路由 → 服务 → 前端 → 测试）
1. `payments.py` + `payment_service.py` + `refund_service.py`
2. `webhook_idempotency_service.py` + `webhook_handler.py` + `webhook_events.py` + `webhook_received` 表迁移 + Admin webhook 查询/手动重试 + Prometheus 指标 + 自动重试/backoff 已完成；e签宝 provider/官方 HMAC 回调与法大大 FASC provider/webhook 代码级协议已完成；真实商户沙箱、账号事件映射与灰度证据待补
3. `subscription_service.py` + `billing_service.py` + `MySubscription.tsx` + `Pricing.tsx`
4. `im_service.py` + `im_hub.py` + `im.py` + `useIMWebSocket.ts` + `Messages.tsx`
5. `rtc_service.py` + `livekit_transcriber.py` + `meeting_assistant_service.py` + `rtc.py`
6. `notification_service.py` + `notifications.py`
7. 测试：`test_payment_*`、`test_webhook_*`、`test_subscription_*`、`test_refund_*`、`test_im_*`

### Step 3 — code-review + security-review
关注：webhook 重放防护（idempotency_key + 签名时间戳 ≤5min）、退款并发安全、订阅金额计算精度（Decimal 而非 float）、WS 鉴权时序窗口、IM 离线消息存储 PII 边界、RTC token 短期化。

### Step 4 — 先写失败测试再改实现
- P0-1：`test_webhook_handler_idempotent`、`test_payment_webhook_writes_back_order`、`test_subscription_activated_on_payment_success`
- P0-2：`test_wechatpay_v3_create_order`、`test_wechatpay_v3_verify_callback`、`test_wechatpay_v3_refund`
- P0-3：`test_alipay_rsa2_create_order`、`test_alipay_rsa2_verify_async_notify`
- P0-4：`test_im_ws_rejects_url_token`、`test_im_ws_first_frame_auth_timeout`、`test_im_ticket_short_lived`
- P0-5：`test_payment_refund_idempotency_key_returns_existing_result`、`test_payment_refund_rejects_reused_idempotency_key_for_other_order`、`test_billing_refund_request_idempotency_key_reuses_pending_refund`、`test_refund_idempotency_key_concurrent_requests_create_one_refund`
- P0-6：`test_create_subscription_starts_pending_and_records_event`、`test_trial_to_paid_records_activation_event`、`test_active_subscription_renewal_extends_period_once`、`test_refund_payment_webhook_expires_subscription`、`test_invalid_subscription_transition_returns_409`
- P0-7：`test_dual_client_subscriptions_are_isolated`、`test_create_subscription_rejects_wrong_client_plan`
- P0-7 前端：`MySubscription.test.ts` 覆盖需求方/服务方订阅归一化、未知 client type 兜底、订单/退款响应变体；`Pricing.test.ts` 覆盖套餐 `client_type` 归一化、价格字段兼容、feature 对象归一化和当前端侧过滤。
- P0-8：`test_im_offline_messages_after_ack_and_ack_updates_read_state`、`test_im_ack_rejects_non_participant_message`、`test_im_websocket_sends_offline_messages_after_auth`
- P0-8 前端：`useIMWebSocket.test.ts` 覆盖用户维度 ACK 游标、认证首包 `last_ack_message_id`、离线消息入 store 与逐条 ACK、`ack_ok` 后持久化游标。

### Step 5 — verification-loop
- `cd backend && pytest -k "payment or webhook or subscription or refund or im or notification or rtc"`
- `cd backend && pytest`（不退化当前默认 `430 passed, 1 skipped` 基线）
- `cd frontend && npm test && npm run lint && npm run build`
- `cd frontend && npx playwright test e2e/pricing.spec.ts e2e/subscription.spec.ts e2e/im.spec.ts`
- 沙箱回归：支付宝沙箱 + 微信沙箱各跑 7 天，零异常截图入 PR 描述

### Step 6 — simplify + 沉淀到 hierarchical-memory
- `add-feature --name "统一 webhook handler 三段式" --pattern "签名→解析→业务回写 + idempotency 表" --files ...`
- `add-feature --name "微信支付 v3 接入" --pattern "JSAPI/Native/H5 + 回调验签" --files ...`
- `add-feature --name "支付宝 RSA2 接入" --pattern "PC/WAP/APP + 异步通知" --files ...`
- `add-bugfix --symptom "WS URL 携 token 泄漏到日志" --fix "首包鉴权或短期 ticket" --files ...`
- `add-feature --name "退款幂等" --pattern "DB 唯一索引 + idempotency_key" --files ...`

## 4. 输出物（写到 `docs/audit/10-billing-im/`）
- `00-prd-reality-gap.md`
- `01-prd-coverage.md`
- `02-issues.md`（P0/P1/P2 合并清单）
- `03-fixes.md`（含 webhook 灰度方案）
- `04-test-additions.md`（含沙箱 7 天回归报告）
- `05-followups.md`
- 代码 PR（按渠道拆分多 PR：webhook 骨架 → 微信 → 支付宝 → IM token → 离线消息）

## 5. 风险护栏（必须遵守）
- **商业化任何代码改动 PR 提交前必须用户预审**（payment / billing / subscription / refund 全覆盖）
- webhook 切官方协议必须给灰度方案：**沙箱 7 天 → 1% → 10% → 50% → 100%**
- 渠道顺序建议：**支付宝沙箱 → 微信沙箱 → 灰度生产**；同一 PR 不混渠道
- **不允许 big-bang 切换**；旧 mock 路径在灰度期间保留为 fallback
- 退款幂等要在沙箱跑至少 7 天再上灰度
- IM URL token 切换需考虑老客户端兼容（首包鉴权 + URL token 双轨灰度 1-2 周后再下线 URL）
- 不动 `prompts/` 任意文件
- 不动 `.env` / 不轮换密钥（属任务 0）；新增微信/支付宝凭据走任务 0 SOP 注入
- 不允许 force push、不动已发布 commit
- 数据库迁移（webhook_received 表）必须给回滚脚本

## 6. 完成标准（DoD）
- [ ] 全部 8 个 P0 修复，每个有"失败 test → 通过 test"证据
- [ ] `webhook_idempotency_service.py` + `webhook_handler.py` + `webhook_events.py` + `webhook_received` 表 + alembic up/down 迁移 + Admin webhook 查询/手动重试 + Prometheus 指标 + 自动重试/backoff 已齐；支付官方验签、e签宝 provider/回调 HMAC、法大大 FASC provider/webhook 代码级协议已齐；真实商户沙箱、账号事件映射与灰度证据待补
- [ ] 微信 / 支付宝沙箱回归报告（各 ≥7 天，零异常）入 PR 描述
- [ ] 灰度方案（1% → 10% → 50% → 100%）写入 `03-fixes.md`
- [ ] 后端 `pytest` 不退化（当前默认 `430 passed, 1 skipped` 基线）
- [ ] 前端 `npm test` + `npm run lint` + `npm run build` 不退化；关键 Playwright 待按发布候选复跑
- [ ] 6 份文档（`00..05.md`）齐全
- [ ] 沉淀到 hierarchical-memory 至少 4 条（建议 P0-1 + P0-2 + P0-3 + P0-4）
- [ ] 回写 `../00-platform/01-prd-reality-gap.md` 中 S5 / S8 状态
- [ ] PR 描述含每个渠道的回滚预案（如何回退到 mock / 老路径）
