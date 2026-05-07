# 任务 5 — 合同全生命周期 + 电子签

> 波次 2（与任务 3/4/6/7 并行）
> 工时估：4-5 天
> 前置：任务 0 + 缺口 A（对象存储）骨架 + 缺口 B（webhook 处理器骨架）已起步
> 输出目录：`docs/audit/05-contract/`

---

## §1 范围

### 要碰的文件

后端（合同 + 电签 + 审查）：
- `backend/src/services/contract_service.py`
- `backend/src/services/contract_lifecycle_service.py`
- `backend/src/services/esign_service.py`
- `backend/src/services/signature_service.py`
- `backend/src/services/document_validator.py`
- `backend/src/services/review_service.py`
- `backend/src/agents/contract_reviewer.py`
- `backend/src/agents/contract_steward.py`
- `backend/src/agents/contract_investigator.py`
- `backend/src/agents/review_checker.py`
- `backend/src/api/routes/contracts.py`
- `backend/src/api/routes/esign.py`

前端：
- `frontend/src/pages/Contracts.tsx`
- `frontend/src/pages/ContractReview.tsx`

测试：
- `backend/tests/test_contract_*.py`
- 新增：`test_contract_state_machine.py`、`test_esign_webhook_idempotent.py`、`test_esign_provider_official.py`

### 不要碰的文件

- `backend/src/services/payment_service.py` / `subscription_service.py` —— 任务 10
- `backend/src/services/a2ui_*.py` —— 任务 4
- `backend/src/services/chat_service.py` / `prompt_assembler.py` —— 任务 3
- `backend/src/api/routes/payments.py` —— 任务 10
- `frontend/src/lib/design-tokens.ts` —— 全局护栏

---

## §2 必修 P0（带文件:行号 + 期望状态）

### P0-1 合同状态机非法转换防护

- 位置：`backend/src/services/contract_lifecycle_service.py`、`backend/src/services/contract_service.py`、`backend/src/api/routes/contracts.py`
- 现状：已收口。`LEGAL_TRANSITIONS` 覆盖全部 `ContractStatus`；合同审查、手动 API 转换与 e签 webhook 写回均走 `ContractLifecycleStateMachine.transition`，非法转换抛 `IllegalStateTransition`/API 409 并保持原状态。
- 期望：
  - [x] 引入 `ContractStatus` Enum + `LEGAL_TRANSITIONS: dict[Status, set[Status]]`
  - [x] 所有本轮触达状态变更必须经 `transition(from, to, actor, reason)`，非法转换抛 `IllegalStateTransition`
  - [x] `pytest -k contract_state_machine` 覆盖全部合法转换 + 至少 6 类非法尝试。证据：`tests/test_contract_state_machine.py`、合同/e签切片 `27 passed`、e签切片 `9 passed`、后端全量 `430 passed, 1 skipped`

### P0-2 电签接口升级到官方协议（e签宝 / 法大大）

- 位置：`backend/src/services/esign_service.py`、`backend/src/core/config.py`
- 现状：代码级已收口。`ESignBaoProvider` 已实现 e签宝官方签名头、创建/启动流程、签署链接、状态查询、下载、撤销；`FaDaDaProvider` 已实现 FASC V5.1 `X-FASC-*` 签名、access token 获取、签署任务创建、签署链接、详情查询、下载、取消。默认工厂仍按 `settings.ESIGN_PROVIDER` 选择，默认 provider 保持 mock。
- 期望：
  - [x] 实现两家官方协议的最小商业闭环（创建/发起/签署链接/查询/撤销/下载）
  - [x] 凭据走 env / secret manager，禁止硬编码
  - [x] 工厂按 `settings.ESIGN_PROVIDER` 选择，默认仍是 mock
  - [x] 测试用 fake `httpx.AsyncClient` 校验请求体、官方签名头、签署链接、状态、下载、撤销
  - [ ] 真实商户沙箱 7 天回归与截图/日志证据
  - [ ] 灰度方案按 **沙箱 7 天 → 1% → 10% → 50% → 100%，每渠道独立切换** 执行并留痕

### P0-3 电签 webhook 业务回写（缺口 B 的合同部分）

- 位置：`backend/src/api/routes/esign.py`、`backend/src/services/esign_webhook_service.py`
- 现状：代码级已收口。通用 HMAC、e签宝官方 `X-Tsign-Open-*` HMAC 与法大大 FASC 表单 `bizContent`/`X-FASC-*` 验签均可进入统一 `webhook_handler`；payload 明确携带 `contract_id` 或已映射 `flow_id/signTaskId` 时可经状态机推进合同为 `signed/terminated` 并补 `sign_date`，同时写审计日志。仍缺真实账号订阅事件清单、沙箱 7 天事件样本和灰度证据。
- 期望：
  - [x] 接入横切缺口 B 的 `webhook_handler` 服务
  - [x] 解析事件 → 幂等查重（基于 `webhook_received` 表 + 官方 event id）→ 调用 `contract_lifecycle_service.transition`
  - [x] 失败进入重试队列，不能直接返回 success 蒙骗外部
  - [x] 覆盖重复回调、错序/非法转换、校验失败、e签宝官方回调、法大大 FASC 回调
  - [ ] 用真实商户后台导出的事件类型表复核 provider 状态映射

