---
name: 架构地图
description: 架构 6 层视图 + 关键文件路径速查
audience: AI agents · 写代码前必读
last_updated: 2026-05-14
---

# 04 · 架构地图

> 写代码前先看架构。完整描述在 [docs/ARCHITECTURE.md](../ARCHITECTURE.md)，本文是**带文件路径的速查版**。

---

## 6 层架构（Harrison Chase 模型）

```
┌────────────────────────────────────────────────────────────────────┐
│ L5  OPS    PR Gate / CI / Self-Heal / On-call                      │
│            .github/workflows/ + scripts/self_heal/                  │
├────────────────────────────────────────────────────────────────────┤
│ L4  EVAL   25 case × 4 维度 + baseline + PR compare                │
│            backend/evals/                                           │
├────────────────────────────────────────────────────────────────────┤
│ L3  TRACES PII scrub (8 类) + cluster_id + trace→test              │
│            backend/src/services/trace_sink.py                       │
│            backend/scripts/trace_to_test/                           │
├────────────────────────────────────────────────────────────────────┤
│ L2  CONTEXT AGENTS.md / skills/ / memory 三层加载                  │
│             AGENTS.md + skills/_template/ + docs/context-architecture.md │
├────────────────────────────────────────────────────────────────────┤
│ L1  HARNESS 8 模块骨架                                              │
│             backend/src/harness/                                    │
│             ├─ enforcement.py     (主入口，已接 chat)              │
│             ├─ trace_context.py                                     │
│             ├─ task_engine.py                                       │
│             ├─ cost_tracker.py                                      │
│             ├─ output_validator.py                                  │
│             ├─ policy_engine.py    (P0 待主路径接入)                │
│             ├─ context_engine.py   (P0 与 compressor 二选一)        │
│             ├─ tool_registry.py    (P1 待与 C2 协同改造)            │
│             └─ capability_negotiator.py (P2 待统一)                 │
├────────────────────────────────────────────────────────────────────┤
│ L0  MODEL  LiteLLM 统一封装                                         │
│            OpenAI / Anthropic / 通义 / 混元 / DeepSeek / Ollama     │
└────────────────────────────────────────────────────────────────────┘
```

详见 [docs/audit/harness/README.md](../audit/harness/README.md)。

---

## 多端架构（产品形态）

```
┌──────────────────────────────────────────────────────────────┐
│  桌面 (Tauri 2 / Rust Edition 2021)            ⭐ 主战场       │
│  - 系统托盘 / 全局快捷键                                       │
│  - SQLCipher 加密 + OS Keyring                                │
│  - 本地 LLM（Ollama）                                          │
│  - 桌面 ↔ 移动远控（配对授权 24h）                            │
│  目录：desktop/                                                │
├──────────────────────────────────────────────────────────────┤
│  移动 (Expo 52 / RN 0.76)        ←─→ 远控配对                  │
│  小程序 (Taro 3.6 / 微信)                                      │
│  跨端 (UniApp Vue3)                                            │
│  目录：mobile/ + mini-program/ + apps/uni-mobile/              │
├──────────────────────────────────────────────────────────────┤
│  Web (React 18 / Vite 7 / Tailwind 3)                          │
│  - 10 personas 工作台                                          │
│  - 知识库 / 协作编辑 (Tiptap)                                  │
│  - 后台管理 18 页                                              │
│  目录：frontend/                                               │
├──────────────────────────────────────────────────────────────┤
│  API (FastAPI / SQLAlchemy 2.0 async)                          │
│  - 75 路由 / 61 个 v3 endpoint                                 │
│  - 双客户端（需求方 / 服务方）                                  │
│  - 三态模式（本地 / 混合 / 云端）                              │
│  - 六层校验：subscription + role + permission + risk + privacy + device │
│  目录：backend/src/api/routes/                                 │
├──────────────────────────────────────────────────────────────┤
│  Agent 层 (22 personas + 21 specialized)                       │
│  - AgentManager / Team / Worker                                │
│  - Harness 治理                                                │
│  - MCP 协议                                                    │
│  目录：backend/src/agents/                                     │
├──────────────────────────────────────────────────────────────┤
│  数据层                                                        │
│  PostgreSQL · Redis · Qdrant · Neo4j · MinIO · SQLCipher       │
└──────────────────────────────────────────────────────────────┘
```

---

## 三态运行模式

| 模式 | 数据出设备 | LLM 位置 | 适用场景 | 验收点 |
|---|---|---|---|---|
| **本地** | ❌ 不出 | Ollama 本地 | 高敏感（合同/法务） | SQLCipher + TopSecret guard |
| **混合** | ✅ 脱敏后 | 云端 + 本地协同 | 一般业务 | privacy_context 8 类 scrub |
| **云端** | ✅ 全云 | 云端 LLM | 通用助手 | 用户显式同意 |

