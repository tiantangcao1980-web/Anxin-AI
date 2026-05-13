# 安心智能助手 V3 — 系统架构总览

> **一句话定位**：一个 App 搞定 法务 / 税务 / 财务 / 公司过程管理 / 调研获客 / 内容产出 / 出海跨境的「中国制造业全链路智能经营助理」。

> **目标用户**：成长型制造企业（10–500 人），决策者 + 业务一号位 + 总经办 + 销售 + 跨境运营。

> **实装进度（2026-04-27）**：P0–P7 已落地 — 31 commits / 61 v3 API endpoint / 543+ pytest / 5 personas 实装。

相关文档：[AGENT_PERSONAS](./AGENT_PERSONAS.md) · [CAPABILITY_MATRIX](./CAPABILITY_MATRIX.md) · [ROADMAP](./ROADMAP.md) · [INTEGRATIONS](./INTEGRATIONS.md) · [SKILLS_INVENTORY](./SKILLS_INVENTORY.md) · [V3_DELIVERY_SUMMARY](./V3_DELIVERY_SUMMARY.md)

---

## 1. 整体架构（分层视图）

```
┌──────────────────────────────────────────────────────────────────────┐
│  L0  接入层（Where users live）                                      │
│  桌面 (Tauri) │ 移动 (Expo RN) │ 小程序 (Taro) │ Web │ IM 通道       │
│                                              飞书 / 钉钉 / 企微 / Slack │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────────┐
│  L1  Persona 层（10 个 user-facing 智能体 / 5 ✅ 实装 + 5 🚧）       │
│  ✅ 流程 / 市场 / 获客 / 内容 / 出海   🚧 助理 / 法律 / 合同 / 尽调 / 财税 │
│  统一注册：PersonaRegistry — backend/src/agents/personas/registry.py  │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────────┐
│  L2  编排层 ✅ TaskOrchestrator (P2)                                 │
│   • 同步对话    • 异步任务（Codex/Dispatch 风格）                    │
│   • Celery + Redis worker / state_machine / events                  │
│   • SandboxExecutor (P3): LocalProvider ✅ + Docker/E2B/Codex 占位  │
│   • IM Gateway (P3): 飞书真 + 钉钉/企微/Slack/Telegram adapter      │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────────┐
│  L3  专业 Agent 层（21 个 specialized agents — 现有，沿用）         │
│  legal_advisor / legal_researcher / contract_reviewer / ...          │
│  compliance_officer / risk_assessor / tax_compliance / due_diligence │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────────┐
│  L4  能力层（4 横通用能力 × Skills 运行时）                          │
│  ① 信息获取 ✅ FetchService 4 层 (L1-L4: HTTP/crawl4ai/HeadlessX/API) │
│  ② 调研分析  ③ 设计开发  ④ 销售决策                                │
│  ✅ Skills 运行时 (P5): skill_registry + skill_executor + 6 API     │
│  ✅ 4 office skill (cowork-anthropic 兼容): docx/xlsx/pptx/pdf      │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────────┐
│  L5  集成层（OAuth 应用市场） ✅ P4 框架 + 5 provider               │
│  办公协作 ✅飞书/✅钉钉 │ 文档 ✅Notion │ 跨境 ✅Shopify+🟡4mock     │
│  CRM 🚧 │ 法务 🟡数据源已接 │ 信息源 🚧 │ 财税 🚧 │ 设计 🚧         │
└──────────────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────────────┐
│  L6  数据 + 模型 + 学习层                                            │
│  RAG-Anything (HKUDS) + MinerU 多模态  🚧 P10                       │
│  Evolver (EvoMap) 学习闭环 + 引文追踪  🚧 后续                     │
│  本地 / 混合 / 云端 三态运行模式（继承 V2 ✅）                       │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 4 横 × 4 纵能力矩阵（鸟瞰图）

| 业务域 ↓ / 通用能力 → | ① 信息获取 | ② 调研分析 | ③ 设计开发 | ④ 销售决策 |
|---|---|---|---|---|
| 🛡 **合规经营**（法/税/财/管理） | 法规 / 公告抓取 | 合同 / 财报分析 + 引文 | 合同模板 / 流程画布 | 风险评级 / 决策建议 |
| 📈 **增长获客**（调研/获客/推广/内容） | 竞品 / 行业资讯抓取 | 市场分析 + 趋势挖掘 | 海报 / 落地页 / 短视频 | Vibe Selling 销售助手 |
| 🌍 **出海跨境**（全链路） | 平台数据 / 海关 / 政策 | 选品 / 关键词 / 受众 | 独立站 / 商品页 / 素材 | 投放 ROI / 多 agent 决策 |
| 🎯 **综合协调** | 跨域信息聚合 | 跨域 RAG 联检 | 跨域工作流编排 | 多 agent 协商 / 复盘 |

> 详细矩阵（每格 3–5 项 skill / agent / 集成）见 [CAPABILITY_MATRIX.md](./CAPABILITY_MATRIX.md)。

---

## 3. 与 V2 架构 Diff

| 模块 | V2 现状 | V3 处置 | 备注 |
|---|---|---|---|
| 21 个 specialized agents | 散落在 `backend/src/agents/` | **保留**，下沉为 L3 专业层 | 由 L1 personas 路由调用 |
| 51 个 routes | 法务为主 | **保留 + 扩展** | 新增 personas / tasks / integrations |
| 32 个 models | 法务领域 | **保留 + 扩展** | 新增 Task / Integration / Skill 模型 |
| 104 个 services | 法务为主 | **保留 + 重构** | 抽取通用 4 横能力到 capability layer |
| coordinator + workforce | 两套并行 | **合并**为 TaskOrchestrator | 统一同步/异步/多 agent |
| 36 pages × 286 components | 法务侧重 | **重构 IA**：10 personas + 任务流 | P1–P3 渐进切换 |
| Tauri 桌面壳 | 已就绪 | **升级为主战场** | 异步任务托盘 + 通知中心 |
| 三态模式（本地/混合/云端） | 已落地 | **保留** | V3 沿用，合规经营默认本地优先 |
| Workforce / consensus_agent | 实验性 | **重构**为 Hermes 范式 | 多 agent 协商 + 投票 |
| 信息获取栈 | searxng + 部分爬虫 | **新增** crawl4ai + HeadlessX self-host | 反检测 + 官方 API 优先 |
| 学习闭环 | 无 | **新增** Evolver (EvoMap) | 任务完成 → 经验回流 |
| 多模态 RAG | 文本为主 | **新增** RAG-Anything (HKUDS) + MinerU | 表格 / 图 / 公式 |
| Vibe Selling / AI-Trader | 无 | **新增** | 销售 + 出海决策范式 |
| canvas-design / web-artifacts-builder | 无 | **新增**（cowork-anthropic） | 设计 + 落地页 |

---

## 4. 三端定位（多形态接入）

| 形态 | 角色 | 核心场景 | 技术栈 | 优先级 |
|---|---|---|---|---|
| 🖥 **桌面（Tauri）** | **主战场** | 长任务、文档处理、多窗口、本地沙箱、合规经营 | Tauri 2 + Rust + React + Vite | P0 |
| 📱 **移动（Expo RN）** | **遥控器** | 任务推送、审批、紧急咨询、查看结果 | Expo + React Native | P1 |
| 🟢 **小程序（Taro）** | **保留** | 轻量入口、客户分享、扫码授权 | Taro 3.6 + React | P2 |
| 🌐 **Web** | 兜底入口 | 落地页、未登录浏览、SaaS 体验 | Vite + React + Shadcn | P0 |
| 💬 **IM 通道** | **现场办公** | 群内 @ 触发任务、推送回报 | 飞书 / 钉钉 / 企微 / Slack / WhatsApp | P3 |

> **设计原则**：桌面跑活，移动看活，小程序拉客，Web 兜底，IM 触达。

---

## 5. 异步任务架构（Codex / Dispatch / Devin 风格）

```
┌─────────────┐   1. 创建任务      ┌──────────────────┐
│  用户       │ ─────────────────▶ │ TaskOrchestrator │
│ (App / IM)  │                    └────────┬─────────┘
└─────▲───────┘                             │
      │                              2. 入队 + 鉴权
      │                                     │
      │                            ┌────────▼─────────┐
      │                            │   TaskQueue      │
      │                            │ (Redis / Celery) │
      │                            └────────┬─────────┘
      │                                     │
      │                          3. 拉取 + 分配 persona
      │                                     │
      │                            ┌────────▼─────────┐
      │                            │ SandboxExecutor  │
      │                            │  · macOS sandbox │
      │                            │  · firejail      │
      │                            │  · Docker        │
      │                            └────────┬─────────┘
      │                                     │
      │                       4. 调用 specialized agent + skills
      │                                     │
      │                            ┌────────▼─────────┐
      │                            │  Agent + Tools   │
      │                            │  (RAG / OAuth)   │
      │                            └────────┬─────────┘
      │                                     │
      │                          5. 进度事件 SSE / WS
      │ ◀───────────────────────────────────┤
      │                                     │
      │                          6. 完成 + 沉淀经验
      │ ◀───────────────────────────────────┤
      │                            (Evolver 学习闭环)
      │                                     │
      └─── 7. 多通道推送 ◀──────────────────┘
              · 桌面通知中心
              · 移动推送
              · IM 卡片消息
              · 邮件摘要
