# 三大核心文档导航

> 日期：2026-05-14
> 用途：**新成员 / AI 智能体 1 小时内能找到「需求 / 架构 / 开发计划」全部权威源** 的单页索引。
> 与 [`00-project-execution-map.md`](00-project-execution-map.md) 的关系：00 文件是"项目推进全景"，本文件是"三大核心知识入口"。

---

## 速查 30 秒

| 我想知道 | 看这个 |
|---|---|
| 这个产品 **是什么、给谁用、为什么做** | [REQUIREMENTS.md](REQUIREMENTS.md) |
| 系统 **怎么搭、各模块如何协作** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **历史轨迹 + P0-P21 路线图** | [ROADMAP.md](ROADMAP.md) |
| 现在 **做到哪一步、接下来做什么** | [DEVELOPMENT_PLAN.md](DEVELOPMENT_PLAN.md) |
| 能否发布、5 维评测怎么判 | [RELEASE_GATE.md](RELEASE_GATE.md) |
| 22 个智能体 **怎么协作、红线在哪** | [AGENTS.md](../AGENTS.md) |
| 设计 token / Icon / 配色 / 排版 | [DESIGN.md](../DESIGN.md) |
| 工程规则（命名 / Git / API / 测试） | [standards/](standards/) |
| AI 智能体 30 秒接手 | [wiki/README.md](wiki/README.md) |

---

## 一、需求层 — `REQUIREMENTS.md`

> "做什么、给谁做、做到什么程度算成功"

### 1.1 一句话定位

**面向中国成长型制造企业（10–500 人）的全链路 AI 智能经营助理**：
- 一个 App 搞定 法务 / 财税 / 合规 / 经营管理 / 调研获客 / 内容产出 / 出海跨境
- 双客户端：**需求方端**（企业 C 端）+ **服务方端**（律师/律所/税务师/财务顾问）
- 三态运行：**local**（数据不出设备）/ **hybrid** / **cloud**

### 1.2 权威源

[`docs/REQUIREMENTS.md`](REQUIREMENTS.md)（325 行，8 节）：
1. 使命 + 一句话定位
2. 用户对象
3. 能力合同（5 域 × 4 维度）
4. 基线产品形态
5. 商业候选版定义
6. 发布门 5 维评测入口
7. 三态运行边界
8. 非功能需求 + 红线

### 1.3 关键非功能需求（红线）

来自 [`REQUIREMENTS.md §8`](REQUIREMENTS.md) + [`AGENTS.md §2`](../AGENTS.md)：

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

## 二、架构层 — `ARCHITECTURE.md`

> "系统如何工作 / 模块如何协作 / 数据如何流转"

### 2.1 6 层模型一图概览

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

| 文档 | 抽象层级 |
|------|----------|
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | **6 层 + 多平台 + 三态 + V3 vs V2 演进 + 关键流程**（权威，356 行） |
| [`../AGENTS.md`](../AGENTS.md) | **运行时 Agent 行为单一真相源**（红线/路由/反 slop/协作） |
| [`audit/harness/README.md`](audit/harness/README.md) | **六层框架**（Model/Harness/Context/Traces/Eval/Ops）持续审计索引 |
| [`context-architecture.md`](context-architecture.md) | **Context 三层**：AGENTS.md / skills/ / memory |
| [`audit/harness/00-integration-matrix.md`](audit/harness/00-integration-matrix.md) | Harness 8 模块接入体检矩阵 |
| [`audit/harness/01-trace-persistence-design.md`](audit/harness/01-trace-persistence-design.md) | Trace 持久化（traces / spans / clusters 三表） |
| [`audit/harness/02-ai-review-gates-design.md`](audit/harness/02-ai-review-gates-design.md) | 4 reviewer PR gate 设计 |
| [`audit/harness/05-self-heal-design.md`](audit/harness/05-self-heal-design.md) | 自愈闭环（severity + dispatcher + path safety） |
| [`v3/integrations.md`](v3/integrations.md) | 34+ OAuth provider / IM 适配器 / 数据源 |
| [`v3/skills-inventory.md`](v3/skills-inventory.md) | 13 域 76+ skill + 4 office 实装路径 |
| [`v3/capability-matrix.md`](v3/capability-matrix.md) | 4 横 × 4 纵能力矩阵 + 实装状态 |
| [`../DESIGN.md`](../DESIGN.md) | **视觉设计单一真相源** |
| [`v3/observability-backend.md`](v3/observability-backend.md) | Sentry + Prometheus + Grafana 后端可观测 |
| [`v3/security-audit.md`](v3/security-audit.md) | P15 OWASP Top 10 / 依赖 / 密钥审计 |

### 2.3 关键架构决策（ADR 索引）

完整决策日志见 [`wiki/06-decision-log.md`](wiki/06-decision-log.md)。

| 决策 | 位置 |
|---|---|
| 剥离 CAMEL-AI → 自研 Harness 层 | [`adr/`](adr/) + [`audit/harness/README.md`](audit/harness/README.md) + [`v3/p16-dependency-upgrade.md`](v3/p16-dependency-upgrade.md) |
| AGENTS.md 作为 Agent 行为单一真相源（vs CLAUDE.md） | [`../AGENTS.md`](../AGENTS.md) §1 |
| Progressive Disclosure skills 体系 | [`../skills/_template/SKILL.md`](../skills/_template/SKILL.md) |
| 三态运行（local/hybrid/cloud） | [`REQUIREMENTS.md §7`](REQUIREMENTS.md) + [`ARCHITECTURE.md §4`](ARCHITECTURE.md) |
| 双客户端隔离（C 端 / 服务方端） | [`ARCHITECTURE.md §2`](ARCHITECTURE.md) |
| v3 升级 / 品牌定型 | [`adr/001-v3-anxin-assistant-upgrade.md`](adr/001-v3-anxin-assistant-upgrade.md) |

