# 任务 0 产出物 3 — 横切系统级缺口（影响多模块的根因）

> 来源：18 处代码点位实测 + 模块依赖关系推导
> 目的：把"看起来是模块级 BUG"实际上是"系统级未接基础设施"的事项识别出来。**不在系统级方案落地前，模块级修补只会到处长野草**

---

## 1. 三个系统级缺口

### 缺口 A — 对象存储（MinIO/S3）底座已接，跨模块迁移未完成

**位置**：[object_storage_service.py](../../backend/src/services/object_storage_service.py)、[document_service.py](../../backend/src/services/document_service.py)、[029_add_document_object_storage_fields.py](../../backend/alembic/versions/029_add_document_object_storage_fields.py)

**现状**：
- 2026-05-06 已新增 `object_storage_service.py`，支持 `local` 与 `minio` 后端。
- `upload_document` / `delete_document` / `update_document_content` 已写入/删除真实对象，`document_versions` 也记录 `storage_backend` + `object_key`。
- `ContractService.save_contract_file` 已从 `data/contracts` 本地直写切到对象存储。

**对其他模块的隐藏影响**：
- IM 文件消息、尽调附件、案件证据、模板上传、桌面同步文件、A2UI 导出仍需逐入口切到统一对象存储接口。
- 历史 `file_path` 已由迁移 029 回填到 `object_key` / `storage_backend='local'`；生产上线前仍需做 DB 行数 vs 对象数抽样比对。

**根本原因**：
- README 第 71 行宣称 PostgreSQL/Redis/Qdrant/Neo4j/MinIO 五件套，docker-compose.yml 也包含 MinIO 容器
- 但 backend/src/services/ 下找不到统一的 `storage_service.py` 或 MinIO/S3 client 抽象层
- 2026-05-06 前 `document_service` 只有 TODO；当前根因已从"无对象存储底座"收窄为"跨模块迁移、生产凭据、历史数据 backfill 未完成"

**修复策略**：
1. 已完成：`object_storage_service.py` + `029_document_object_storage` + DocumentService/ContractService 主入口接入。
2. 待完成：全文 grep 其他业务模块中"应该存文件但没存"的地方（IM/尽调/案件/模板/A2UI/桌面同步）→ 统一接到 object_storage_service。
3. 待完成：生产/预发环境 DB 行数 vs 对象数抽样比对。

**该修在哪个任务**：任务 6（文档主任务）建立 storage_service；任务 5/9/8/10/11 各自切换为调用

**护栏**：
- MinIO 凭据要从 task 0 SOP 走过的"新凭据"路径，不能复用旧的
- 切换前要做"双写过渡期"：先写 DB + 写文件，确认两边一致后再切只读路径

---

### 缺口 B — Webhook 业务闭环仍不完整（通用回写/幂等/重试已落，真实渠道仍待沙箱闭环）

**位置**：
- [payments.py:308](../../backend/src/api/routes/payments.py) 微信支付 webhook
- [payments.py:334](../../backend/src/api/routes/payments.py) 支付宝 webhook
- [esign.py:337](../../backend/src/api/routes/esign.py) 电签 webhook

**现状**：
- 支付 webhook 的通用 HMAC 路径已接 `payment_webhook_service.py`，可根据回调 payload 推进 `PaymentOrder` 状态，并在订阅订单场景更新 `Subscription.last_payment_id` 与状态。
- 电签 webhook 的通用 HMAC 路径已接 `esign_webhook_service.py`，当 payload 明确携带 `contract_id` 或已映射的第三方 `flow_id` 时可将完成/签署事件回写为 `ContractStatus.SIGNED` 并补 `sign_date`。
- 微信支付 v3 回调/同步响应 RSA-SHA256 验签、Wechatpay 资源 AES-GCM 解密、支付宝同步响应/异步通知 RSA2 验签、e签宝 `X-Tsign-Open-*` HMAC 回调验签已落到 `official_webhook_security.py`，并通过路由/provider 接入。
- 微信/支付宝真实下单、查询、关闭、退款请求代码已落地；仍未完成沙箱凭据、微信平台证书/公钥轮换验证与真实渠道闭环。
- e签宝 provider/官方回调 HMAC 与法大大 FASC provider/webhook 代码级协议已落；仍未完成真实账号事件映射、商户沙箱 7 天和灰度证据；第三方 `flow_id` 到本地合同的持久映射已通过 `contracts.esign_flow_id` 落地。
- `webhook_received` 持久化幂等表与 `(scope, idempotency_key)` 唯一约束已落地，支付/电签重复通知会跳过业务副作用。
- Admin `/admin/webhooks` 已可按 `scope/status` 查询 webhook 幂等记录、返回状态统计并对失败记录发起手动重试。
- `/metrics` 已暴露 `anxin_webhook_received_total` / `anxin_webhook_failed_total` / `anxin_webhook_processing`。
- 失败 webhook 自动重试/backoff 已落地：`last_retry_at` / `next_retry_at` 调度字段、`retry_due_failed_webhooks` 批处理与 `WEBHOOK_RETRY_WORKER_ENABLED` 后台 worker 开关已完成。
- 仍缺渠道真实沙箱重试策略验证、账号事件映射、证书/事件轮换和灰度证据；稳定业务事件对象、官方通知 id 幂等、e签宝/法大大电签代码级协议已补。

