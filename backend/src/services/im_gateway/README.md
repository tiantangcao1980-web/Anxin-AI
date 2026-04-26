# im_gateway —— 多 IM 通道适配（P1 骨架）

## 用途
让安心智能助手以**机器人**身份接入用户日常使用的 IM。法律团队往往同时在飞书 / 微信 / 钉钉中工作，agent 需要"主动找上门"而不是等用户切换 App。

参考实现：Hermes-Agent 的多通道抽象 + Accio Work 营销工具的消息渠道 UI 配置体验。

## 设计要点

### 1. 适配器抽象（`base.py`）
4 个抽象方法构成最小契约：
- `send_message`：单向推送（agent → 用户）
- `receive_webhook`：归一化平台回调
- `register_bot`：首次接入 / 配置变更
- `list_groups`：拉群列表（用于"选择推送目标"UI）

子类只需实现这 4 个方法 + `channel_type` 类属性，即可被 `IMAdapterRegistry` 路由。

### 2. 配对授权（24h 窗口）
平台 ID（飞书 `open_id` / Slack `U...`）必须与内部 `users.id` 绑定后才能推送。流程：

1. 用户在 IM 端发送配对码（如 `/bind 837421`）
2. `receive_webhook` 解析后创建 `PairingRequest{status=PENDING, expires_at=now+24h}`
3. 内部用户在 App 内的"待审批"看到请求并点"同意"
4. 状态转 `APPROVED` 并落 `IMBinding`，后续推送即可使用 `internal_user_id`

24h 后未审批 → 定时任务（P3 cron）扫描 `expires_at < now AND status=PENDING` → 置 `EXPIRED`。

### 3. 通道接入路线

| 平台 | 优先级 | 关键挑战 |
|------|--------|----------|
| **飞书 Lark** | **P3 首发** | tenant_access_token 自动刷新；事件加密回调 |
| 微信（企微 / 公众号 / 小程序） | P3+ | 三套不同的回调 / 消息体协议 |
| 钉钉 | P3+ | 群机器人限频（20/分钟），优先用「企业内部应用」工作通知 |
| Telegram | P4 | 国内出网代理；Webhook vs Long Polling |
| Slack | P4 | Events API 签名校验；Block Kit 卡片 |
| Discord | P5 预留 | 已在枚举中占位，未实现 adapter |

## 文件结构

| 文件 | 角色 |
|------|------|
| `base.py` | `BaseIMAdapter` 抽象基类 |
| `feishu_adapter.py` / `wechat_adapter.py` / `dingtalk_adapter.py` / `telegram_adapter.py` / `slack_adapter.py` | 5 个通道占位实现 |
| `registry.py` | `IMAdapterRegistry`，按 `channel_type` 路由 + 默认全注册 |
| `models.py` | `IMChannel` / `IMBinding` / `PairingRequest` ORM |

## 与既有 `models/im.py` 的关系
既有的 `im_conversations / im_participants / im_messages` 是**应用内** IM；本模块是**外部** IM 网关，表名前缀 `im_gateway_*` 隔离，互不影响。
