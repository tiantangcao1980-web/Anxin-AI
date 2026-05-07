# 提案：A2UI Action 越权批量修复

> 任务范围：TASK-04 P0-2「action 调用越权」
> 前置：`PROPOSAL-action-coverage.md` 第 2.2 节已确认 payload 全裸、无签名、无 `user_id` 透传
> 引用格式：`relative/path:line`
> 仅盘点 + 设计方案，不改代码

## 1. 当前 action 调用方清单（影响面）

### 1.1 后端入站
| 调用方 | 文件:行号 | 备注 |
|---|---|---|
| WS 顶层路由 | `backend/src/api/routes/chat.py:525` | `websocket_chat(ws, session_id)` **没有 `Depends(get_current_user_required)`**，整个 WS 通道无认证用户 |
| WS 分发 | `backend/src/api/routes/chat.py:595-599` | `if msg_type == "a2ui_event": handle_a2ui_event(ctx, data)` |
| Handler 适配 | `backend/src/api/routes/chat_handlers/a2ui_handler.py:8-45` | 入口函数，把 `data` 直接拆给 service |
| Service 派发 | `backend/src/services/a2ui_intent_handler.py:115-198` | `handle_a2ui_event(action_id, component_id, payload, form_data, context)`，13 条 `if action_id == ...` |
| `__init__` 暴露 | `backend/src/api/routes/chat_handlers/__init__.py:14,22` | 仅 re-export |

### 1.2 前端出站（唯一 emitter）
| 调用方 | 文件:行号 | 备注 |
|---|---|---|
| WS 发送 | `frontend/src/pages/Chat.tsx:1735-1742` | 唯一一处 `wsRef.send({type:'a2ui_event', action_id, component_id, payload, form_data})` |
| 过期校验 | `frontend/src/components/a2ui/A2UIRenderer.tsx:154-164` | 仅有 `message.metadata.expiresAt` 软校验，纯客户端可绕过 |
| 自然语言映射 | `frontend/src/components/chat/a2uiActionMap.ts:25,31` | 部分 action（`view_case_detail` / `select_doc_type`）走对话流，不经 `a2ui_event` |

### 1.3 上下文实际可用字段
- `WebSocketContext.__init__`：`session_id`、`conversation_id`、`workforce`（`backend/src/api/routes/chat_handlers/context.py:88-104`）。
- **没有 `user_id`、`case_id`、`org_id`** 字段。`chat.py:1251` 写过 `ctx.user_id`，实际是 `AttributeError`，被 try/except 静默吞。
- `handle_a2ui_event` 注入 context 仅 `{"conversation_id": ctx.conversation_id}`（`a2ui_handler.py:28`）。

> 影响面合计：**1 个前端 emitter + 5 个后端节点**。无第三方 / 移动端 / SDK 调用，可见所有调用都在仓内，整体改造可控。

## 2. 每个 action 的 payload 业务 ID 字段

| action_id | 业务 ID 字段 | 取值来源 | 后端引用 |
|---|---|---|---|
| `contact_lawyer` | `payload.lawyerId` | 服务端 `lawyer_card` 注入 | `a2ui_intent_handler.py:330` |
| `view_lawyer_detail` | `payload.lawyerId` | 同上 | `a2ui_intent_handler.py:526` |
| `select_service` | `payload.serviceId` | 服务端 `service_selection` 注入 | `a2ui_intent_handler.py:380` |
| `submit_engagement` | `form_data.case_type/urgency/description/contact_method` | 用户表单 | `a2ui_intent_handler.py:438` |
| `confirm_engagement` | `payload`（当前为空，仅 generate UUID） | — | `a2ui_intent_handler.py:489` |
| `start_due_diligence` | `form_data.company_name/investigation_scope/purpose` | 用户表单 | `a2ui_intent_handler.py:723` |
| `select_doc_type` | `payload.serviceId` 或 `payload.docType` | 服务端注入 | `a2ui_intent_handler.py:956` |
| `view_engagement_detail` | `payload`（当前空） | — | `a2ui_intent_handler.py:1093` |
| `assess_*_risk`、`go_back`、`cancel_engagement`、`view_more_lawyers`、`ai_match_lawyer`、`find_lawyer`、`paste_contract`、`browse_templates`、`view_full_report`、`ai_suggestions`、`upload_contract`、`start_review` | 无业务 ID | — | — |

