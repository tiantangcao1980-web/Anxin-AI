# 全谱页面专业一致性审计 · 2026-05-20

> 范围：`frontend/src/pages/` 全量 71 个 `.tsx` 文件
> 目的：在 Editorial Luxury Reset 完成 4 个 surface 之后，盘点剩余 67 个业务页的合规度，给出改造路径决策依据
> 不修改任何文件，仅诊断

---

## 1. 总体盘点

| 指标 | 数值 |
|------|------|
| 总页面数 | **71** |
| 根 `pages/` | 39 |
| `pages/admin/` | 18 |
| `pages/v3/` | 14 |
| 最大页面 | `Chat.tsx` (2796 行) |
| 平均行数 | ~400 |

## 2. 布局容器合规度（最关键指标）

| 分类 | 页面数 | 占比 | 说明 |
|---|---|---|---|
| **A 类（合规）** | **45** | 63% | 使用 `PageContainer` 或 `CenterLayout` |
| **B 类（半合规）** | **17** | 24% | 自定义 div + padding，缺标准容器 |
| **C 类（不合规）** | **9** | 13% | 完全自定义布局，无任何标准 |

**关键观察**：`pages/v3/` 下 **14 个页面全部是 C 类**（v3 体系自成一派，未对齐 PageContainer）。

## 3. 排版散落度（违反 Editorial Luxury 程度）

| 检查项 | 命中次数 | 严重程度 |
|---|---|---|
| `text-2xl/3xl/4xl` 直接用（应走 `text-h1/h2/h3` token）| **9 处** | 🟡 中 |
| `font-bold/extrabold/black`（应主用 `font-medium/font-serif`）| **18 处** | 🟡 中 |
| `font-serif` 已正确应用 | 仅 Login + DomainHomePage | ⚠️ Editorial 渗透率仅 3% |

## 4. 颜色与禁令违规

| 检查项 | 命中 | 文件 |
|---|---|---|
| Hex 硬编码 `#xxxxxx` 在 tsx | **9 处** | 集中在 `admin/AdminAudit.tsx`（PDF 打印模板） |
| 紫色违禁（violet/purple/indigo）| **0 命中** ✅ | — |
| Emoji 字面值（⚖️🤖⚠️）| **4 处** | 散落在文案中 |
| V2 术语「案件中心」「律所」 | **16 命中** | 但 13 处「律所」属产品事实（注册角色）保留 |

## 5. Worst Offenders Top 10

| # | 文件 | 行数 | 主要违规 | 优先级 |
|---|---|---|---|---|
| 1 | `Chat.tsx` | **2796** | C 类 / 无 PageContainer / 完全自定义 / 用户日常入口 | **P0** |
| 2 | `AgentApprovalWorkspace.tsx` | 2221 | ⚠️ 内部 form 待审 | P1 |
| 3 | `KnowledgeGraph.tsx` | 1683 | ⚠️ font-bold×2 + 复杂嵌套 | P2 |
| 4 | `DueDiligence.tsx` | 952 | **C 类** / 无 PageContainer | **P1** |
| 5 | `ComplianceCheck.tsx` | 884 | text-2xl×1 + font-bold×2 | P2 |
| 6 | `admin/AdminAudit.tsx` | — | 9 处 Hex 硬编码（PDF 模板） | P1 |
| 7 | `Documents.tsx` | 340 | **C 类** | P1 |
| 8 | `v3/rag/RagDashboardPage.tsx` | 213 | **C 类** + v3 体系无独立 PageContainer | P2 |
| 9 | `LawyerProfile.tsx` | 498 | font-bold×1 + Detail 布局复杂 | P2 |
| 10 | `Cases.tsx` | 340 | B 类 / 待迁 A | P2 |

## 6. 业务模式分类（影响"建模板批量迁移"的可行性）

| 模式 | 页数 | 代表 | 建模板工作量 |
|---|---|---|---|
| List 列表页 | ~15 | Cases / Contracts / FindLawyer / Leads / Documents | 24-30h |
| Detail 详情页 | 2 | CaseDetail / LawyerProfile | 6-8h |
| Form 表单页 | 6 | Settings / LawyerOnboarding / PrivateLLMSetup | 12-16h |
| Dashboard/Workspace | 7 | LawyerDashboard / MonitoringCenter / Collaboration | 20-28h |
| Admin 表格 | 12 | AdminBilling / AdminConfig / AdminFeatureFlags | 16-20h |
| Chat/AI | 1-2 | Chat / QuickQuery | 16-24h |
| v3 系统 | 14 | TasksPage / SkillsPage / RagDashboard* | 待评估 |

**全量改造总工时**：100-180 小时（单人 2-4 周）

---

## 改造路径（3 选 1）

### A · 灰度推进（保守，2-3 周）
- 每周改 8-10 个页面，按优先级 P0 → P1 → P2 推进
- 不建模板，逐页 ad-hoc 调整
- 风险：每页改法可能不一致

### B · 建模板 + 批量迁移（推荐，2-3 周）
- 阶段 1（3 天）：先建 5 个模板（`ListPageTemplate` / `DetailPageTemplate` / `FormPageTemplate` / `DashboardTemplate` / `AdminTableTemplate`）
- 阶段 2（5 天）：批量迁移高频列表/详情/表单页（约 30 页）— 90% 工作走配置而非手写
- 阶段 3（5 天）：定向重构 Chat / AgentApproval / KnowledgeGraph 三个最大页面
- 阶段 4（2 天）：v3/ 14 页统一接入 PageContainer，决定是否独立体系
- 风险：模板抽象不到位可能漏掉细节

### C · 聚焦核心 10 页（快速，3-5 天）
- 仅改造**用户日访问 Top 10**：Chat / Cases / Contracts / Settings / KnowledgeBase / FindLawyer / CaseDetail / DueDiligence / Documents / Collaboration
- v3/ + admin/ 保持现状，挂"待重构"标签
- 风险：50+ 页面仍混乱，问题没根治

---

## 推荐路径

**选 B（建模板 + 批量迁移）**。理由：

1. **63% 已合规** — 不是从零开始，建模板能锁定剩余 37% 的统一度
2. **模式高度聚类** — 15 个 List 页 + 12 个 Admin 表格 + 6 个 Form 页 = 33 页，**建 3 个模板就覆盖 47%**
3. **Chat 必须单独重构** — 2796 行 + 完全自定义 + 用户日常入口，无法通过模板复用
4. **v3/ 14 页是独立议题** — 应单独评估是否需要独立 PageContainer，不卡主线
5. **守护机制已就位** — Reset 阶段加的 95+ 反向断链可阻止任何回归

如选 B，我会先做 3 天「模板层」（不动业务代码，只建 5 个模板组件 + 1 个示范页），完成后给你看模板效果，你确认后再批量迁移。