实现：`backend/src/services/privacy_context.py` + 桌面 `desktop/src-tauri/` 隐私门。

---

## 关键流程速查

### 1. 聊天主路径（H1 enforcement 已接入）

```
POST /api/v3/chat
  → routes/chat.py
  → services/chat_service.py
  → AgentManager.route(persona)
  → BaseAgent._init_agent() (LiteLLM)
  → output_validator (now: harness.enforcement.run_validation)
  → trace_sink (PII scrub + cluster_id)
  → task_engine.transition (state machine)
  → ChatResponse {content, harness: {trace_id, tokens, validation_action}}
```

文件：[backend/src/services/chat_service.py](../../backend/src/services/chat_service.py)

### 2. 异步任务（TaskOrchestrator）

```
POST /api/v3/agent_tasks/submit
  → Celery enqueue
  → TaskOrchestrator pick
  → Persona agent invoke
  → 状态机：PENDING → RUNNING → VALIDATING → COMPLETED|FAILED|RETRY
  → 客户端：GET /agent_tasks/{id} 轮询 或 SSE
```

### 3. OAuth 应用授权

```
GET /api/v3/app_authorizations/providers   ← 列 5 provider
POST /authorize/{provider}                 ← 跳转 OAuth
GET /callback/{provider}                   ← Fernet 加密存储 token
```

### 4. 桌面远控配对授权

```
桌面发起 → 24h 限时配对码
  → 移动扫码确认
  → /api/v3/im_pairing/* 颁发授权 token
  → WebSocket 通道建立
```

### 5. RAG 查询链路

```
POST /api/v3/rag_query
  → 检索（Qdrant 向量 + Neo4j KG）
  → MinerU 多模态解析（如有）
  → VLM 重排（如启用）
  → 引用链路（来源 + 段落）
```

---

## 关键数据模型（必须了解）

| 模型 | 文件 | 用途 |
|---|---|---|
| `User / Tenant` | `backend/src/models/user.py` | 用户多租户 |
| `AgentTask` | `backend/src/models/agent_task.py` | 异步任务状态机 |
| `Conversation / Message` | `backend/src/models/chat.py` | 聊天历史 |
| `AppAuthorization` | `backend/src/models/app_authorization.py` | OAuth token |
| `IMPairing` | `backend/src/models/im_pairing.py` | 远控配对 |
| `Skill / SkillConnector` | `backend/src/models/skill*.py` | Skills 注册表 |
| `Trace` | `backend/src/models/trace.py` | Agent 执行轨迹 |
| `KnowledgeBase / Document` | `backend/src/models/kb*.py` | RAG 知识库 |

---

## CI / Gate（L5 Ops）

| Workflow | 用途 | 文件 |
|---|---|---|
| `backend-ci.yml` | 后端 ruff/mypy/pytest | `.github/workflows/` |
| `frontend-ci.yml` | 前端 lint/build/vitest | 同上 |
| `desktop-ci.yml` | cargo clippy + test | 同上 |
| `mobile-ci.yml` | RN typecheck + smoke | 同上 |
| `ai-review.yml` | 4 reviewer 并行（code/security/dep/regression）| 同上 |
| `release-gate.yml` | 商业门禁脚本 | `scripts/commercial-readiness-gate.sh` |
| `eval-baseline.yml` | 25 case eval + baseline compare | `backend/evals/` |
| `nightly-smoke.yml` | 每夜 smoke | 同上 |

---

## 跨平台共享设计

- **图标**：所有平台统一从 `@/lib/icons` 导入（vs `from 'lucide-react'`），P0 待收口
- **设计 Token**：`docs/design/cross-platform-token-drift.md` 跟踪四端漂移
- **API 客户端**：每端各自 `src/lib/api/`，schema 由 OpenAPI 生成
- **错误处理**：参考 `docs/mobile/error-handling-guidelines.md`

---

## 我要写代码时该读哪里？

| 我要做什么 | 先读什么 |
|---|---|
| 加 API 路由 | `docs/standards/api-design.md` + `backend/src/api/routes/` 模仿一个 |
| 加 Agent | `docs/standards/backend-standard.md` §Agent + `skills/_template/` |
| 加前端页面 | `docs/standards/frontend-standard.md` + `frontend/src/pages/` 模仿一个 |
| 改桌面 | `desktop/src-tauri/` + `docs/desktop/` |
| 改数据库 | `docs/standards/database-standard.md` + 注意 alembic 双 head |
| 加测试 | `docs/standards/testing-standard.md` |
| 安全相关 | `docs/standards/security-standard.md` + 不要绕过 `_check_mcp_tool_policy` |