```

### 沙箱方案矩阵

| 平台 | 首选 | 兜底 | 隔离级别 |
|---|---|---|---|
| macOS | `sandbox-exec` profile | Docker Desktop | 文件 + 网络 |
| Linux | `firejail` / `bwrap` | Docker | 文件 + 网络 + syscall |
| Windows | Windows Sandbox / WSL2 | Docker Desktop | VM 级 |
| 服务端 | Docker / containerd | gVisor | 容器 |

---

## 6. 数据流（端到端示例）

**场景**：用户在飞书群里 @ 安心助理，问「帮我尽调一下『XX 制造有限公司』」。

```
[1] 飞书群 @bot ─▶ Lark Webhook ─▶ AnxinGateway
                                        │
[2] Gateway ─▶ TaskOrchestrator.create(persona="尽调专家", input=...)
                                        │
[3] Orchestrator ─▶ 路由到 Persona「尽调专家」
                                        │
[4] Persona ─▶ 编排 specialized agents:
              · due_diligence  (主导)
              · evidence_analyst
              · sentiment_agent
              · legal_researcher (法律风险)
              · risk_assessor
                                        │
[5] 调用 4 横能力:
    ① 信息获取: 企查查 API + 官方公告 + 新闻抓取 (HeadlessX)
    ② 调研分析: RAG-Anything 解析年报 + 引文追踪
    ③ 设计开发: 生成尽调报告 PDF (canvas-design)
    ④ 销售决策: 综合评分 + 风险等级建议
                                        │
