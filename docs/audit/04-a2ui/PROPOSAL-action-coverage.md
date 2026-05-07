# 提案：A2UI 协议加固方案

> 来自 TASK-04 P0-1 / P0-2 / P0-3 / P0-4
> 范围：仅盘点 + 修复方案，不改代码
> 引用格式：`relative/path:line`

## 1. 现状盘点

### 1.1 后端事件 / 组件类型枚举
- 协议工厂集中在 `backend/src/services/a2ui_protocol.py`，全部走自由 dict 字面量，没有 Pydantic / dataclass：
  - 通用：`recommendation-card:51`、`lawyer-card:90`、`horizontal-scroll:106`、`form-sheet:131`、`order-card:177`、`info-banner:195`、`button-group:209`、`status-card:229`、`detail-list:243`、`progress-steps:258`、`risk-indicator:278`、`text-block:294`、`divider:302`、`service-selection:316`、`contract-preview:343`、`action-bar:359`
  - 扩展接口：`map-view:383`、`payment-card:415`、`lawyer-picker:440`、`media-card:465`、`schedule-picker:487`、`feedback-card:511`、`plugin-container:535`
  - 法务专用：`case-progress:724`、`risk-assessment:758`、`contract-compare:790`、`fee-estimate:829`
- 流事件 4 种：`stream_start:599`、`stream_component:632`、`stream_delta:667`、`stream_end:687`（在 `a2ui_protocol.py`），运行时由 `a2ui_stream.py:50/65/71/77` 发送。
- 意图 6 种、action 25+：`a2ui_intent_handler.py:36-64` 列出 `find_lawyer / review_contract / draft_document / risk_assessment / due_diligence / legal_consultation`；`handle_a2ui_event:115-198` 用 `if action_id == ...` 长链分发。

### 1.2 前端组件类型枚举
- 真正生效的 switch 在 `frontend/src/components/a2ui/A2UIRenderer.tsx:82-142`，覆盖 27 种 kebab-case 类型，与后端 `a2ui_protocol.py` 一一对应（人工抄写）。
- 联合类型在 `frontend/src/components/a2ui/types.ts:33-62`，新组件需要同时改 union、interface 和 switch 三处。
- 还存在一份 **平行废弃注册表** `frontend/src/components/a2ui/core/A2UIComponentRegistry.ts:11-74`（snake_case：`button / card / legal_clause / case_analysis / risk_matrix`），与上面 27 种完全没有交集，是历史 dead-code，但没有标 deprecated，未来一定漂移。
- 流式状态机在 `frontend/src/components/a2ui/StreamingA2UIRenderer.tsx:336-389`，`stream_*` 4 个 action 字面量与后端硬编码对齐。

### 1.3 schema 是否双方共享
- **没有**单一来源。后端是 dict + 字符串 type，前端是 TS interface，靠人肉 review。
- 没有 OpenAPI / protobuf / JSON Schema 导出脚本，也没有 CI 校验。
- 字段命名约定不统一：后端构造时既有 camelCase（`imageFallback`、`ratingText`）又夹 snake 入参（如 `lawyer_id`），靠工厂函数手动转 camel；一旦绕过工厂写 raw dict（`a2ui_stream.py:121-144` 的 `make_lawyer_card`）就缺失 type-check。

### 1.4 测试覆盖了哪些 action
- `backend/tests/test_a2ui_action_coverage.py:10-25`：用正则 `actionId":\s*"([^"]+)"` 扫描源码里所有 `actionId`，逐个跑 `handle_a2ui_event` 看是否非空。覆盖了"分发完整性"，但**不**覆盖：authz、签名、过期、未知 action、未知事件。
- `test_a2ui_action_coverage.py:29-48` 烟测 6 个常用 action 返回非空。
- `backend/tests/test_a2ui_due_diligence_event.py:10-55` mock `get_company_info`，验证 `start_due_diligence` 的卡片结构。
- 前端 / e2e 当前**没有** `a2ui-workbench.spec.ts`（TASK-04 §1 列为"新增"）。

---

## 2. P0 必修项的具体差距

### 2.1 P0-1 schema 一致性
- 单一来源缺失。后端 27 种 kebab-case + 前端 27 种 union + 前端注册表 9 种 snake_case **三套**并存。
- 不一致案例：
  - 后端 `make_lawyer_card`（`a2ui_stream.py:111`）和 `lawyer_card`（`a2ui_protocol.py:56`）字段大小写一致但**默认 action 不同**（`consult_lawyer` vs `contact_lawyer`），前端 switch (`A2UIRenderer.tsx:84`) 不感知。
  - `A2UIComponentRegistry.ts` 注册的 `legal_clause / case_analysis / risk_matrix / contract_viewer` 在后端协议层根本不存在；反过来后端 `payment-card / map-view / schedule-picker / plugin-container` 在注册表里也没有。
  - `types.ts:48` 写了 `LawyerPickerComponent.data.lawyers: A2UIComponent[]`，但后端 `lawyer_picker:436` 直接传 `lawyers` raw list（不是组件包装），结构对不上。