**对其他模块的隐藏影响**：
- 订阅模块的通用回调路径已有最小回写能力，但真实微信/支付宝渠道未接入前不能作为生产支付闭环。
- 合同模块的"已发起签署 → 已签署"分支已有最小回写能力，但官方电签渠道、归档、审计双写仍未闭环。
- 如果回调 payload 不符合当前通用解析字段，客户端仍可能一直看到订单 `pending`。
- ValueDashboard 等订阅价值组件展示数据永远是初始态

**根本原因**：
- PROJECT_STATUS Batch 5 + Batch 7 的"webhook 升级"以通用 HMAC 为主，未覆盖真实渠道沙箱闭环与全部电签 provider 协议。
- 本轮补了支付/电签通用业务回写、稳定业务事件对象、持久幂等、手动/自动重试、指标、统一 `webhook_handler.py`、e签宝 provider/官方回调 HMAC 与法大大 FASC provider/webhook；仍缺通知触发、真实商户沙箱、账号事件映射与灰度证据。

**修复策略**：

**Phase 0.5：已完成的最小业务回写**
- `payment_webhook_service.py` 支持订单 id / 状态 / transaction id 提取。
- 微信、支付宝现有通用 HMAC webhook 可推进订单状态，订阅订单可更新订阅状态。
- `esign_webhook_service.py` 支持 `contract_id` / `flow_id` / 状态 / 签署时间提取。
- 电签现有通用 HMAC webhook 可在 payload 带 `contract_id` 或已映射 `flow_id` 时推进合同为已签署并补签署日期。
- 覆盖测试：`test_wechat_payment_webhook_updates_order_status`、`test_alipay_payment_webhook_updates_subscription`、`test_esign_webhook_accepts_valid_signature`。

**Phase 0.6：已完成的失败重试与观测底座**
- `webhook_received` 增加 `last_retry_at` / `next_retry_at`，失败时按指数 backoff 计算下次重试窗口。
- `webhook_retry_service.py` 支持人工重试单条失败记录与批量重试 due failed records。
- `webhook_retry_worker.py` 在 `WEBHOOK_RETRY_WORKER_ENABLED=true` 时由 FastAPI lifespan 启动，按 `WEBHOOK_RETRY_INTERVAL_SECONDS` 扫描失败记录。
- 覆盖测试：`test_webhook_retry_worker_retries_due_failed_records`、`test_webhook_retry_worker_respects_max_attempts`。

**Phase 1：统一 webhook 处理器骨架（已完成）**
```python
# backend/src/services/webhook_handler.py
async def handle_verified_webhook(scope: str, payload: dict, idempotency_key: str):
    # 1. 幂等查重（复用 webhook_idempotency_service + webhook_received 表）
    # 2. 路由到对应 scope 的业务回写函数
    # 3. 业务函数返回结果 → 写入 webhook_received 表
    # 4. failed 记录自动写入 backoff 信息，供 Admin/worker 重试
```

**Phase 2：每个渠道实现"签名 → 解析 → 业务事件"3 步**
- 微信支付 v3 → ✅ Native 下单/查单/关单/退款、同步响应验签、回调 RSA-SHA256 验签与资源解密、官方通知 id 幂等已落；仍需沙箱回归、证书/公钥轮换验证与沙箱重试策略验证
- 支付宝 → ✅ page.pay/query/refund/close 签名请求、同步响应验签、异步通知 RSA2 验签与 `notify_id` 幂等已落；仍需沙箱回归、WAP/APP 与沙箱重试策略验证
- e签宝 → ✅ `X-Tsign-Open-*` 回调 HMAC 验签已落；仍需账号订阅事件映射到 `ContractSignedEvent` / `ContractCancelledEvent`，以及 provider 创建/查询/撤销/下载沙箱闭环
- 法大大 → 同上