### P0-4 多版本 diff 与回滚

- 位置：`backend/src/services/contract_service.py`、`frontend/src/pages/ContractReview.tsx`
- 现状：已收口。`Contract.version` + `ContractVersion` 持久化版本账本，`apply_suggestions` 生成新版本，服务端提供版本列表、段落 diff 和 rollback；前端审查页有版本时间线、比较、diff 和回滚入口，回滚走状态机并拒绝法律终态。
- 期望：
  - [x] 服务端：`get_version_diff(contract_id, v1, v2)` 返回结构化 diff（按段落）
  - [x] 前端：审查页加"版本时间线 + diff 视图 + 回滚到此版本"按钮，回滚需二次确认
  - [x] 回滚必走状态机（不可在"已归档"/终态状态回滚）
  - [x] 证据：`tests/test_contract_versions.py`、`tests/test_contract_version_migration.py`、`frontend/e2e/contract-lifecycle.spec.ts`，后端全量 `430 passed, 1 skipped`

### P0-5 审查并发与超时；签署回调幂等

- 位置：`backend/src/services/contract_service.py`、`backend/src/services/contract_review_lock.py`、`backend/src/services/webhook_idempotency_service.py`、`backend/src/services/webhook_handler.py`、`backend/src/api/routes/contracts.py`、`backend/src/api/routes/esign.py`
- 现状：已收口。合同审查通过 `ContractReviewLock` 对同一合同/版本加短租约锁，`CONTRACT_REVIEW_TIMEOUT_SECONDS` 默认 90s；超时或异常会把合同推进 `review_failed`，允许重试再进入 `under_review`。`handle_verified_webhook` 在 `webhook_received` 幂等表外再加 `webhook_processing_lock`，并发重复事件被串行化，业务写回只执行一次。
- 期望：
  - [x] 审查任务加分布式锁（基于合同 id + 审查轮次），同一合同同时只能一个审查在跑
  - [x] 单次审查 LLM 总超时 90s，超时后任务标 `review_failed`，可手动重试
  - [x] 签署回调用 `(provider, event_id)` 唯一索引 + Redis/local 短期锁，杜绝并发双写
  - [x] 证据：`tests/test_contract_review_workflow.py` 并发/超时重试，`tests/test_webhook_business_events.py` 并发重复 webhook，合同/e签组合切片 `54 passed, 9 deselected`

### P0-6 合同附件接对象存储抽象层（缺口 A）

- 位置：`backend/src/models/contract.py`、`backend/src/services/contract_service.py`、`backend/src/api/routes/contracts.py`、`frontend/src/lib/api.ts`、`frontend/src/pages/ContractReview.tsx`
- 现状：已收口。新增 `ContractAttachment` 对象存储记录与 Alembic 迁移 `037_add_contract_attachments.py`；附件上传走 `read_validated_upload_file` 和 `object_storage_service.put`，列表/下载/下载 URL/删除均按合同所属组织校验，上传/下载/删除写入审计日志；前端合同审查页可上传、下载、删除附件。
- 期望：
  - [x] 调用任务 6 / 缺口 A 提供的 `object_storage_service`
  - [x] 上传 → put + 写 DB；下载 → org-scoped object read；删除 → 对象 + DB 双删
  - [x] alembic 迁移：附件表加 `storage_backend` / `object_key`
  - [x] 证据：`tests/test_contract_attachments.py`、`tests/test_contract_attachment_migration.py`、合同/对象存储/上传授权切片 `26 passed`

---

## §3 流程

### Step 0 — PRD vs 代码现实差分

输出 `00-prd-reality-gap.md`，重点：电签最初声称"已支持"实际是 mock；本轮已补官方 provider 代码级适配、官方 webhook 验签、flow 映射、持久幂等、状态机与审计双写。真实商户沙箱闭环、账号事件表和灰度证据仍需收口。

### Step 1 — 检索与读取

1. `/hierarchical-memory find-feature "contract lifecycle state machine"` / `find-bugfix "esign webhook"`
2. `/iterative-retrieval` 按"路由 → service → agent → 模型 → 前端 → 测试"分层读
3. 阅读官方电签协议文档（e签宝 OpenAPI / 法大大 OpenAPI），列出最小必需端点

### Step 2 — Track A 三角对齐

输出 `01-prd-coverage.md`，把"起草 → 审查 → 风险 → 修改 → 签署 → 归档"六态全链路对账。

### Step 3 — Track B

`/code-review` + `/backend-patterns` + `/api-design` + `/security-review`（webhook 重放 / 越权 / 注入）+ `/database-patterns`（状态机迁移）。

### Step 4 — P0 修复

