# 03 · 云服务对外契约（Auth / Sync / IM）

> 日期：2026-05-22
> 来源：[产品蓝图 §4](../plans/2026-05-22-product-blueprint.md)
> 适用范围：桌面 / 移动 / 小程序 / UniApp / Web 各端调用云端 API 时的统一契约
> 优先级：⭐⭐⭐ 平台合同级

---

## 总览

云端 FastAPI 服务收口为 **3 个核心域 + N 个业务域**。客户端只通过本文件定义的契约访问；业务域 API 走每个域的 README。

```
┌───────────────────────────────────────────────────────────┐
│  桌面 · 移动 · 小程序 · UniApp · Web 后台                  │
└─────┬──────────┬──────────┬──────────────────────────────┘
      │          │          │
      ▼          ▼          ▼
   ☁ Auth   ☁ User-Sync  ☁ IM      ←—— 3 个核心云服务
      │          │          │
      └──────────┴──────────┴──── 业务域（personas / RAG / contracts / ...）
                                  通过 Auth 鉴权后调用
```

---

## 1. Auth Service

**前缀**：`/api/v1/auth`  
**SLA**：可用性 ≥ 99.9%，p99 < 200ms  
**鉴权**：除 `register/login/refresh` 外的端点需要 `Authorization: Bearer <access_token>`

### 1.1 端点清单

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| POST | `/auth/register` | 注册（手机/邮箱 + 验证码 + 可选邀请码） | ✅ |
| POST | `/auth/login` | 登录（密码 / 验证码 / 二维码） | ✅ |
| POST | `/auth/logout` | 注销当前 token | ✅ |
| POST | `/auth/refresh` | 用 refresh_token 换新 access_token | ✅ |
| POST | `/auth/revoke` | 撤销 refresh_token（单设备登出） | ✅ |
| GET | `/auth/me` | 当前用户信息 | ✅ |
| PUT | `/auth/me` | 更新当前用户信息 | ✅ |
| POST | `/auth/verify-email` | 邮箱验证 | ✅ |
| POST | `/auth/resend-verification` | 重发验证码 | ✅ |
| POST | `/auth/forgot-password` | 发送密码重置链接 | ✅ |
| POST | `/auth/reset-password` | 重置密码 | ✅ |
| PUT | `/auth/change-password` | 修改密码（需旧密码） | ✅ |
| GET | `/auth/features` | 当前用户可用 feature flags | ✅ |
| GET | `/auth/oauth/wechat/url` | 获取微信扫码 URL | ✅ |
| POST | `/auth/oauth/wechat/callback` | 微信回调 | ✅ |
| POST | `/auth/wechat/code2session` | 微信小程序 code2session | ✅ |
| GET | `/auth/oauth/alipay/url` | 支付宝扫码 URL | ✅ |
| POST | `/auth/oauth/alipay/callback` | 支付宝回调 | ✅ |
| GET | `/auth/sessions` | 多设备会话列表 | 🚧 |
| DELETE | `/auth/sessions/{id}` | 远程撤销某设备会话 | 🚧 |
| POST | `/auth/mfa/setup` | 启用 TOTP / 短信 MFA | 🚧 |
| POST | `/auth/mfa/verify` | 校验 MFA 验证码 | 🚧 |

### 1.2 关键 schema

**TokenResponse**（登录返回）：

```json
{
  "access_token": "eyJ...",
  "refresh_token": "rt_...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "u_xxx",
    "primary_client": "demand" | "provider",
    "email": "...",
    "phone": "...",
    "subscription_tier": "free" | "pro" | "enterprise"
  }
}
```

### 1.3 错误码

| HTTP | code | 含义 |
|---|---|---|
| 400 | `INVALID_PARAMS` | 参数校验失败 |
| 401 | `INVALID_CREDENTIALS` | 密码/验证码错误 |
| 401 | `TOKEN_EXPIRED` | access_token 过期 |
| 403 | `MFA_REQUIRED` | 需要 MFA 二次验证 |
| 409 | `EMAIL_TAKEN` / `PHONE_TAKEN` | 已注册 |
| 429 | `RATE_LIMITED` | 触发限流 |

### 1.4 配对/远控相关（在 IM 域定义）

`/im-pairing/*` 不在 auth 域，见第 3 节 IM Service。

---

## 2. User-Sync Service

**前缀**：`/api/v1/sync`  
**SLA**：可用性 ≥ 99.5%，桌面 SQLCipher 本地优先；云端可降级  
**鉴权**：必须

