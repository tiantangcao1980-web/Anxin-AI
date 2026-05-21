# UI 全谱修复路线图 · 2026-05-20

> 配套 [`UI_GUIDELINES.md`](../../UI_GUIDELINES.md) + [`full-page-audit-2026-05-20.md`](full-page-audit-2026-05-20.md)
> 范围：`frontend/src/pages/` 71 个 `.tsx` 文件
> 单一执行总纲。每完成一批 commit + push + 在表格更新状态。

---

## 状态图例
- ✅ **Done** — 已完成 Editorial Luxury 改造
- 🟡 **Partial** — 部分合规，需补
- ⬜ **Todo** — 待处理
- 🚫 **Skip** — 不在改造范围（V2 兼容 / pending V3 重构）

---

## 阶段 0 · 已完成（Reset 4 个 surface）

| 文件 | 行数 | 用何容器 | 状态 |
|---|---|---|---|
| `pages/Login.tsx` | 997 | 自定义 Editorial 7+5 + serif Display | ✅ |
| `pages/DomainHomePage.tsx` | — | 编辑部目录 4+8 | ✅ |
| `components/WelcomeGuide.tsx` | — | 编辑部目录 modal | ✅ |
| `components/Layout.tsx` | — | 顶栏 + 侧栏（1px primary 替代域色） | ✅ |
| `pages/Leads.tsx` | 599 | ListPageTemplate + DetailPageTemplate + PanelSection | ✅ |

---

## 阶段 1 · List 类（15 页 / 估时 24-30h）

用 **`<ListPageTemplate>`** 改造。每页含：① 改 UI ② 验证功能 ③ 修 bug ④ commit。

| # | 文件 | 行数 | 业务复杂度 | 模板选择 | 预估 (h) | 状态 |
|---|---|---|---|---|---|---|
| 1 | `Leads.tsx` | 599 | Pipeline + List + Detail | ListPageTemplate + DetailPageTemplate | — | ✅ Done |
| 2 | `Cases.tsx` | 340 | List + Filter | ListPageTemplate | 2 | ⬜ |
| 3 | `Contracts.tsx` | — | List + Risk badge | ListPageTemplate | 2 | ⬜ |
| 4 | `Documents.tsx` | 340 | Mixed grid（**C 类**）| ListPageTemplate | 3 | ⬜ |
| 5 | `FindLawyer.tsx` | 478 | List + 推荐匹配 | ListPageTemplate | 2.5 | ⬜ |
| 6 | `KnowledgeBase.tsx` | 994 | List + 搜索 + 上传 | ListPageTemplate | 3 | ⬜ |
| 7 | `Tasks.tsx` | 298 | List + filter | ListPageTemplate | 1.5 | ⬜ |
| 8 | `Messages.tsx` | — | 消息流（special） | 自定义 + EditorialPageHeader | 2 | ⬜ |
| 9 | `News.tsx` | — | 文章列表 | ListPageTemplate | 1.5 | ⬜ |
| 10 | `Academy.tsx` | — | 课程列表 | ListPageTemplate | 1.5 | ⬜ |
| 11 | `CaseMarket.tsx` | — | 案件市场 | ListPageTemplate | 2 | ⬜ |
| 12 | `CaseCenter.tsx` | — | 中心枢纽 | DashboardTemplate | 2 | ⬜ |
| 13 | `ManagementCenter.tsx` | — | 管理中心 | DashboardTemplate | 2 | ⬜ |
| 14 | `Investigation.tsx` | — | 调查列表 | ListPageTemplate | 1.5 | ⬜ |
| 15 | `RiskAlertPanel.tsx` | — | 风险面板 | DashboardTemplate | 1.5 | ⬜ |
| 16 | `SyncConflicts.tsx` | — | 冲突列表 | ListPageTemplate | 1 | ⬜ |
| 17 | `Pricing.tsx` | — | 套餐对比 | 自定义 Editorial | 2 | ⬜ |

---

## 阶段 2 · Detail/Form 类（8 页 / 估时 18-24h）

