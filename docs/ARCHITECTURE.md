# 架构 — 单一真相源

> **状态**：本文是「安心智能助手」架构的**单一权威来源**。
> **版本**：2026-05-14 · V3 P0-P7 + 六层框架 H0-O2 基线后
> **历史来源**：合并自 `docs/v3/architecture.md` + `docs/architecture-v2.md` + `docs/strategy/` 架构章节。原文归档到 [docs/archive/legacy-spine-sources/](archive/legacy-spine-sources/)。
> **更新规则**：架构决策变更时更新。预期年度 1-2 次。每次变更必须追加到 [wiki/06-decision-log.md](wiki/06-decision-log.md)。

---

## 目录

1. [六层 Agent 架构（Harrison Chase 模型）](#1-六层-agent-架构harrison-chase-模型)
2. [多端架构（产品形态）](#2-多端架构产品形态)
3. [4 横 × 4 纵能力矩阵](#3-4-横--4-纵能力矩阵)
4. [三态运行模式](#4-三态运行模式)
5. [V3 vs V2 架构演进](#5-v3-vs-v2-架构演进)
6. [关键流程时序](#6-关键流程时序)
7. [当前实装清单](#7-当前实装清单)
8. [REFERENCES（交叉索引）](#8-references交叉索引)

---

## 1. 六层 Agent 架构（Harrison Chase 模型）

把 Agent 拆成**可独立演化**的 6 层，对应 8 个 Harness 模块 + 上下游基础设施。

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

详细落地见 [docs/audit/harness/README.md](audit/harness/README.md)。

### 1.1 Harness 8 模块职责

| 模块 | 职责 | 主路径接入 |
|---|---|---|
| `enforcement.py` | Harness 主入口 (`run_validation`) | ✅ chat 主路径已接 |
| `trace_context.py` | 请求级 trace 上下文管理 | ✅ |
| `task_engine.py` | 任务状态机（PENDING/RUNNING/VALIDATING/COMPLETED/FAILED/RETRY） | ✅ chat 主路径已接 |
| `cost_tracker.py` | LLM token / 美元消耗追踪 | 🚧 P1 用户配额 |
| `output_validator.py` | Agent 输出质量校验（4 维度） | ✅ via enforcement |
| `policy_engine.py` | 工具调用 / 跨 persona 策略 | 🚧 P0 待统一（当前 `_check_mcp_tool_policy` 在 base.py） |
| `context_engine.py` | 上下文压缩 / 选择 | 🚧 P0 与 compressor 二选一 |
| `tool_registry.py` | 工具注册表 | 🚧 P1 与 Skills 协同 |
| `capability_negotiator.py` | 能力协商（多端） | 🚧 P2 |

---

## 2. 多端架构（产品形态）

```
┌────────────────────────────────────────────────────────────────────┐
│  桌面 (Tauri 2 / Rust Edition 2021)            ⭐ 主战场             │
│  - 系统托盘 / 全局快捷键                                             │
│  - SQLCipher 加密 + OS Keyring                                      │
│  - 本地 LLM（Ollama）                                                │
│  - 桌面 ↔ 移动远控（配对授权 24h）                                  │
│  目录：desktop/                                                      │
├────────────────────────────────────────────────────────────────────┤
│  移动 (Expo 52 / RN 0.76)        ←─→ 远控配对                        │
│  小程序 (Taro 3.6 / 微信)                                            │
│  跨端 (UniApp Vue3)                                                  │
│  目录：mobile/ + mini-program/ + apps/uni-mobile/                    │
├────────────────────────────────────────────────────────────────────┤
│  Web (React 18 / Vite 7 / Tailwind 3)                                │
│  - 10 personas 工作台                                                │
│  - 知识库 / 协作编辑 (Tiptap)                                        │
│  - 后台管理 18 页                                                    │
│  目录：frontend/                                                     │
├────────────────────────────────────────────────────────────────────┤
│  API (FastAPI / SQLAlchemy 2.0 async)                                │
│  - 75 路由 / 61 个 v3 endpoint                                       │
│  - 双客户端（需求方 / 服务方）                                        │
│  - 三态模式（本地 / 混合 / 云端）                                     │
│  - 六层校验：subscription + role + permission + risk + privacy + device │
│  目录：backend/src/api/routes/                                       │
├────────────────────────────────────────────────────────────────────┤
│  Agent 层 (22 personas + 21 specialized)                             │
│  - AgentManager / Team / Worker                                      │
│  - Harness 治理                                                      │
│  - MCP 协议                                                          │
│  目录：backend/src/agents/                                           │
├────────────────────────────────────────────────────────────────────┤
│  数据层                                                              │
│  PostgreSQL · Redis · Qdrant · Neo4j · MinIO · SQLCipher             │
└────────────────────────────────────────────────────────────────────┘
```

### 2.1 桌面（主战场）

- **框架**：Tauri 2（vs Electron — Rust 二进制更小、内存更省）
- **本地数据**：SQLCipher + 文件系统沙箱
- **密钥管理**：OS Keyring（macOS Keychain / Windows Credential Manager）
- **本地 LLM**：Ollama 集成（可选）
- **远控**：作为"主"端，向移动颁发 24h 配对授权
- **签名**：macOS Apple notarization + Windows 代码签名（阻断中）

### 2.2 移动（远控 + 离线）

- **形态**：3 套并行
  - `mobile/` Expo 52 + RN 0.76（主版本）
  - `apps/uni-mobile/` UniApp Vue3（跨端探索）
  - `mini-program/` Taro 3.6 + React（微信小程序）
- **特殊能力**：
  - 配对扫码连接桌面
  - 生物识别（Face ID / 指纹）
  - 推送通知
  - 离线缓存

### 2.3 Web（工作台 + 后台）

- **用户端**：10 personas 工作台 + 知识库 + 协作编辑
- **管理端**：18 页后台（多租户管理 / 计费 / 智能体治理 / 监控）

### 2.4 API（双客户端 + 六层校验）

- **双客户端入口**：需求方（企业老板）/ 服务方（律师顾问）
- **六层校验**：每个 API 请求经 subscription → role → permission → risk → privacy → device

---

## 3. 4 横 × 4 纵能力矩阵

### 3.1 4 横（用户场景）

| 横 | 名称 | Persona |
|---|---|---|
| 1 | 综合协调 | 安心助理 / 流程管家 |
| 2 | 合规经营 | 法律顾问 / 合同管家 / 尽调专家 / 财税顾问 |
| 3 | 增长获客 | 市场研究员 / 获客猎手 / 内容总监 |
| 4 | 出海跨境 | 跨境电商助手 |

### 3.2 4 纵（技术能力）

| 纵 | 名称 | 实装 |
|---|---|---|
| A | 知识检索（RAG） | Qdrant + Neo4j + MinerU 多模态 |
| B | 工具调用（MCP） | `_check_mcp_tool_policy` + Skills 4 office |
| C | 内容生产（Skills） | docx / xlsx / pptx / pdf 4 office skill |
| D | 数据 / 抓取 | FetchService 4 层（HTTP / crawl4ai / HeadlessX / 官方 API） |

### 3.3 矩阵交叉

每个 Persona × 每个 技术能力 = 一个具体落地点。详见 [docs/wiki/04-architecture-map.md](wiki/04-architecture-map.md) + [docs/v3/capability-matrix.md](archive/legacy-spine-sources/v3/capability-matrix.md)（归档）。

---

## 4. 三态运行模式

| 模式 | 数据出设备 | LLM 位置 | 验证点 | 适用场景 |
|---|---|---|---|---|
| **本地** | ❌ 不出 | Ollama 本地 | SQLCipher + TopSecret guard | 高敏感（合同 / 法务 / 政府） |
| **混合** | ✅ 脱敏后 | 云端 + 本地协同 | privacy_context 8 类 PII scrub | 一般业务 |
| **云端** | ✅ 全云 | 云端 LLM | 用户**显式同意** + 审计 | 通用助手 |

### 4.1 切换机制

```
用户请求
  → privacy_context 评估请求级隐私
  → 若 risk_level = HIGH → 强制本地模式（覆盖用户偏好）
  → 否则按用户偏好（默认混合）
  → device_capability 校验（本地模式需 Ollama 可用）
  → 路由到对应 LLM provider
```

### 4.2 实现位置

- `backend/src/services/privacy_context.py` — 评估
- `backend/src/services/llm_router.py` — 路由
- `desktop/src-tauri/src/privacy_gate.rs` — 桌面边界

---

## 5. V3 vs V2 架构演进

### 5.1 7 项关键升级

| 项 | V2（安心法务） | V3（安心智能助手） | 决策 |
|---|---|---|---|
| 1 | 法律垂直 | 全链路（法 + 财 + 增 + 跨境） | 市场扩展 |
| 2 | Web 主战场 | 桌面主战场 | 本地隐私 + 远控 |
| 3 | CAMEL-AI 框架 | 自研 Harness 层 | 解锁 litellm 升级 |
| 4 | 单 chat 入口 | 10 personas 工作台 | 多场景协同 |
| 5 | 横向加 persona | 六层框架纵向建能力 | 可演化治理 |
| 6 | output_validator 软警告 | CRITICAL 拒发 + retry | 质量门禁 |
| 7 | trace 仅内存 | 持久化 + PII scrub + cluster | 失败可追溯 |

### 5.2 升级路径

V2 → V3 的完整路径见 [docs/adr/001-v3-anxin-assistant-upgrade.md](adr/001-v3-anxin-assistant-upgrade.md)。

---

## 6. 关键流程时序

### 6.1 聊天主路径（H1 enforcement 已接入）

```
Client
  ↓ POST /api/v3/chat
api/routes/chat.py
  ↓
services/chat_service.py
  ↓
  ├─ task_engine.create(PENDING) → trace_context.start()
  ↓
  ├─ AgentManager.route(persona) → BaseAgent._init_agent (LiteLLM)
  ↓
  ├─ task_engine.transition(RUNNING)
  ↓
  ├─ Agent.invoke(prompt) → LLM response
  ↓
  ├─ task_engine.transition(VALIDATING)
  ↓
  ├─ harness.enforcement.run_validation(response)
  │    ├─ output_validator.validate (4 维度)
  │    └─ if CRITICAL → reject
  │       if FAIL → retry
  │       if WARN → pass with mark
  ↓
  ├─ trace_sink.persist (PII scrub + cluster_id)
  ↓
  ├─ task_engine.transition(COMPLETED|FAILED|RETRY)
  ↓
ChatResponse {
  content,
  memory_id,
  harness: { trace_id, tokens, validation_action }
}
```

文件：[backend/src/services/chat_service.py](../backend/src/services/chat_service.py)

### 6.2 异步任务（TaskOrchestrator）

```
POST /api/v3/agent_tasks/submit
  → Celery enqueue → Redis broker
  → TaskOrchestrator.pick (worker)
  → Persona.invoke
  → task_engine 状态机
  → 客户端：GET /agent_tasks/{id} 轮询 或 SSE
```

### 6.3 OAuth 应用授权

```
GET /providers              → 列 5 provider 元数据
POST /authorize/{provider}  → 跳转 provider OAuth
GET /callback/{provider}    → exchange code → Fernet 加密 token_store
```

### 6.4 桌面远控配对

```
桌面：generate_pairing_code() → 24h TTL
移动：scan QR → POST /im_pairing/confirm
后端：colocate device fingerprints → issue auth token
建立 WebSocket 通道
```

### 6.5 RAG 查询链路

```
POST /api/v3/rag_query
  → 检索（Qdrant 向量 + Neo4j KG）
  → MinerU 多模态解析（如有）
  → VLM 重排（如启用）
  → 引用链路（来源 + 段落 + page）
  → ChatResponse with sources
```

---

## 7. 当前实装清单

### 7.1 已实装（V3 P0-P7 + Harness H0-O2 ✅）

| 域 | 实装 |
|---|---|
| API endpoint | 61 v3 endpoint |
| Persona | 10 用户可见 + 22 内部 |
| Specialized agent | 21 |
| 异步任务 | TaskOrchestrator + Celery |
| OAuth | 5 provider + Fernet 加密 |
| IM | 飞书真接入 + 4 占位 + 配对授权 |
| Skills 运行时 | watchdog 热加载 + 4 office skill |
| FetchService | 4 层 + 5 法律源 + 5 电商源 |
| RAG | Qdrant + Neo4j + MinerU 多模态 |
| 六层框架 | H0-O2 + H1 |
| 数据栈 | PG / Redis / Qdrant / Neo4j / MinIO / SQLCipher |

### 7.2 规划中（P8-P13）

详见 [ROADMAP.md](ROADMAP.md)。

---

## 8. REFERENCES（交叉索引）

| 主题 | 文档 | 用途 |
|---|---|---|
| **Agent 行为** | [AGENTS.md](../AGENTS.md) | 22 Agent 红线 / 路由 / 反 slop / 协作约定（运行时单一真相源） |
| **视觉 / UI** | [DESIGN.md](../DESIGN.md) | 设计 token / 组件 / 图标体系（设计单一真相源） |
| **六层框架** | [docs/audit/harness/README.md](audit/harness/README.md) | H0-O2 落地审计 |
| **Harness H1 followups** | [docs/audit/harness/03-h1-followups.md](audit/harness/03-h1-followups.md) | P0-P2 后续任务 |
| **Context 三层** | [docs/context-architecture.md](context-architecture.md) | AGENTS / skills / memory 加载顺序 |
| **Skills** | [skills/_template/](../skills/_template/) | Skill 开发骨架 |
| **API 设计** | [docs/standards/api-design.md](standards/api-design.md) | REST / WS / SSE 规范 |
| **数据库** | [docs/standards/database-standard.md](standards/database-standard.md) | Schema / ORM / 迁移 / 多租户 |
| **前端** | [docs/standards/frontend-standard.md](standards/frontend-standard.md) | React / RN / Taro / UniApp 四端 |
| **桌面设计** | [docs/desktop/](desktop/) | 同步引擎 / 窗口 / SQLCipher 策略 |
| **移动设计** | [docs/mobile/](mobile/) | UniApp 迁移 / 错误处理 |
| **设计 Token** | [docs/design/cross-platform-token-drift.md](design/cross-platform-token-drift.md) | 跨端 token 漂移跟踪 |

---

## 附录 · 归档与原文

- **原 v3/architecture.md（321 行）**：[docs/archive/legacy-spine-sources/v3/architecture.md](archive/legacy-spine-sources/v3/architecture.md)
- **原 architecture-v2.md（354 行）**：[docs/archive/legacy-spine-sources/architecture/architecture-v2.md](archive/legacy-spine-sources/architecture/architecture-v2.md)
- **strategy 架构章节**：[docs/archive/legacy-spine-sources/strategy/](archive/legacy-spine-sources/strategy/)
- **5 篇 architecture 深度文档**：[docs/architecture/](architecture/)（object-storage / UI-UX 优化 / hybrid 硬件隐私 / 内存进化）

---

> **维护提示**：架构决策变更必须先追加到 [wiki/06-decision-log.md](wiki/06-decision-log.md)，再更新本文。