### 2.1 端点清单

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| POST | `/sync/push` | 推送本地变更到云端（增量 + lamport_clock） | 🚧（桌面 fail-closed） |
| GET | `/sync/pull` | 拉取云端增量更新 | 🚧 |
| GET | `/sync/status` | 同步状态（最后时间 / 待推送 / 待拉取 / 冲突数） | ✅ |
| POST | `/sync/resolve` | 解决同步冲突 | ✅ |
| POST | `/sync/full-sync` | 全量同步（慎用） | ✅ |
| GET | `/sync/devices` | 已注册设备列表 | 🚧 |
| POST | `/sync/artifacts/push` | 推送 Harness Artifact | ✅ |
| POST | `/sync/artifacts/pull` | 拉取 Harness Artifact | ✅ |

### 2.2 远控（信令层在 sync 域；UI 在 IM 域）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/sync/remote-control/pairings` | 申请配对 |
| POST | `/sync/remote-control/pairings/{id}/confirm` | 桌面确认配对 |
| POST | `/sync/remote-control/route-token` | 签发 route token |
| POST | `/sync/remote-control/commands` | 下发远控命令 |
| POST | `/sync/remote-control/commands/claim` | 桌面拉取待执行命令 |
| POST | `/sync/remote-control/commands/{id}/cancel` | 取消未执行 |
| POST | `/sync/remote-control/commands/{id}/status` | 回传执行状态 |
| GET | `/sync/remote-control/commands/{id}` | 获取状态 |
| GET | `/sync/remote-control/audit-events` | 审计事件 |

### 2.3 同步协议

**数据单元**：`entity_type + entity_id + lamport_clock + payload + tenant_id`

**Push 请求**：

```json
{
  "device_id": "d_xxx",
  "lamport_clock": 12345,
  "changes": [
    {
      "entity_type": "task",
      "entity_id": "t_xxx",
      "operation": "upsert" | "delete",
      "payload": {...},
      "client_clock": 12346
    }
  ]
}
```

**Push 响应**：

```json
{
  "accepted": 10,
  "conflicts": [
    {
      "entity_type": "task",
      "entity_id": "t_xxx",
      "server_version": {...},
      "client_version": {...}
    }
  ],
  "new_server_clock": 12350
}
```

**Pull 请求**：`?since_clock=12345&device_id=d_xxx&entity_types=task,document`

### 2.4 三态模式

| 模式 | 同步对象 | 端点行为 |
|---|---|---|
| 🔒 `local` | 不同步 | 客户端不调用 sync API |
| 🔄 `hybrid` | 仅元数据 + 协作 artifact，敏感数据本地 | sync API 只接受非敏感字段 |
| ☁️ `cloud` | 全量 | 全部同步 |

桌面客户端在 `sync.push` payload 头部加 `X-Privacy-Mode: local|hybrid|cloud`，服务端按 mode 校验合法字段。

---

## 3. IM Service

**前缀**：`/api/v1/im` + `/api/v1/im-pairing` + WebSocket `/ws/im`  
**SLA**：可用性 ≥ 99.9%，消息送达 p99 < 500ms  
**鉴权**：必须

### 3.1 端点清单

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| GET | `/im/users/search` | 搜索可联系的用户/agent | ✅ |
| GET | `/im/conversations` | 会话列表 | ✅ |
| POST | `/im/conversations` | 创建会话（私聊 / 群 / agent） | ✅ |
| GET | `/im/conversations/{id}/messages` | 消息列表（分页） | ✅ |
| PUT | `/im/conversations/{id}/read` | 标记已读 | ✅ |
| WS | `/ws/im` | WebSocket 推送（消息 / 在线状态 / 任务卡更新） | 🚧 |
| POST | `/im/messages` | 发送消息 | 🚧 |
| GET | `/im/presence` | 在线状态（人 / agent） | 🚧 |

### 3.2 配对授权（移动 → 桌面）

| 方法 | 路径 | 说明 | 状态 |
|---|---|---|---|
| POST | `/im-pairing/request` | 桌面发起配对（生成二维码 + code） | ✅ |
| GET | `/im-pairing/pending` | 移动端查待授权请求 | ✅ |
| GET | `/im-pairing/authorized` | 已授权配对列表 | ✅ |
| POST | `/im-pairing/{id}/approve` | 移动端授权 | ✅ |
| POST | `/im-pairing/{id}/reject` | 移动端拒绝 | ✅ |

### 3.3 第三方 IM 适配器（出站）

来源：`backend/src/services/im_gateway/`

| 适配器 | 用途 |
|---|---|
| `feishu_adapter.py` | 飞书消息 / 卡片 / 审批 / 群机器人 |
| `dingtalk_adapter.py` | 钉钉 |
| `wechat_adapter.py` | 企微 |
| `slack_adapter.py` | Slack |
| `telegram_adapter.py` | Telegram |