| # | 文件 | 行数 | 模板 | 预估 (h) | 状态 |
|---|---|---|---|---|---|
| 1 | `CaseDetail.tsx` | — | DetailPageTemplate | 2.5 | ⬜ |
| 2 | `LawyerProfile.tsx` | 498 | DetailPageTemplate | 2.5 | ⬜ |
| 3 | `Settings.tsx` | 1507 | FormPageTemplate + anchorNav | 6 | ⬜ |
| 4 | `LawyerOnboarding.tsx` | 943 | FormPageTemplate | 4 | ⬜ |
| 5 | `PrivateLLMSetup.tsx` | 531 | FormPageTemplate | 2.5 | ⬜ |
| 6 | `MySubscription.tsx` | 517 | DashboardTemplate + Detail | 2.5 | ⬜ |
| 7 | `ClientPortal.tsx` | — | DetailPageTemplate | 1.5 | ⬜ |
| 8 | `QuickQuery.tsx` | — | 自定义聚焦输入 + EditorialPageHeader | 1.5 | ⬜ |

---

## 阶段 3 · Dashboard / Workspace（7 页 / 估时 20-28h）

最复杂层级，含图表 + 表格 + 多区块。用 `<DashboardTemplate>` + `<PanelSection>`。

| # | 文件 | 行数 | 估时 (h) | 已知功能 bug 待修 | 状态 |
|---|---|---|---|---|---|
| 1 | `LawyerDashboard.tsx` | — | 3 | 检查图表无紫色 | ⬜ |
| 2 | `AcquisitionDashboard.tsx` | — | 3 | — | ⬜ |
| 3 | `MonitoringCenter.tsx` | 514 | 4 | 实时数据轮询 — 测试不闪烁 | ⬜ |
| 4 | `KnowledgeGraph.tsx` | 1683 | 6 | Canvas 节点色已修 (commit b2436e52) | ⬜ |
| 5 | `Collaboration.tsx` | 1749 | 6 | 协作编辑器整合 | ⬜ |
| 6 | `AgentApprovalWorkspace.tsx` | 2221 | 8 | Form 嵌套 / 多 step | ⬜ |
| 7 | `ContractReview.tsx` | 1394 | 5 | diff 渲染保留 | ⬜ |
| 8 | `ComplianceCheck.tsx` | 884 | 4 | 风险三档保留 | ⬜ |
| 9 | `DueDiligence.tsx` | 952 | 4 | InvestigationReport 模板已修 (b2436e52) | ⬜ |

---

## 阶段 4 · Admin 表格（18 页 / 估时 28-36h）

全部用 `<AdminTableTemplate>`。Admin 页 ROI 最低但数量多，可批量。

| # | 文件 | 行数 | 估时 (h) | 状态 |
|---|---|---|---|---|
| 1 | `admin/AdminDashboard.tsx` | — | 2 | ⬜ |
| 2 | `admin/AdminBasic.tsx` | — | 1.5 | ⬜ |
| 3 | `admin/AdminUsers.tsx` | 545 | 2.5 | ⬜ |
| 4 | `admin/AdminBilling.tsx` | 630 | 2.5 | ⬜ |
| 5 | `admin/AdminConfig.tsx` | 623 | 2.5 | ⬜ |
| 6 | `admin/AdminFeatureFlags.tsx` | 557 | 2 | ⬜ |
| 7 | `admin/AdminRoles.tsx` | — | 1.5 | ⬜ |
| 8 | `admin/AdminOrgs.tsx` | — | 1.5 | ⬜ |
| 9 | `admin/AdminEnterprise.tsx` | — | 2 | ⬜ |
| 10 | `admin/AdminFirm.tsx` | — | 1.5 | ⬜ |
| 11 | `admin/AdminLawyerVerify.tsx` | — | 1.5 | ⬜ |
| 12 | `admin/AdminAIConfig.tsx` | — | 1.5 | ⬜ |
| 13 | `admin/AdminIntegrations.tsx` | — | 2 | ⬜ |
| 14 | `admin/AdminAcquisition.tsx` | 370 | 2 | ⬜ |
| 15 | `admin/AdminSecurity.tsx` | — | 2 | ⬜ |
| 16 | `admin/AdminHarness.tsx` | — | 1.5 | ⬜ |
| 17 | `admin/AdminHealth.tsx` | — | 1.5 | ⬜ |
| 18 | `admin/AdminAudit.tsx` | — | 1 | 🟡 Partial（PDF 模板 hex 已修 b2436e52，UI 头部待 Editorial 化）|

---

## 阶段 5 · Chat 单独重构（1 页 / 估时 16-24h）

`pages/Chat.tsx` — 2796 行 / 用户日常入口 / 完全自定义（C 类）。最复杂也最重要。

