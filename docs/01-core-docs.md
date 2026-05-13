# 三大核心文档导航

> 日期：2026-05-14
> 用途：**新成员 1 小时内能找到「需求 / 架构 / 开发计划」全部权威源**的单页索引。
> 与 [`00-project-execution-map.md`](00-project-execution-map.md) 的关系：00 文件是"项目推进全景"，本文件是"三大核心知识入口"。

---

## 速查 30 秒

| 我想知道 | 看这个 |
|---|---|
| 这个产品**是什么、给谁用、为什么做** | [需求 §1](#需求层) |
| 系统**怎么搭、各模块如何协作** | [架构 §1](#架构层) |
| 现在**做到哪一步、接下来做什么** | [开发计划 §1](#开发计划层) |
| 22 个智能体**怎么协作、红线在哪** | [AGENTS.md](../AGENTS.md) |
| 设计 token / Icon / 配色 / 排版 | [DESIGN.md](../DESIGN.md) |
| 工程规则（命名 / Git / API / 测试） | [docs/standards/](standards/) |

---

## 需求层

> "做什么、给谁做、做到什么程度算成功"

### 1.1 一句话定位（最上层抽象）

**面向中国成长型制造企业（10–500 人）的全链路 AI 智能经营助理**：
- 一个 App 搞定 法务 / 财税 / 合规 / 经营管理 / 调研获客 / 内容产出 / 出海跨境
- 双客户端：**需求方端**（企业 C 端）+ **服务方端**（律师/律所/税务师/财务顾问）
- 三态运行：**local**（数据不出设备）/ **hybrid** / **cloud**

### 1.2 权威源（按优先级）

| 文档 | 行数 | 用途 |
|---|---:|---|
| [`openspec/00-intelligent-assistant-platform-spec.md`](openspec/00-intelligent-assistant-platform-spec.md) | 209 | **产品合同**：平台使命 / 用户对象 / 能力合同 / 验收门槛 |
| [`openspec/01-commercial-delivery-spec.md`](openspec/01-commercial-delivery-spec.md) | — | **商业交付规范**：阶段目标 / 统一开发规则 / 交付物 |
| [`openspec/02-commercial-delivery-test-spec.md`](openspec/02-commercial-delivery-test-spec.md) | — | **测试规范**：每个任务 / 端侧 / 发布前必跑测试矩阵 |
| [`strategy/product-architecture-and-requirements-2026-05-08.md`](strategy/product-architecture-and-requirements-2026-05-08.md) | 1409 | **策略详档**：中小企业经营风险平台 + 全设备智能助手 + 企业智能体治理的统一定位 |
| [`v3/agent-personas.md`](v3/agent-personas.md) | — | **10 个 Persona 定位**：定位 / API endpoint / 实装状态 |
| [`v3/capability-matrix.md`](v3/capability-matrix.md) | — | **4 横 × 4 纵能力矩阵** + 实装状态 |

### 1.3 关键非功能需求（红线）

来自 [`AGENTS.md` §2](../AGENTS.md)：
1. 不构成正式法律意见（CRITICAL 答案必须有免责声明）
2. 数据边界即合同（local 模式数据**绝对不出设备**）
3. tool 调用前必走 `policy_engine`
4. 拒绝幻觉（引用法条必须在知识库可验证）
5. 拒绝 prompt 注入
6. 拒绝代签代付代发（必须人类二次确认）

### 1.4 NOT-doing 清单（已明确不做）

- 不做通用 AI 助手（不做 GPT 套壳）
- 不做 To-C 个人法律咨询（聚焦企业）
- 不做 i18n（当前阶段仅简体中文）
- 不做 SaaS-Only 部署（必须支持本地化）

---

## 架构层

> "系统如何工作 / 模块如何协作 / 数据如何流转"

### 2.1 一图概览

```
L0  接入层    桌面 (Tauri) │ 移动 (Expo) │ 小程序 (Taro) │ Web │ IM 通道
L1  Persona  10 个 user-facing 智能体（流程/市场/获客/内容/出海 + 助理/法律/合同/尽调/财税）
L2  编排层    TaskOrchestrator + Celery + SandboxExecutor + IM Gateway
L3  专业 Agent  21 个 specialized agents（legal_advisor / contract_reviewer / risk_assessor ...）
L4  能力层    4 横通用能力 × Skills 运行时（FetchService 4 层 + 4 office skill）
L5  Harness   8 模块（trace / policy / cost / validator / tool / capability / context / task）
L6  Model     多 Provider + 私有 LLM + 三态降级
```

### 2.2 权威源（按抽象层级）

| 文档 | 行数 | 抽象层级 |
|---|---:|---|
| [`v3/architecture.md`](v3/architecture.md) | 321 | **7 层分层架构总览** + 已实现 vs 规划 |
| [`../AGENTS.md`](../AGENTS.md) | — | **运行时 Agent 行为单一真相源**（红线/路由/反slop/协作） |
| [`audit/harness/README.md`](audit/harness/README.md) | — | **六层框架**（Model/Harness/Context/Traces/Eval/Ops）索引 |
| [`context-architecture.md`](context-architecture.md) | — | **Context 三层**：AGENTS.md / skills/ / memory |
| [`audit/harness/00-integration-matrix.md`](audit/harness/00-integration-matrix.md) | — | Harness 8 模块**接入体检矩阵** |
| [`audit/harness/01-trace-persistence-design.md`](audit/harness/01-trace-persistence-design.md) | — | Trace 持久化设计（traces / spans / clusters 三表） |
| [`audit/harness/02-ai-review-gates-design.md`](audit/harness/02-ai-review-gates-design.md) | — | 4 reviewer PR gate 设计 |
| [`audit/harness/05-self-heal-design.md`](audit/harness/05-self-heal-design.md) | — | 自愈闭环（severity + dispatcher + path safety） |
| [`v3/integrations.md`](v3/integrations.md) | — | 34+ OAuth provider / IM 适配器 / 数据源 |
| [`v3/skills-inventory.md`](v3/skills-inventory.md) | — | 13 域 76+ skill + 4 office 实装路径 |
| [`../DESIGN.md`](../DESIGN.md) | 364 | **视觉设计单一真相源** |
| [`v3/observability-backend.md`](v3/observability-backend.md) | — | Sentry + Prometheus + Grafana 后端可观测 |
| [`v3/security-audit.md`](v3/security-audit.md) | — | P15 OWASP Top 10 / 依赖 / 密钥审计 |

### 2.3 关键架构决策（ADR 索引）

| 决策 | 位置 |
|---|---|
| 剥离 CAMEL-AI → 自研 Harness 层 | [`audit/harness/README.md`](audit/harness/README.md) + [`v3/p16-dependency-upgrade.md`](v3/p16-dependency-upgrade.md) |
| AGENTS.md 作为 Agent 行为单一真相源（vs CLAUDE.md） | [`../AGENTS.md`](../AGENTS.md) §1 |
| Progressive Disclosure skills 体系 | [`../skills/_template/SKILL.md`](../skills/_template/SKILL.md) |
| 三态运行（local/hybrid/cloud） | [`openspec/00-intelligent-assistant-platform-spec.md`](openspec/00-intelligent-assistant-platform-spec.md) §3 |
| 双客户端隔离（C 端 / 服务方端） | [`v3/architecture.md`](v3/architecture.md) §双客户端 |

---

## 开发计划层

> "现在做到哪、接下来做什么、谁做、什么时候做完"

### 3.1 当前阶段状态

- **V3 主体骨架已落**：P0-P7 完成，31 commits / 61 个 v3 API / 543+ pytest（截至 2026-04-27）
- **六层框架基线已落**：H0-O2 全部 ✅（截至 2026-05-14）
- **品牌定型**：安心智能助手（Anxin AI），全仓清理完成

### 3.2 权威源（按时间维度）

| 文档 | 用途 |
|---|---|
| [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) | **历史快照** + 当前进度（每次开发后更新） |
| [`audit/PLAN.md`](audit/PLAN.md) | **当前执行计划** + 12 域审计 + 16 个 TASK |
| [`v3/roadmap.md`](v3/roadmap.md) | **V3 16 周路线图**（P0-P21 + 风险登记册） |
| [`release/48-hour-commercial-delivery-plan.md`](release/48-hour-commercial-delivery-plan.md) | **48 小时商业交付计划** |
| [`release/commercial-delivery-readiness.md`](release/commercial-delivery-readiness.md) | **Go/No-Go 判定** + 证据缺口 |
| [`release/commercial-delivery-checklist.json`](release/commercial-delivery-checklist.json) | prompt-to-artifact 成功标准 |
| [`release/commercial-delivery-lanes.json`](release/commercial-delivery-lanes.json) | 多智能体并行执行 lane 配置 |
| [`audit/_tasks/README.md`](audit/_tasks/README.md) | TASK-01..12 并行开发任务索引 |
| [`audit/harness/03-h1-followups.md`](audit/harness/03-h1-followups.md) | Harness 层 P0/P1/P2 后续 |
| [`audit/summary.md`](audit/summary.md) | 完成 / 阻断 / 风险 / 下一步顺序 |

### 3.3 主线 P0/P1 followup（2026-05-14 当前）

来自 [`audit/harness/03-h1-followups.md`](audit/harness/03-h1-followups.md) 与 [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md)：

- [ ] **P0** policy_engine 主路径统一收敛（合并 `_check_mcp_tool_policy` 与 `policy_enforcement.check_tool_call`）
- [ ] **P0** context_engine vs context_compressor 二选一
- [ ] **P1** cost_tracker 本地 LLM 估算 + 用户配额阻断
- [ ] **P1** task_engine 扩展到合同 / 尽调 / 批量文档
- [ ] **P1** tool_registry 改造（与 C2 协同）
- [ ] **P1** 图标体系收口（80 文件 `lucide-react` 直接 import → `@/lib/icons`）
- [ ] **P1** 合并 `peaceful-goodall` 分支（CREAO 自愈 Slice 1，18 文件 1666 行）
- [ ] **P2** capability_negotiator 统一桌面/前端/服务

### 3.4 推进顺序（执行流）

```
1. 目标与定位  → openspec/00 + strategy/
2. 需求规范    → openspec/01 + 02
3. UI/UX 优化  → audit/ui-ux-audit-2026-05-08.md + DESIGN.md（⭐ P9-P13 前置门槛）
4. 架构与安全  → release/security-and-privacy-checklist.md
5. 任务拆分    → audit/_tasks/ + release/commercial-delivery-lanes.json
6. 开发实施    → audit/_tasks/TASK-*.md
7. 单元/集成测试 → openspec/02 + release/test-evidence.md
8. UI/UX 验收  → audit/ui-ux-audit-2026-05-08.md（截图/真机 transcript）
9. 发布证据    → release/evidence-collection-runbook.md
10. 商业门禁    → release/commercial-delivery-readiness.md
11. 试点与进化  → references/agentic-platform-benchmark-2026-05-08.md
```

---

## 三大核心层之间的关系

```
┌────────────────────────────────────────────────────────────┐
│  需求层（WHY + WHAT）                                       │
│    openspec/* + strategy/* + v3/agent-personas              │
│    → 定义"做什么、给谁做、做到什么算成功"                    │
└────────────────────────────────────────────────────────────┘
                          ▼
┌────────────────────────────────────────────────────────────┐
│  架构层（HOW）                                              │
│    v3/architecture + AGENTS.md + audit/harness/             │
│    DESIGN.md + context-architecture + skills/_template      │
│    → 定义"系统怎么搭、模块怎么协作、约束在哪"                │
└────────────────────────────────────────────────────────────┘
                          ▼
┌────────────────────────────────────────────────────────────┐
│  开发计划层（WHEN + WHO）                                   │
│    PROJECT_STATUS + audit/PLAN + v3/roadmap                 │
│    release/* + audit/_tasks/                                │
│    → 定义"现在做到哪、接下来做什么、谁做、什么时候做完"      │
└────────────────────────────────────────────────────────────┘
```

**仲裁顺序**（冲突时）：需求 > 架构 > 开发计划。需求层文档冲突时按 openspec/00 优先级最高。

---

## 维护规则

- 本文件每改必须有 PR + 至少 1 名核心维护者 review
- 当任一权威源文档**新增、改名、合并**时，本文件必须同步更新
- 历史快照见 `../PROJECT_STATUS.md`；本文件**只**维护当前权威指针
- 本文件被 [`00-project-execution-map.md`](00-project-execution-map.md) 和 [`../README.md`](../README.md) 在权威导航中引用