> 注：这些是"出站"通知渠道。**入站 IM（用户与 agent 通过本系统聊天）走 `/im/*` + `/ws/im`**。

### 3.4 消息类型

| `type` | 含义 |
|---|---|
| `text` | 普通文本 |
| `image` | 图片 |
| `file` | 文件附件 |
| `task_card` | 任务卡（可点开 task detail，支持暂停/继续/取消） |
| `artifact_ref` | Artifact 引用（合同 / 报告 / 图谱） |
| `control_signal` | 远控信令（移动端 → 桌面） |
| `pairing_request` | 配对授权请求（移动端 inline 卡片） |
| `system` | 系统通知 |

### 3.5 在线状态三态

```
online   — 活跃中（10 分钟内有交互）
busy     — agent 正在执行任务 / 用户手动设为忙
offline  — 离线
```

agent 的扩展状态：`running` / `paused` / `error`，叠加在 `busy` 上。

### 3.6 WebSocket 协议

**连接**：`wss://api.anxinai.com/ws/im?token={access_token}&device_id={d}`

**服务端推送事件**：

```json
{ "event": "message.new", "conversation_id": "c_xxx", "message": {...} }
{ "event": "presence.update", "user_id": "u_xxx", "status": "online" }
{ "event": "task.update", "task_id": "t_xxx", "status": "running" | "paused" | "completed" }
{ "event": "pairing.request", "request_id": "p_xxx", "device": {...} }
{ "event": "remote-control.signal", "signal": {...} }
```

**客户端发送**：

```json
{ "action": "subscribe", "conversation_ids": ["c_1", "c_2"] }
{ "action": "presence.set", "status": "busy" }
{ "action": "typing", "conversation_id": "c_xxx" }
```

---

## 4. 业务域 API（不在云服务核心）

业务域 API 通过 Auth 鉴权后由客户端直接调用：

| 域 | 路由前缀 | 服务 |
|---|---|---|
| Personas | `/api/v1/persona-*` `/api/v1/personas` | 10 个 persona |
| Tasks / Agents | `/api/v1/agent-tasks` `/api/v1/agents` | TaskOrchestrator |
| RAG / 知识 | `/api/v1/rag-*` `/api/v1/knowledge*` | RAG-Anything |
| Contracts | `/api/v1/contracts` `/api/v1/esign` | 合同 + 电签 |
| Skills | `/api/v1/skills` | Skills 注册 + 执行 |
| Payments / Billing | `/api/v1/payments` `/api/v1/billing` | 计费 |
| Admin | `/api/v1/admin/*` | 18 个治理后台端点 |
| Plugins / MCP | `/api/v1/mcp` `/api/v1/skills` `/api/v1/integrations` | 工具生态 |

业务域 API 不在本契约保证 SLA 内，端点变更必须通过 PR Review。

---

## 5. 客户端调用规则

| 端 | 必须 |
|---|---|
| **桌面** | Auth + Sync + IM + 业务 API；离线模式下只用 Sync 缓存数据 |
| **移动** | Auth + IM + 业务 API（不直接同步，通过桌面）；远控信令通过 IM 入站 |
| **小程序 / UniApp** | Auth + IM 子集（消息推送 + 配对授权）；不参与同步 |
| **Web 官网** | 无（仅 `/auth/oauth/*` 用于扫码登录回调） |
| **Web 后台** | Auth + Admin 业务 API |

---

## 6. 演进与版本控制

- 本契约版本号通过 OpenAPI `info.version`。当前 `0.3.0`（V3 主线）。
- 破坏性变更必须：先 deprecate（在响应头加 `X-Deprecated: true` + `Sunset` 头），下个大版本删除。
- 桌面/移动客户端在启动时拉 `/api/v1/meta/version`，若服务端版本 < 客户端期望最低版本则提示升级。

---

## 7. 关联

- 路由实现：[`backend/src/api/routes/`](../../backend/src/api/routes/)
- IM 适配器：[`backend/src/services/im_gateway/`](../../backend/src/services/im_gateway/)
- 同步引擎（桌面）：[`desktop/src/services/sync_engine.rs`](../../desktop/src/services/sync_engine.rs)
- 远控配对：[`backend/src/services/im_gateway/pairing/`](../../backend/src/services/im_gateway/pairing/)
- 测试规范：[`02-commercial-delivery-test-spec.md`](02-commercial-delivery-test-spec.md)
- 产品蓝图：[`docs/plans/2026-05-22-product-blueprint.md`](../plans/2026-05-22-product-blueprint.md)