### 2.2 P0-2 action 越权
- 前端事件回调 `A2UIRenderer.tsx:154-164` 仅做 `expiresAt` 检查，无签名。
- 后端入口 `chat_handlers/a2ui_handler.py:22-29` 只把 `conversation_id` 注入 context，**完全没有**传 `user_id / org_id / case_id`。`handle_a2ui_event` (`a2ui_intent_handler.py:115`) 也没有 `current_user` 参数。
- 风险面：客户端任何拿到 ws 的人构造 `{type:"a2ui_event", action_id:"confirm_engagement", payload:{lawyerId:"lawyer-001"}}` 即可直接走完委托确认，跨会话伪造 `conversation_id` / `lawyerId` 服务端无校验。
- 当前所有 `payload.lawyerId / serviceId / docType` 都是 raw 字符串，**没有 HMAC、没有 nonce、没有 ttl**。
- 测试中没有任何越权 case（`test_a2ui_action_coverage.py` 覆盖正向）。

### 2.3 P0-3 未知事件 / 未知组件降级
- 前端：`A2UIRenderer.tsx:139-141` 默认分支是 `console.warn` + `return null` —— 整个组件**静默吞掉**，但 motion wrapper (`A2UIRenderer.tsx:177-183`) 仍然占位渲染空 div + delay 动画，肉眼看是 layout 抽了一格，体验不是"白屏"但也不是"提示升级"。`A2UIComponentRegistry` 那一套根本没接入运行时，缺少 fallback "暂不支持" UI。
- 后端：`a2ui_intent_handler.py:197` 未知 action 返回 None；`chat_handlers/a2ui_handler.py:40-41` 走 `return False` → 上游 `chat.py:595-598` 把 raw 文本 `"用户执行了操作: <action_id>"` 当成普通对话发给 LLM，**不是 500，但是会污染对话上下文 + 浪费 token**，且前端不知道这个 action 被降级了。
- 没有 `{type:"unsupported", original_type, message}` 标准事件；没有 `a2ui_unknown_component_total / a2ui_unsupported_event_total` 埋点。

### 2.4 P0-4 协议版本兼容
- 协议消息体 (`a2ui_protocol.py:540-566` 的 `a2ui_message`) 没有 `protocol_version` 字段，`metadata` 也没有版本。
- 流事件同上 (`a2ui_stream.py:80-99`)。
- 仅有的"version"是 `A2UIComponentRegistry.ts` 各 entry 的 `version: '1.0.0'`，没接入运行时协议协商。
- 老客户端收到新事件类型：经过前端 union 类型断言的 `as any`（`A2UIRenderer.tsx:117/119/121/123`）其实**不会硬崩**，但 default 分支 `return null` 静默吞，用户看不出来，没有"请升级客户端"提示。
- 老客户端收到新字段：interface 是 `optional` 字段为主，结构上不严格，所以加字段不立即崩；但前端渲染组件内部如果断言新字段为必填会运行时 undefined。
- `frontend/e2e/` 目前不存在 `a2ui-workbench.spec.ts`（待新增）。

---

## 3. 实施方案（仅草稿，不直接改）

### 3.1 schema 单一真相源
- 推荐：用 `pydantic.BaseModel` 把 `a2ui_protocol.py` 的 27 个工厂 + 4 个 stream event 重写为模型；`a2ui_protocol/__init__.py` 暴露便捷工厂保持向后兼容。
- 用 `datamodel-code-generator` 或 `pydantic2ts` 在 `make schema` 中导出 `frontend/src/components/a2ui/schema.gen.ts`，前端 `types.ts` 改为 `re-export from './schema.gen'`。
- CI 加 `scripts/check-a2ui-schema.ts`（TASK-04 §2 P0-1 已点名）：
  - 读 `schema.gen.ts` 全部 type literal，比对 `A2UIRenderer.tsx` 的 switch case 集合，缺一个就 fail。
  - 比对后端 `Component.type` 字面量集合（pydantic Literal 提取）与前端 union。
- 删除 `frontend/src/components/a2ui/core/A2UIComponentRegistry.ts` 或显式标 `@deprecated`，避免误用。

### 3.2 action 越权防护
- `chat_handlers/a2ui_handler.py:22-29` 的 context 增加 `user_id / org_id / case_id`，并把 `ctx.user` 透传给 `handle_a2ui_event`（`a2ui_intent_handler.py:115` 改签名）。
- 引入 action 签名工具 `backend/src/services/a2ui_signing.py`：
  - 生成：`token = HMAC_SHA256(SECRET, f"{user_id}|{session_id}|{action_id}|{nonce}|{exp}")`，`exp = now + 300`。
  - `a2ui_protocol.py` 工厂统一在构造 `action / actions / submitAction` 时注入 `actionToken`。
  - 校验：`handle_a2ui_event` 入口先调 `verify_action_token(payload.actionToken, expected={user_id, session_id, action_id})`，失败返回 `unsupported` 事件 + 403 埋点。