**Phase 3：业务回写**
- 订单状态机推进 + 触发订阅生效
- 合同状态机推进 + 自动归档
- 通知发起人（IM 内 + 邮件 + 推送）

**Phase 4：观测**
- 已有 webhook_received 表字段：`processed_at` / `error` / `retry_count` / `last_retry_at` / `next_retry_at`
- 已有 Admin `/admin/webhooks` 接口展示"未处理 webhook" / "处理失败 webhook"基础数据并支持失败记录手动重试，前端页面仍可按需接入
- 已有 Prometheus 文本指标：`anxin_webhook_received_total` / `anxin_webhook_failed_total` / `anxin_webhook_processing`

**该修在哪个任务**：
- 骨架在任务 0 后续做（或任务 10 起步时建）
- 渠道适配在任务 5（电签）+ 任务 10（支付）

**护栏**：
- **不允许 big-bang 切换**：先在沙箱跑 7 天，零异常再灰度
- 灰度顺序：支付宝沙箱 → 微信沙箱 → 电签沙箱 → 灰度生产 1% → 10% → 50% → 100%
- 每个渠道切换都要在 PR 描述里贴"沙箱回归 7 天"的截图

---

### 缺口 C — 桌面同步数据面仍未商业闭环（假成功已清除）

**位置**：
- [sync.rs](../../desktop/src/commands/sync.rs) Rust IPC 直连同步 fallback 已代码级接入 SQLCipher `sync_log` push/pull 写回，并继续在 TopSecret/未登录时 fail-closed，报告本地待同步、离线任务和冲突统计
- [sync_engine.rs:191](../../desktop/src/services/sync_engine.rs) `push_pending_records` 未启用时返回 Error
- [sync_engine.rs:199](../../desktop/src/services/sync_engine.rs) `pull_incremental_updates` 未启用时返回 Error

**现状**：2026-05-08 后旧的 `Ok(0)` 假成功已清除，未启用的后台 `SyncEngine` 数据面会显式失败，不再告诉用户“同步完成”。2026-05-09 `trigger_sync` Rust IPC fallback 已补代码级 SQLCipher push/pull 写回；商业缺口仍在：packaged runtime push/pull/conflict/retry、跨设备会话延续、移动远控命令队列和 signed packaged runtime 证据还没有闭合。

**对其他模块的隐藏影响**：
- ROADMAP M3「跨设备会话延续（桌面开始 → 手机继续）」依赖真实同步与远控协议，当前仍不能标记完成
- 桌面端"绝密本地"模式已能保持不上行的安全边界，但非绝密/混合模式还缺真实云端同步证据
- 文档模块依赖（缺口 A）+ 同步依赖（缺口 C）仍需要 packaged runtime smoke 证明数据可持久、可恢复、可跨设备延续

**根本原因**：
- ROADMAP 曾把"离线任务队列 + 同步引擎"标为已完成，因 `desktop/src/services/sync_engine.rs` 文件存在
- 代码级假成功已经被改为 fail-closed；下一步不是继续删除旧 fallback，而是补真实云数据面、远控审计和 packaged runtime 证据

**修复策略**：

**Phase 1：SQLite schema + 离线队列**
```sql
-- desktop/migrations/001_offline_queue.sql
CREATE TABLE offline_tasks (
    id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- case/contract/document/message
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,    -- create/update/delete
    payload BLOB NOT NULL,
    created_at INTEGER NOT NULL,
    status TEXT DEFAULT 'pending',  -- pending/syncing/synced/failed
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);
CREATE INDEX idx_status ON offline_tasks(status);
CREATE INDEX idx_entity ON offline_tasks(entity_type, entity_id);

CREATE TABLE sync_state (
    key TEXT PRIMARY KEY,
    value TEXT
);
-- 例：sync_state['last_sync_version'] = '12345'
```

**Phase 2：push 实现（从 SQLite 到云端）**
- `push_pending_records` 读 `WHERE status='pending'`，限 100 条
- POST 给后端 `/api/v1/sync/push`，body = records 列表
- 后端处理：每条按 entity_type 路由到对应 service 的 upsert
- 后端返回 `{accepted: [...], rejected: [{id, reason}]}`
- 桌面端把 accepted 的标记为 synced，rejected 的标 failed + 写 last_error