[6] SandboxExecutor 隔离运行 (firejail)
                                        │
[7] 进度通过 SSE 实时推送到飞书卡片 (5%/30%/80%/100%)
                                        │
[8] 完成 ─▶ 飞书卡片消息 + PDF 附件 + 桌面通知
                                        │
[9] Evolver 沉淀: 「制造业尽调」模板 + 「XX 公司」知识节点
```

---

## 7. 安全 / 合规要点

### 三态运行模式（继承 V2，V3 沿用）

| 模式 | 数据出域 | 模型推理 | 适用场景 | V3 默认 |
|---|---|---|---|---|
| **本地** | ❌ | 本地 LLM (Ollama / vLLM) | 合规经营、内部合同、敏感尽调 | 桌面端默认 |
| **混合** | 脱敏后出 | 本地 + 云端协同 | 调研、内容、跨境 | 桌面 / 移动 |
| **云端** | ✅ | 云端 LLM (Claude / 通义) | 普通对话、公开信息 | Web / 小程序 |

### V3 新增安全要点

- **OAuth 凭证**：统一 KMS 加密存储；按 persona / 任务 最小授权；24h 自动 refresh。
- **沙箱**：所有异步任务必走 SandboxExecutor，文件白名单 + 网络白名单 + 时长上限。
- **跨境数据**：出海场景遵循 PIPL / GDPR 双合规；用户域数据本地保留；模型不持久化。
- **链路追踪**：每个任务唯一 `task_id`，全链路日志（OpenTelemetry）+ 审计可回放。
- **引文追踪**：所有调研 / 法律输出必须带 source URL + 段落锚点（DeepTutor 风格），可一键溯源。
- **人机协同**：高风险动作（合同提交 / 钱款 / 法律意见正式发出）必须二次确认。

---

## 8. 技术栈速览

| 层 | 关键技术 |
|---|---|
| 桌面 | Tauri 2 · Rust · React 19 · Vite · Shadcn · Tailwind v4 |
| 移动 | Expo SDK 53 · React Native · NativeWind |
| 小程序 | Taro 3.6 · React · NutUI |
| 后端 | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Celery |
| 数据 | PostgreSQL 16 · Redis 7 · Qdrant (向量) · MinIO (对象) |
| RAG | RAG-Anything (HKUDS) · MinerU · LangChain |
| Agent | 自研 Orchestrator · Hermes-Agent 范式 · 自研 Harness Workforce |
| 学习 | Evolver (EvoMap) · 经验沉淀回流 |
| 信息获取 | crawl4ai · HeadlessX (self-host) · BeautifulSoup4 · lxml · 官方 API |
| 设计 | canvas-design · web-artifacts-builder · Remotion (视频) |
| 沙箱 | sandbox-exec (mac) · firejail (linux) · Docker · WSL2 (win) |
| 监控 | OpenTelemetry · Prometheus · Grafana · Loki |

---

## 9. 演进路线（速览）

| 阶段 | 状态 | 核心交付 |
|---|---|---|
| P0 品牌切换 | ✅ 完成（2026-04-26） | 安心法务 → 安心智能助手 |
| P1 IA 重构 | ✅ 完成（2026-04-26） | 侧边栏 10 personas + 7 占位页 + 后端 3 模块骨架 + 6 大文档 |
| P2 异步任务 MVP | ✅ 完成（2026-04-27） | TaskOrchestrator + Celery + 8 endpoint + Alembic 028 |
| P3 IM 通道 + 沙箱 | ✅ 完成（2026-04-27） | 飞书真 + 4 占位 + 配对授权 24h + SandboxExecutor 骨架 |
| P4 OAuth 首批 5 个 | ✅ 完成（2026-04-27） | 飞书/钉钉/Notion/Shopify(真)+Amazon SP-API(mock) |
| P5 Skills 运行时 + 4 office | ✅ 完成（2026-04-27） | skill_registry + skill_executor + docx/xlsx/pptx/pdf |
| P6 信息获取栈 + 多源 | ✅ 完成（2026-04-27） | FetchService 4 层 + 5 法律源 + 5 电商源 |
| P7 5 user-facing personas | ✅ 完成（2026-04-27） | 流程/市场/获客/内容/出海 + PersonaRegistry |
| P8 文档同步 + bug 修 | 🚧 进行中 | 文档对齐 + baseline 健康度 + 前端 personas 落地页 |
| P9+ 5 法务 persona / 知识库 / 生产部署 | 🔜 待启动 | 见 ROADMAP |

> 详细路线图见 [ROADMAP.md](./ROADMAP.md)。

---

## 10. V3 模块清单（实装路径速查）

| 模块 | 路径 | 状态 |
|---|---|---|
| **Persona Registry** | [`backend/src/agents/personas/registry.py`](../../backend/src/agents/personas/registry.py) | ✅ |
| Persona BasePersona | [`backend/src/agents/personas/base_persona.py`](../../backend/src/agents/personas/base_persona.py) | ✅ |
| Persona — 流程管家 | [`backend/src/agents/personas/operations_manager.py`](../../backend/src/agents/personas/operations_manager.py) | ✅ |
| Persona — 市场研究员 | [`backend/src/agents/personas/market_researcher.py`](../../backend/src/agents/personas/market_researcher.py) | ✅ |
| Persona — 获客猎手 | [`backend/src/agents/personas/lead_hunter.py`](../../backend/src/agents/personas/lead_hunter.py) | ✅ |
| Persona — 内容总监 | [`backend/src/agents/personas/content_director.py`](../../backend/src/agents/personas/content_director.py) | ✅ |
| Persona — 跨境电商助手 | [`backend/src/agents/personas/ecommerce_assistant.py`](../../backend/src/agents/personas/ecommerce_assistant.py) | ✅ |
| **TaskOrchestrator** | [`backend/src/services/task_orchestrator/`](../../backend/src/services/task_orchestrator/) | ✅ P2 |
| **IM Gateway** | [`backend/src/services/im_gateway/`](../../backend/src/services/im_gateway/) (5 adapter，feishu 真) | ✅ P3 |
| IM 配对授权 | [`backend/src/services/im_gateway/pairing/`](../../backend/src/services/im_gateway/pairing/) | ✅ P3 |
| **SandboxExecutor** | [`backend/src/services/sandbox_executor/`](../../backend/src/services/sandbox_executor/) (LocalProvider 真) | ✅ P3 |
| **AppAuthorization (OAuth)** | [`backend/src/services/app_authorization/`](../../backend/src/services/app_authorization/) (4 真 provider) | ✅ P4 |
| **SkillRegistry + Executor** | [`backend/src/services/skill_registry/`](../../backend/src/services/skill_registry/) + [`skill_executor/`](../../backend/src/services/skill_executor/) | ✅ P5 |
| **Office Skills** (4) | [`skills/office/{docx,xlsx,pptx,pdf}/`](../../skills/office/) | ✅ P5 |
| **FetchService 4 层** | [`backend/src/services/fetch/`](../../backend/src/services/fetch/) (router + tiers + sources + compliance) | ✅ P6 |
| Fetch — 法律源 (5) | [`backend/src/services/fetch/sources/legal/`](../../backend/src/services/fetch/sources/legal/) | ✅ P6 |
| Fetch — 电商源 (5) | [`backend/src/services/fetch/sources/ecommerce/`](../../backend/src/services/fetch/sources/ecommerce/) (shopify 真+4 mock) | 🟡 P6 |
| **v3 API routes**（10 文件 / 61 endpoint） | `backend/src/api/routes/{personas,persona_market,persona_sales,persona_content,persona_ecommerce,tasks,agent_tasks,im_pairing,app_authorizations,skills,fetch}.py` | ✅ |
| **Alembic 迁移** | `028_add_agent_tasks_table.py` / `029_add_im_gateway_tables.py` / `030_add_app_authorization_tables.py` | ✅ |
| **前端 v3 页面** | [`frontend/src/pages/v3/`](../../frontend/src/pages/v3/) (tasks + agents + 6 capabilities) | ✅ |

---

## 11. V3 已实现部分 vs 规划部分

### ✅ 已实现（P0-P7）

- 🏷 品牌切换 + 8 文件
- 🧭 IA 重构（feature flag）+ 7 v3 页面
- 🔄 异步任务（TaskOrchestrator + Celery）+ 状态机
- 💬 IM 通道（飞书真 + 4 占位）+ 配对授权 24h + Celery 过期清理
- 🛡 沙箱执行器骨架 + LocalProvider 可用
- 🔐 OAuth 框架 + 4 真 provider（飞书/钉钉/Notion/Shopify）+ 加密 token_store
- 🧰 Skills 运行时（pyyaml + watchdog 热加载）+ 6 API
- 📄 4 office skill（cowork-anthropic 兼容）+ helpers + templates + tests
- 🌐 FetchService 4 层 + 合规审计 + URL 路由 + 频率限制
- 📚 5 法律数据源（合规版）
- 🛒 5 电商数据源（Shopify 真 + 4 mock）
- 🤖 5 user-facing persona（流程 / 市场 / 获客 / 内容 / 出海）+ PersonaRegistry
- 📊 DeepResearch 迭代算法 / LeadScoring 模型 / AI 议价能力 / VAT 指引
- 🧪 543+ pytest 通过；100 个 test 文件

### 🚧 规划中（P8+）

- **P8（进行中）**：baseline bug 修 / 健康度 / 前端 personas 落地页 / 文档同步（本任务 ✅）
- **P9+**：5 法务 persona 上层包装（21 agent 已就绪）/ 真 OAuth（CRM / 信息源 / 财税）/ Docker sandbox provider
- **P10**：知识库新版 — RAG-Anything (HKUDS) + MinerU 多模态接入；引文锚点
- **P11**：团队协作 — tenant_id 全链路 + RBAC + 审计可视化
- **P12**：E2E playwright 全量（5 personas × 主流程 × 三端）
- **P13**：生产部署到 anxinai.com（双域名平滑过渡）
- **Beyond**：Agent 三层重构 / Evolver 学习闭环 / 国际化 / LLM 路由 + 缓存 + 成本优化

---

上次更新：2026-04-27（P0-P7 实装状态完整同步）