协议层注入业务 ID 的工厂位置：
- `a2ui_protocol.py:75` `lawyer_card → data.lawyerId`
- `a2ui_protocol.py:334` `contract_preview → data.contractId`
- `a2ui_protocol.py:712` `case_progress → data.caseId`
- `a2ui_stream.py:125,141` `make_lawyer_card → data.lawyerId` 与 `data.action.payload.lawyerId`

> 关键观察：`lawyerId` 当前是从 `MOCK_LAWYERS`（`a2ui_intent_handler.py:205-251`）写死的字符串，没有"用户—律师"绑定关系；`form_data` 里完全没有 `lawyerId`，意味着「确认委托」走到后端时**已经无法对应任何具体律师**，只是生成新的 `ENG-xxxx`。

## 3. 越权场景示例

### 3.1 跨用户跨案件下单
1. 攻击者 A 登录正常账户，从浏览器开发者工具拿到自己 WS 连接。
2. 直接构造 `{type:"a2ui_event", action_id:"confirm_engagement", payload:{lawyerId:"lawyer-001"}, form_data:{}}`，连续刷 1k 次。
3. 后端 `_handle_confirm_engagement(payload, context)` 不校验 `payload.lawyerId` 是否在 A 可访问范围，全部返回成功状态卡 + 新 `ENG-xxxx`，导致律师端被刷单/黑名单律师被滥用。

### 3.2 跨会话伪造 conversation_id
- WS 顶层 `chat.py:525` 用前端传入的 `session_id` 直接当 `conversation_id`（`chat.py:556-568`），并未与登录用户绑定。
- 攻击者从他人浏览器 / 日志中拿到任意 `conversation_id`，直连 `/api/chat/ws/{session_id}`，无 token、无 cookie、无 origin 校验即可恢复别人对话上下文，并继续触发 a2ui action。

### 3.3 触发已过 ttl 的 action
- 唯一过期校验在 `A2UIRenderer.tsx:157`，且依赖 `message.metadata.expiresAt`（后端目前没注入此字段，见 `a2ui_protocol.py:540-566`，故事实上**永不过期**）。
- 攻击者保留半年前的 `lawyerId/payload`，照样可重放 `contact_lawyer` 进入服务选择流。

### 3.4 表单越权
- `submit_engagement` 的 `form_data.description` 长度无上限校验（`a2ui_intent_handler.py:468`），可塞 LLM prompt-injection 给"委托管理 Agent"。

## 4. 设计方案：HMAC + nonce + ttl + user_id 绑定

### 4.1 服务端发签
新增 `backend/src/services/a2ui_signing.py`：

```python
def sign_action(*, user_id, session_id, action_id, scope=None, ttl=300):
    nonce = secrets.token_urlsafe(8)
    exp = int(time.time()) + ttl
    body = f"{user_id}|{session_id}|{action_id}|{scope or ''}|{nonce}|{exp}"
    sig = hmac.new(SECRET, body.encode(), sha256).hexdigest()
    return {"v": 1, "uid": user_id, "sid": session_id, "aid": action_id,
            "scope": scope, "nonce": nonce, "exp": exp, "sig": sig}

def verify_action(token, *, expected_user_id, expected_session_id, expected_action_id):
    # 1) v 必须为 1；2) exp 未过期；3) uid/sid/aid 与 expected 全等；
    # 4) HMAC 重算一致；5) nonce 不在重放黑名单（Redis SETEX ttl=600s）
```

- 密钥：`A2UI_HMAC_SECRET` 环境变量（与 TASK-01 token secret 隔离）。
- nonce 黑名单：Redis `SETNX a2ui:nonce:{nonce} 1 EX 600`，写失败即拒绝（重放）。
- `scope` 用于 `lawyerId / caseId / contractId / engagementId` 这类业务实体粘合。

### 4.2 工厂统一注入 `actionToken`
所有协议工厂在生成 `action / actions / submitAction / cancelAction` 时，**必须**走一个新的 helper：