**Phase 3：pull 实现（从云端到 SQLite）**
- `pull_incremental_updates` GET `/api/v1/sync/pull?since_version=X`
- 后端基于 sync_log 表返回所有大于 X 的变更
- 桌面端写入 SQLite + 更新 sync_state['last_sync_version']
- 处理本地与云端冲突（需要冲突合并策略）

**Phase 4：冲突合并**
- 默认策略：last-writer-wins（云端 updated_at 比本地新 → 云端赢）
- 用户可见冲突队列：在桌面端"我的待解决冲突"页面手动选择
- 复用现有 [sync.rs:155 `resolve_conflict`](../../desktop/src/commands/sync.rs) 上行接口

**Phase 5：观测 + 自动重试**
- offline_tasks.failed 自动按指数退避重试（1m / 5m / 15m / 1h）
- 退避超过 24h 仍 failed → 提示用户人工处理

**该修在哪个任务**：任务 11b（独立任务，工时 7-10 天）

**护栏**：
- 桌面端 SQLite schema 改动要走 Rust-owned SQLCipher migration/service 机制，不能绕过 `desktop/migrations/` 和 `secure_db` 直接改本地库
- 同步引擎上线前要在 50 个种子用户灰度跑至少 14 天
- 后端 sync 接口要做"按 device_id + user_id 隔离的限流"（防恶意刷）

---

## 2. 三个缺口的依赖关系

```
缺口 A 对象存储 ─────┬───→ 任务 5 合同（附件）
                    ├───→ 任务 6 文档（主体）
                    ├───→ 任务 8b 案件（证据）
                    ├───→ 任务 9 尽调（报告）
                    ├───→ 任务 10 IM（文件消息）
                    └───→ 任务 11b 桌面同步（文件 records）

缺口 B Webhook ─────┬───→ 任务 5 合同（电签回写）
                    └───→ 任务 10 订阅（支付回写）

缺口 C 桌面同步 ─────→ 任务 11b（自身）+ 任务 11c 移动端（共用 sync 协议）
```

**结论**：
- 缺口 A 的底座已落地，后续阻断集中在 MinIO/S3 外部配置、backfill 与下游入口真实运行证据。
- 缺口 B 的代码级官方协议与幂等/重试底座已落地，上线仍必须等真实支付/电签沙箱与灰度证据。
- 缺口 C 已由任务 11b 推进到 SQLCipher/keyring、Rust IPC fallback、unsigned release packaged-binary loopback 和跨设备代码级 rehearsal；商业闭环仍必须等 signed packaged runtime、shared-staging sync transcript、交互式冲突/人工处理 UI transcript 和真机跨设备续接证据。

---

## 3. 优先级与排期建议

| 缺口 | 建议起步时机 | 关键产出 |
|---|---|---|
| A 对象存储 | 任务 0 完成后，与任务 1/2 并行启动（独立工程师） | ✅ 底座已落地；剩余 MinIO 凭据、backfill、业务附件入口迁移 |
| B Webhook 骨架 | 任务 0 完成后，由任务 5 工程师起步（合并到任务 5）| ✅ `webhook_received` + `webhook_idempotency_service` + `webhook_handler.py` + `webhook_events.py` + Admin 查询/手动重试 + Prometheus 指标 + 自动重试/backoff + 官方通知 id 幂等 + e签宝 provider/官方回调 HMAC + 法大大 FASC provider/webhook 已落；真实沙箱、账号事件映射与灰度证据待补 |
| C 桌面同步 | 已完成代码级/unsigned release 本地证据；商业证据继续推进 | signed packaged runtime + shared-staging sync transcript + 交互式冲突/人工处理 UI transcript + 真机跨设备续接 |

---

## 4. 与其他文档的对账

完成本节后，需要回写：
- `PROJECT_STATUS.md` → 2026-05-09 已补商业交付状态纠偏，明确桌面 11a/11b 的代码级证据与 signed/runtime/真机阻断
- `PRODUCT_ROADMAP.md` → 2026-05-09 已把"离线任务队列 + 同步引擎"从完成态改为代码级/unsigned 证据已具备、商业证据待补，并把移动端路线改为 uni-app
- 在 `docs/architecture-v2.md` 中加一节"对象存储抽象层"（缺口 A 的设计）

---

> 文档作者：Claude Code
> 状态：待用户审阅 → 同意后由对应任务工程师起步