| 关注点 | 改造方向 |
|---|---|
| 头部 | `<EditorialPageHeader>` 紧凑模式 + tracker「AI Chat · 对话」 |
| 左侧会话列表 | hairline 分隔 + 衬线对话名 + caption 时间 |
| 中间消息流 | bubble 改为 Editorial 排版（用户右对齐 / AI 左对齐衬线） |
| 工具栏 | `InputOrchestrationBar` 与 Editorial 风格对齐（已部分） |
| Empty 态 | Editorial Empty + 推荐场景 |
| Risk 提示 | 状态色 tone-only |

**功能必须保留**：流式光标、思考链、引用、置信度、多模型切换、右侧工作台、文档预览、Canvas 编辑。

**Chat 是独立 phase，不与其他阶段并行**。

---

## 阶段 6 · v3/ 14 页（独立议题 / 估时 12-18h）

`v3/` 子目录 14 页全部 C 类。**建议先评估是否独立 PageContainer**：
- 如果 v3 是「下一代设计体系」试验场，保留为独立路径
- 如果 v3 只是新功能落地，应统一接入 PageTemplate

| 文件 | 估时 (h) | 状态 |
|---|---|---|
| `v3/agents/AgentsPage.tsx` | 1.5 | ⬜ |
| `v3/personas/PersonaWorkspacePage.tsx` | 2 | ⬜ |
| `v3/tasks/TasksPage.tsx` | 1.5 | ⬜ |
| `v3/capabilities/AppAuthorizationsPage.tsx` | 1 | ⬜ |
| `v3/capabilities/MessageChannelsPage.tsx` | 1 | ⬜ |
| `v3/capabilities/PairingAuthorizationsPage.tsx` | 1 | ⬜ |
| `v3/capabilities/PluginsPage.tsx` | 1 | ⬜ |
| `v3/capabilities/ScheduledTasksPage.tsx` | 1 | ⬜ |
| `v3/capabilities/SkillsPage.tsx` | 1 | ⬜ |
| `v3/rag/RagDashboardPage.tsx` | 2 | ⬜ |
| `v3/rag/DocumentLibraryPage.tsx` | 1.5 | ⬜ |
| `v3/rag/IngestPage.tsx` | 1.5 | ⬜ |
| `v3/rag/KnowledgeGraphPage.tsx` | 1.5 | ⬜ |
| `v3/rag/MultimodalQueryPage.tsx` | 1.5 | ⬜ |

---

## 阶段 7 · 收尾（估时 4-8h）

- 全量 vitest + typecheck + commercial-readiness-gate 验证
- 浏览器实景验证 10 个关键页（截图）
- 更新 visual-review-checklist.md
- PR comment 通知设计师
- 跑 commercial-readiness-gate --with-local-tests（如可行）

---

## 单页改造工作流（每页必走）

```
1. grep V2/违规项
   - hex 硬编码 / emoji / font-bold / text-2xl/3xl/4xl
   - V2 文案（"安心法务" 等）
   - 紫色族
2. 改 UI
   - 选择模板（按 UI_GUIDELINES §3.1）
   - 替换 V2 chip / cardStyle 为 Editorial
   - 状态色用 tone-only，不用背景色块
3. 修发现的 bug
   - 失效路由
   - 类型错误
   - dead code
   - 缺失 a11y label
4. 验证
   - vitest 必过
   - typecheck 0 新错误
   - 浏览器 HMR 编译通过
   - 截图自检（可选）
5. commit
   - 标题：refactor(ui): {page} → Editorial Luxury (Phase N · M/T)
   - 内容：UI 改 / bug 修 / 功能保留三件套清单
6. push（每完成 5-8 页 push 一次）
```

---

## 总工作量

| 阶段 | 页数 | 估时 |
|---|---|---|
| Phase 0 已完成 | 5 | — |
| Phase 1 List | 17 | 24-30h |
| Phase 2 Detail/Form | 8 | 18-24h |
| Phase 3 Dashboard/Workspace | 9 | 20-28h |
| Phase 4 Admin | 18 | 28-36h |
| Phase 5 Chat | 1 | 16-24h |
| Phase 6 v3 | 14 | 12-18h |
| Phase 7 收尾 | — | 4-8h |
| **总计** | **72** | **122-168h** |

单人全职：**3-4 周**。多次会话推进 + 频繁 commit/push。

---

> Last updated: 2026-05-20 — Step 3 路线图建立
> Next update: 每完成一个 Phase 后更新表格状态