```python
def make_action(label, action_id, *, ctx, payload=None, scope=None, variant="primary"):
    token = sign_action(user_id=ctx.user_id, session_id=ctx.session_id,
                        action_id=action_id, scope=scope)
    return {"label": label, "actionId": action_id, "payload": payload or {},
            "actionToken": token, "variant": variant}
```

- 升级位点：`a2ui_protocol.py` 工厂里所有 `action=`/`actions=`/`submit_action=`/`cancel_action=` 注入处（`recommendation_card:51`、`lawyer_card:90`、`order_card:177`、`status_card:229` 等 25+ 处）。
- `a2ui_stream.py:138-142` 默认 action 同步改造。

### 4.3 入站校验
- `WebSocketContext` 增加 `user_id: str | None`、`case_id: str | None`，由 WS handshake 阶段注入。
- WS handshake 鉴权：`chat.py:525` 改用 `Cookie / Sec-WebSocket-Protocol / query?token=` 三选一，复用 REST 同款 `decode_access_token`。无效 token 直接 `await websocket.close(code=4401)`。
- `chat_handlers/a2ui_handler.py:23-29` 改为：
  ```python
  token = data.get("action_token")
  if not verify_action(token, expected_user_id=ctx.user_id,
                       expected_session_id=ctx.session_id,
                       expected_action_id=a2ui_action_id):
      await ctx.send("a2ui_unsupported", {...code:"AUTHZ_FAIL"...}); return True
  ```
- `handle_a2ui_event` 签名改为 `(action_id, component_id, payload, form_data, *, ctx)`，内部访问 `ctx.user_id / ctx.case_id`（**破坏性签名变更**，参见 §5 兼容期方案）。

### 4.4 业务粘合校验
- `lawyerId / caseId / contractId / engagementId` 这类 `scope` 字段，单独再做一次"是否属于当前用户"DB 查询：
  - `lawyerId`：v1.1 接 `lawyer_profiles` 表后做"该律师是否对该用户开放"。当前 MOCK 期可放行但记 audit log。
  - `caseId / engagementId`：查 `cases.user_id == ctx.user_id`。
  - `contractId`：查 `contracts.owner_id == ctx.user_id`。
- 命中即放行，否则返回标准 `a2ui_unsupported` 事件（与 P0-3 共用降级通道）。

## 5. 兼容期方案（旧 action 至少 1 周仍接受 + warning log）

### 5.1 阶段策略
| 阶段 | 时间 | 服务端行为 | 前端行为 |
|---|---|---|---|
| T0：双写 | 第 1 周 | 工厂注入 `actionToken`；handler 校验 token，**缺失/失败** → `logger.warning + audit_log(reason)`，仍按旧逻辑放行 | 透传 `actionToken`（payload + form_data 同位） |
| T1：硬开关 | 第 2 周 | `A2UI_ENFORCE_AUTHZ=true` 后缺 token / 校验失败直接拒绝（返回 `a2ui_unsupported` + code `AUTHZ_FAIL`） | 同上，UI 不变 |
| T2：清理 | 第 3 周 | 移除兼容分支；nonce 黑名单 SLO 监控 | 移除 fallback "[A2UI操作]" 文本兜底（`Chat.tsx:1745`） |

### 5.2 兼容期日志结构
```
event=a2ui_action_legacy  user=<uid|anon>  action=<aid>  reason=<missing_token|expired|sig_mismatch|cross_user|cross_session>  conversation=<cid>
```
按 `reason` 维度埋点 `a2ui_action_legacy_total{reason=...}`，T1 切换前要求 `missing_token` 比例 < 1%。

### 5.3 老前端如何不挂
- T0 期：服务端兼容缺 `actionToken`；老前端继续 work。
- T1 期：在前端发版（Chat.tsx）后再开 `A2UI_ENFORCE_AUTHZ`。前端版本号通过 P0-4 协议握手 `clientVersion` 协商：`<1.1` 走兼容、`>=1.1` 强制。

## 6. 测试矩阵

新增 `backend/tests/test_a2ui_action_authz.py`（pytest 标记 `-k a2ui_action_authz`）：