- 密钥来源：`A2UI_HMAC_SECRET` 环境变量（与 TASK-01 token 密钥隔离）。
- 前端：`A2UIRenderer.tsx` 事件回调原样把 `actionToken` 透传回后端，无须解析。
- pytest 新增 3 case：跨用户、跨 case、过期。

### 3.3 优雅降级
- 前端：在 `A2UIRenderer.tsx:139-141` default 分支返回 `<UnsupportedComponentFallback type={component.type} />`，文案走 i18n key（不允许中文硬编码，TASK-04 §5 护栏），样式 token 化（不动 `design-tokens.ts`）。
- 同时上报 metrics：`window.__a2ui_unknown_component_total++` 或 PostHog event。
- 后端 `a2ui_intent_handler.py:197` 改为返回标准事件：
  ```
  {
    "type": "a2ui_unsupported",
    "original_action": action_id,
    "message": "当前服务不支持此操作，请升级客户端或重试",
    "components": [info_banner(...)],
  }
  ```
  `chat_handlers/a2ui_handler.py:40-41` 改为发送该事件而不是 `return False`，避免污染对话流。
- Prometheus metric：`a2ui_unknown_component_total{type=...}`、`a2ui_unsupported_event_total{action_id=...}`。

### 3.4 协议版本字段
- 在 `a2ui_protocol.py:540` 的 `a2ui_message` 和 `a2ui_protocol.py:599` 的 `a2ui_stream_start` 顶层加 `"protocolVersion": "1.0"`（semver string）。
- 前端 `types.ts:16-30` `A2UIMessage` 加 `protocolVersion?: string`。
- 握手协商：ws 建连时前端首包 `{type:"a2ui_hello", clientVersion:"1.x"}` → 后端按 client 能力降级（拒识别新组件就回退到 `unsupported` 事件）。
- 老客户端 unknown field：明确 union 都用 optional，遵循 "ignore unknown" 协议；新增字段必须 optional + 文档登记到 `docs/audit/04-a2ui/02-issues.md` 兼容矩阵。

---

## 4. 测试方案

后端 pytest（新文件 `backend/tests/test_a2ui_protocol_version.py` + 现有 `test_a2ui_action_coverage.py` 增 case）：
1. `test_action_authz_cross_user`：用 user A 签名的 actionToken 用 user B 提交 → 期望 `unsupported` + 403。
2. `test_action_authz_expired`：构造 `exp` 过期 5min 的 token → 期望拒绝。
3. `test_unknown_action_returns_unsupported_event`：发 `action_id="nonexistent_x"` → 期望返回 `type: a2ui_unsupported`，**不**回退到对话流。
4. `test_protocol_version_negotiation`：client `1.0` 发请求 → 后端返回的 message 不包含 `2.x` 才有的字段（mock 一个 future field）。

前端 e2e（新文件 `frontend/e2e/a2ui-workbench.spec.ts`）：
1. mock ws 推送 `{type:"future-card-2.0"}` → 断言渲染出 fallback 卡片，文案匹配 i18n key，且兄弟节点正常。

### 工时估算

不分次实施，按整包估：
- P0-1 schema 单一源 + CI 脚本：1.0 天（pydantic 重写 + 生成器接入 + check 脚本）。
- P0-2 action HMAC + 越权测试：0.75 天（含密钥环境变量 + 三类 pytest）。
- P0-3 双侧降级 + 埋点：0.5 天（前端 fallback 组件 + 后端 unsupported 事件 + i18n key）。
- P0-4 protocol_version 握手 + 兼容矩阵：0.5 天。
- 联调 + 文档（02-issues / 03-fixes / 04-test-additions / 05-followups）：0.25 天。
- **合计：≈ 3 工程师日**（与 TASK-04 §0 的 2-3 天对齐）。

---

## 6. 风险护栏
- 协议字段改动需要前后端**同步发版**（TASK-04 §5）。每个 P0 单独 commit/PR，描述里列"前后端影响面 + 升级顺序 + 老客户端回退方案"。
- HMAC 密钥从 `A2UI_HMAC_SECRET` 环境变量读取，**不写死**，与 TASK-01 token 密钥隔离。
- 前端 fallback 文案走 i18n，不允许中文硬编码；样式不允许新增 hardcoded color，必须复用 `design-tokens.ts`（不可改）。
- 不动 `chat_service.py / prompt_assembler.py / contract_* / esign_service.py`（其他任务范围）。
- `A2UIComponentRegistry.ts` 这份 dead-code 删除前必须确认没有任何 import；建议先标 `@deprecated` 一个迭代再删。
- 删除已有事件类型属于破坏性变更，本提案不包含删除，仅"加字段 + 加版本"向前兼容。