---

## 三、开发计划层 — `ROADMAP.md` + `DEVELOPMENT_PLAN.md` + `RELEASE_GATE.md`

> "现在做到哪、接下来做什么、谁做、什么时候做完、能否发布"

### 3.1 当前阶段状态

- **V3 主体骨架已落**：P0-P7 完成，31 commits / 61 个 v3 API / 543+ pytest（截至 2026-04-27）
- **六层框架基线已落**：H0-O2 全部 ✅（截至 2026-05-14）
- **品牌定型**：安心智能助手（Anxin AI），全仓清理完成
- **文档单一信源化完成**：5 Spine + 9 Wiki + 101 文件归档（2026-05-14）

### 3.2 权威源（按用途）

| 文档 | 用途 |
|---|---|
| [`../PROJECT_STATUS.md`](../PROJECT_STATUS.md) | **历史快照** + 当前进度（每次开发后更新） |
| [`ROADMAP.md`](ROADMAP.md) | **路线图**：P0-P21 + 风险登记册 + 里程碑 |
| [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md) | **当前批次** T1-T10 + 6 lane 并行 + 48h 冲刺 + 执行规范 |
| [`RELEASE_GATE.md`](RELEASE_GATE.md) | **5 维评测** / lane 测试 / 门禁命令 / 证据清单 / Go-NoGo |
| [`wiki/03-current-state.md`](wiki/03-current-state.md) | **AI 高频更新版**当前状态摘要 |
| [`audit/harness/03-h1-followups.md`](audit/harness/03-h1-followups.md) | Harness 层 P0/P1/P2 后续 |
| [`audit/harness/`](audit/harness/) | 六层框架持续审计 |
| [`audit/ui-ux-audit-2026-05-08.md`](audit/ui-ux-audit-2026-05-08.md) | UI/UX 审计差异清单（P9-P13 前置门槛） |
| [`release/`](release/) | 证据物料 / runbook / external-* / checklist JSON |

### 3.3 主线 P0/P1 followup（2026-05-14 当前）

来自 [`DEVELOPMENT_PLAN.md §4`](DEVELOPMENT_PLAN.md)：

- [ ] **P0** policy_engine 主路径统一收敛（合并 `_check_mcp_tool_policy` 与 `policy_enforcement.check_tool_call`）
- [ ] **P0** context_engine vs context_compressor 二选一
- [ ] **P0** UI/UX 假成功修复（按 `audit/ui-ux-audit-2026-05-08.md`）
- [ ] **P1** cost_tracker 本地 LLM 估算 + 用户配额阻断
- [ ] **P1** task_engine 扩展到合同 / 尽调 / 批量文档
- [ ] **P1** tool_registry 改造（与 C2 协同）
- [ ] **P1** 图标体系收口（80 文件 `lucide-react` 直接 import → `@/lib/icons`）
- [ ] **P1** 合并 `peaceful-goodall` 分支（CREAO 自愈 Slice 1）
- [ ] **P2** capability_negotiator 统一桌面/前端/服务

### 3.4 推进顺序（执行流）

见 [`00-project-execution-map.md §7`](00-project-execution-map.md)。

---

## 三大核心层之间的关系

```
┌────────────────────────────────────────────────────────────┐
│  需求层（WHY + WHAT）                                       │
│    REQUIREMENTS.md                                          │
│    → 定义"做什么、给谁做、做到什么算成功"                    │
└────────────────────────────────────────────────────────────┘
                          ▼
┌────────────────────────────────────────────────────────────┐
│  架构层（HOW）                                              │
│    ARCHITECTURE.md + AGENTS.md + audit/harness/             │
│    DESIGN.md + context-architecture + skills/_template      │
│    → 定义"系统怎么搭、模块怎么协作、约束在哪"                │
└────────────────────────────────────────────────────────────┘
                          ▼
┌────────────────────────────────────────────────────────────┐
│  开发计划层（WHEN + WHO）+ 发布门（CAN-RELEASE?）            │
│    ROADMAP.md + DEVELOPMENT_PLAN.md + RELEASE_GATE.md       │
│    PROJECT_STATUS.md + audit/harness + audit/ui-ux          │
│    → 定义"现在做到哪、接下来做什么、能否发布"                │
└────────────────────────────────────────────────────────────┘
```

**仲裁顺序**（冲突时）：REQUIREMENTS > ARCHITECTURE > ROADMAP > DEVELOPMENT_PLAN > RELEASE_GATE。

---

## 维护规则

- 本文件每改必须有 PR + 至少 1 名核心维护者 review
- 当任一 Spine 文档**新增、改名、合并**时，本文件必须同步更新
- 历史快照见 `../PROJECT_STATUS.md`；本文件**只**维护当前权威指针
- 本文件被 [`00-project-execution-map.md`](00-project-execution-map.md) 和 [`../README.md`](../README.md) 在权威导航中引用