顺序：P0-1 状态机 → P0-6 对象存储接入 → P0-4 版本 diff → P0-5 并发 / 幂等 → P0-2 官方协议适配（沙箱）→ P0-3 webhook 业务回写。每个 P0 单独 commit。

### Step 5 — 测试补全

- `/tdd-workflow` 补 P0-1 状态机 + P0-3 webhook 幂等 + P0-2 provider 录回放
- `/e2e-testing` 补 `frontend/e2e/contract-lifecycle.spec.ts`（上传/起草 → 审查 → 版本 diff/回滚；签署 → 归档随 P0-2/P0-3 后续补）

### Step 6 — `/verification-loop` + `/simplify` + memory 沉淀

---

## §4 输出物

```
docs/audit/05-contract/
  ├─ 00-prd-reality-gap.md
  ├─ 01-prd-coverage.md
  ├─ 02-issues.md
  ├─ 03-fixes.md
  ├─ 04-test-additions.md
  └─ 05-followups.md
```

代码 PR：建议 6 个（每个 P0 一个），P0-2 官方协议 PR 必须附"沙箱 7 天回归截图"。

---

## §5 风险护栏

- **webhook 切官方协议必须走灰度**：沙箱 7 天 → 1% → 10% → 50% → 100%，**禁止 big-bang**；**每渠道独立切换**（e签宝先于法大大或反之，由用户决定顺序）
- **每个 webhook PR 必须在描述里贴沙箱回归证据**（请求/响应日志 + 7 天无异常截图）
- 不动 `payment_service` / `subscription_service`（任务 10）
- 状态机改动若新增/删除 enum 值需提供 alembic 迁移 + 回滚脚本；本轮仅复用既有 `ContractStatus`，未改 schema
- 电签 provider 凭据从 env / secret manager 读取；测试 fixture 不允许出现真实凭据
- 合同附件对象存储接入若与任务 6 同步进行，需先与任务 6 工程师对齐 `object_storage_service` 接口签名
- 涉及法律效力的"已签署 / 已归档"状态变更要双写审计日志（操作人 + 时间 + IP + reason）

---

## §6 完成标准 DoD

- [x] Step 0 差分文档输出，用户审阅路径：`docs/audit/05-contract/00-prd-reality-gap.md`
- [x] P0-1 状态机 Enum + 转换矩阵 + 测试全绿（含 ≥ 6 类非法尝试）。证据：`tests/test_contract_state_machine.py`、合同/e签切片 `27 passed`、e签切片 `9 passed`、后端全量 `430 passed, 1 skipped`
- [x] P0-2 e签宝 + 法大大官方协议代码级适配完成；默认 provider 仍 mock。证据：`tests/test_esign_provider_clients.py`、电签/provider 切片 `9 passed, 20 deselected`
- [ ] P0-2-sandbox 真实商户沙箱跑通；灰度方案文档完整并有 7 天回归截图/日志
- [x] P0-3 电签 webhook 官方协议代码级联通；错序 / 官方事件 id / 法大大 FASC 测试覆盖。证据：`tests/test_official_webhook_security.py`、`tests/test_webhook_business_events.py`、`tests/test_external_surface_guards.py`、合同/e签/provider 切片 `56 passed, 8 deselected`
- [ ] P0-3-sandbox 真实账号订阅事件映射与沙箱回调样本复核完成
- [x] P0-4 版本 diff + 回滚按钮上线；e2e 通过。证据：`tests/test_contract_versions.py`、`tests/test_contract_version_migration.py`、`frontend/e2e/contract-lifecycle.spec.ts --project=chromium` → `1 passed`
- [x] P0-5 审查分布式锁 + 90s 超时；签署回调并发测试无双写。证据：`tests/test_contract_review_workflow.py`、`tests/test_webhook_business_events.py`，合同/e签组合切片 `54 passed, 9 deselected`
- [x] P0-6 合同附件走 `object_storage_service`；alembic 迁移落地；前端审查页可操作附件。证据：`tests/test_contract_attachments.py`、`tests/test_contract_attachment_migration.py`、合同/对象存储/上传授权切片 `26 passed`
- [x] P0-1/P0-2/P0-3/P0-4/P0-5/P0-6 相关 `pytest` 切片 + 后端全量全绿。证据：后端全量 `430 passed, 1 skipped, 10 warnings`
- [x] `frontend/e2e/contract-lifecycle.spec.ts` 全绿
- [ ] `02-issues.md` P0 全 closed（剩真实商户沙箱/灰度证据，不再是代码级 provider 缺口）
- [x] memory 沉淀：`add-feature: contract-state-machine` 已记录为 `feature-1778041562837`；`add-feature: contract-version-diff-rollback` 已记录为 `feature-1778043201056`；`add-feature: contract-review-timeout-webhook-lock` 已记录为 `feature-1778043952565`；合同附件、官方电签 provider 与 FASC webhook 已写入 project memory（当前 `noteCount: 16`）
