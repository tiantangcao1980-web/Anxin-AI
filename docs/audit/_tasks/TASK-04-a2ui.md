# 任务 4 — A2UI 协议 + 动态工作台

> 波次 2（与任务 3/5/6/7 并行）
> 工时估：2-3 天
> 前置：任务 0 + 任务 3（协调器与意图路由稳定）联调建议
> 输出目录：`docs/audit/04-a2ui/`

---

## §1 范围

### 要碰的文件

后端（A2UI 协议层）：
- `backend/src/services/a2ui_builder.py`
- `backend/src/services/a2ui_intent_handler.py`
- `backend/src/services/a2ui_protocol.py`
- `backend/src/services/a2ui_stream.py`

前端（动态工作台 + 原语组件）：
- `frontend/src/components/a2ui/`
- `frontend/src/components/ai-primitives/`
- `frontend/src/components/document-workbench/`

测试：
- `backend/tests/test_a2ui_action_coverage.py`
- `backend/tests/test_a2ui_due_diligence_event.py`
- 新增：`backend/tests/test_a2ui_protocol_version.py`、`frontend/e2e/a2ui-workbench.spec.ts`

### 不要碰的文件

- `backend/src/services/chat_service.py` / `prompt_assembler.py` —— 任务 3
- `backend/src/services/contract_*` / `esign_service.py` —— 任务 5
- `frontend/src/lib/design-tokens.ts` —— 全局护栏，禁改

---

## §2 必修 P0（带文件:行号 + 期望状态）

### P0-1 后端事件类型 ↔ 前端组件类型 schema 一一对齐

- 位置：`backend/src/services/a2ui_protocol.py` 与 `frontend/src/components/a2ui/`、`frontend/src/components/ai-primitives/`
- 现状：后端事件枚举（`a2ui_protocol.py`）与前端组件 switch（`a2ui/Renderer.tsx`/`ai-primitives/*`）人工保持，未来一定漂移
- 期望：用 JSON Schema（或 pydantic + zod）单一来源；CI 跑 `scripts/check-a2ui-schema.ts` 校验前后端事件类型对称；新增事件必须同步前端 stub

### P0-2 action 调用越权

- 位置：`backend/src/services/a2ui_intent_handler.py`、`backend/src/services/a2ui_stream.py`
- 现状：客户端发回 `action_id` 触发后端动作时，未严格校验 `action_id` 是否属于当前用户/案件/会话，伪造 id 可触发他人案件的 action
- 期望：
  - 服务端在派发前校验 `action.session_id == current_session.id` + `action.scope_id ∈ user.accessible_scopes`
  - `action_id` 改为 HMAC 签名（含 session_id + user_id + nonce + ttl 5 min），不可伪造
  - `pytest -k a2ui_action_authz` 覆盖三类越权（跨用户 / 跨案件 / 过期）

### P0-3 未知事件 / 未知组件类型的优雅降级

- 位置：`backend/src/services/a2ui_stream.py`、`frontend/src/components/a2ui/Renderer.tsx`
- 现状：前端遇到未知 component_type 直接 throw 导致整片工作台白屏；后端遇到未知 intent 直接 500
- 期望：
  - 前端未知组件 → 渲染降级 fallback（"该组件暂不支持，请升级客户端"），不影响兄弟节点
  - 后端未知事件 → 返回 `{type: "unsupported", original_type, message}` 标准事件，前端显示提示
  - 双侧加埋点：`a2ui_unknown_component_total` / `a2ui_unsupported_event_total`

### P0-4 协议版本兼容（老客户端收到新事件）

- 位置：`backend/src/services/a2ui_protocol.py`、`frontend/src/components/a2ui/Renderer.tsx`
- 现状：协议无版本号，新增字段直接进 payload；老客户端收到新字段会因严格校验失败
- 期望：
  - 协议加 `protocol_version` 字段（semver），握手时双方协商最低公共版本
  - 后端按 `client.protocol_version` 自动降级输出（高版本字段 strip 或转 fallback 事件）
  - 双向兼容矩阵在 `docs/audit/04-a2ui/` 落表

---

## §3 流程

### Step 0 — PRD vs 代码现实差分

输出 `00-prd-reality-gap.md`，对账"动态工作台 / A2UI 协议"在 `PROJECT_STATUS.md` / `DESIGN.md` 的承诺与实际事件覆盖度。

### Step 1 — 检索与读取

1. `/hierarchical-memory find-feature "a2ui dynamic workbench"` / `find-bugfix "a2ui action"`
2. `/iterative-retrieval` 按"协议 → builder → stream → 前端 Renderer → 原语组件 → 测试"分层读
3. 列出当前所有事件类型 + 组件类型，与前端 switch 比对，输出"漂移清单"

### Step 2 — Track A 三角对齐

输出 `01-prd-coverage.md`。

### Step 3 — Track B

`/code-review` + `/api-design`（schema 单一来源）+ `/security-review`（action 越权 + 注入伪造）。

### Step 4 — P0 修复

按 P0-1 → P0-4 顺序，每个 P0 单独 commit。schema 改动一定要前后端同发。

### Step 5 — 测试补全

- `pytest -k a2ui_action_authz / a2ui_protocol_version / a2ui_unknown_event`
- `frontend/e2e/a2ui-workbench.spec.ts` 覆盖未知组件降级 + 老客户端协议协商

### Step 6 — `/verification-loop` + `/simplify` + memory 沉淀

---

## §4 输出物

```
docs/audit/04-a2ui/
  ├─ 00-prd-reality-gap.md
  ├─ 01-prd-coverage.md
  ├─ 02-issues.md
  ├─ 03-fixes.md
  ├─ 04-test-additions.md
  └─ 05-followups.md
```

代码 PR：4 个（每个 P0 一个）。

---

## §5 风险护栏

- **协议字段改动需要前后端同步发版**：任何 PR 在描述里必须列"前后端影响面 + 升级顺序 + 老客户端兼容方案"
- 不动其他模块 chat / contract / esign / prompts
- action HMAC 密钥从环境变量读取，不能写死；与任务 1 的 token 密钥隔离
- 前端 fallback 降级 UI 与 `frontend/src/lib/design-tokens.ts` 保持一致；不允许新增 hardcoded 颜色
- 未知组件降级"提示升级客户端"文案要走 i18n，不允许中文硬编码

---

## §6 完成标准 DoD

- [ ] Step 0 差分文档输出
- [ ] P0-1 schema 单一来源 + CI 校验脚本接入
- [ ] P0-2 action HMAC 签名 + 三类越权测试全绿
- [ ] P0-3 未知组件 / 未知事件降级，e2e 通过，不再白屏
- [ ] P0-4 协议版本号落地，兼容矩阵文档写完，老/新客户端各跑一轮回归
- [ ] `backend/tests/test_a2ui_*.py` 全绿（含新增）
- [ ] `frontend/e2e/a2ui-workbench.spec.ts` 全绿
- [ ] `02-issues.md` P0 全 closed
- [ ] memory 沉淀 `add-feature: a2ui-protocol-versioning` + `add-bugfix: a2ui-action-authz`