| 用例 | 输入 | 期望 |
|---|---|---|
| `test_legit_action_passes` | A 用 A 的 token 提交 | 200 + 业务卡片 |
| `test_missing_token_in_enforce_mode` | `A2UI_ENFORCE_AUTHZ=true` + 无 token | `a2ui_unsupported` code=`MISSING_TOKEN` |
| `test_expired_token` | 构造 `exp=now-10` | code=`EXPIRED` |
| `test_cross_user_token` | A 的 token 用 B 的 ws | code=`USER_MISMATCH` |
| `test_cross_session_token` | A 旧 session 的 token 在新 session 提交 | code=`SESSION_MISMATCH` |
| `test_replay_nonce` | 同一 token 提交两次 | 第二次 code=`REPLAY` |
| `test_signature_tamper` | 改 1 byte | code=`SIG_MISMATCH` |
| `test_scope_mismatch` | `lawyerId=lawyer-001` 但 token.scope=`lawyer-002` | code=`SCOPE_MISMATCH` |
| `test_legacy_compat_mode` | `A2UI_ENFORCE_AUTHZ=false` + 无 token | 200 + warning log + `a2ui_action_legacy_total++` |

E2E `frontend/e2e/a2ui-workbench.spec.ts`：覆盖"过期 token → 显示降级提示卡，不影响兄弟节点"。

## 7. 工时估算

| 工作项 | 估算 |
|---|---|
| `a2ui_signing.py` + 单测 + Redis nonce | 0.4 天 |
| WS handshake 加 token / cookie 鉴权 + `WebSocketContext.user_id/case_id` | 0.3 天 |
| `make_action` helper + 25+ 工厂改造 + `a2ui_stream.py` 默认 action | 0.4 天 |
| `handle_a2ui_event` 改签名 + 兼容期双轨 + audit log | 0.3 天 |
| 业务粘合校验（lawyer/case/contract/engagement DB 查询） | 0.2 天 |
| 越权 9 条 pytest + e2e 1 条 | 0.3 天 |
| 兼容期监控 / 文档（02-issues / 03-fixes / 05-followups） | 0.2 天 |
| **合计** | **约 2.1 工程师日** |

> 与 `PROPOSAL-action-coverage.md` §4 中 P0-2 给的 0.75 天差别：那份只覆盖了「HMAC 工具 + 三类越权 pytest」，未含"WS handshake 鉴权 + WebSocketContext 重构 + 25+ 工厂注入 + 兼容期双轨"这四块的实施。本提案为整包估。

## 8. 风险护栏

- **不动**：`backend/src/services/chat_service.py`、`prompt_assembler.py`、`contract_*`、`esign_service.py`（任务 3/5 范围）；`frontend/src/lib/design-tokens.ts`。
- **HMAC 密钥**：`A2UI_HMAC_SECRET` 环境变量，启动时缺失则 fail-fast；与任务 1 的 token secret 隔离；预生产/生产用不同 secret。
- **WS handshake 改鉴权**是破坏性变更，必须前后端同发；老 ws 连接保留 1 周宽限期，灰度先开 5% 流量观察 4xx 比例。
- **nonce 黑名单**走 Redis；Redis 不可用时降级到内存 LRU（仅本进程，记 warning），避免单点导致全量阻断。
- **MOCK_LAWYERS** 阶段 `lawyerId` 校验只能记 audit log 不阻断；接入 `lawyer_profiles` 表后再开实校验，避免误伤当前用户。
- **`actionToken` 不进数据库 / 不进对话历史**：保存消息时（`a2ui_handler.py:32-33`）剥离 token 字段，只留 `action_id`，避免 token 泄漏到 `messages.content`。
- **签名失败的卡片不能消失**：拒绝时只发 `a2ui_unsupported` 事件，前端兄弟卡片继续显示，避免整片工作台抽掉（与 P0-3 共用渲染降级路径）。
- **审计日志独立**：`audit_log` 表新增 `kind=a2ui_action_authz`，记录 `reason / user_id / action_id / scope / nonce`；保留 90 天供合规复核。
- 每个改造单独 commit/PR：`(1)` signing 工具 + 单测 → `(2)` WS handshake 鉴权 → `(3)` 工厂注入 + 前端透传 → `(4)` enforce 开关 + e2e。每个 PR 描述列「前后端影响面 + 升级顺序 + 老客户端回退方案」。
