# 安心法务 — 导航与模块重构规划

> **版本**: v1.0
> **日期**: 2026-04-12
> **状态**: 设计确认
> **优先级**: P0

---

## 1. 重构目标

减少导航层级、合并关联功能、优化用户体验。核心变更：

| # | 变更类型 | 变更内容 |
|---|---------|---------|
| 1 | **合并** | 案件管理 + 案源管理 + 任务中心 → **案件中心** |
| 2 | **合并** | 合同管理 + 合规自检 → **管理中心** |
| 3 | **重命名** | 找律师 → **律师精英** |
| 4 | **重命名+增强** | 文档中心 → **智能文档**（新增文档/文件夹 CRUD） |
| 5 | **重构** | 智能调查 → **舆情监测**（2 个子模块：舆情中心 + 智能调查） |
| 6 | **移除** | 顶部导航移除"任务中心"独立入口 |

---

## 2. 导航结构对比

### 2.1 当前结构（Before）

```
顶部导航：AI法务 | 智能协作 | 智能调查 | 法律智库
系统功能：任务中心（独立导航项）

智能协作侧边栏（6项）：
  ├─ 案件管理     /cases
  ├─ 合同管理     /contracts
  ├─ 文档中心     /documents
  ├─ 找律师       /find-lawyer
  ├─ 合规自检     /compliance-check
  └─ 案源管理     /leads

智能调查侧边栏（8项）：
  ├─ 调查概览     /due-diligence
  ├─ 风险评估     /due-diligence/risk
  ├─ 诉讼分析     /due-diligence/litigation
  ├─ 信用合规     /due-diligence/compliance
  ├─ 关系图谱     /due-diligence/graph
  ├─ 舆情监控     /due-diligence/sentiment
  ├─ 风险推演     /due-diligence/simulation
  └─ 调查报告     /due-diligence/report
```

### 2.2 目标结构（After）

```
顶部导航：AI法务 | 智能协作 | 舆情监测 | 法律智库
系统功能：无独立导航项（任务中心并入案件中心）

智能协作侧边栏（4项）：
  ├─ 案件中心     /case-center       ← 合并: 案件管理+案源管理+任务中心
  ├─ 管理中心     /management        ← 合并: 合同管理+合规自检
  ├─ 律师精英     /find-lawyer       ← 重命名: 找律师
  └─ 智能文档     /documents         ← 重命名+增强: 文档中心

舆情监测侧边栏（2项）：
  ├─ 舆情中心     /monitoring        ← 新: 企业监测大盘
  └─ 智能调查     /investigation     ← 重构: 原智能调查（内联子视图）
```

---

## 3. 各模块详细设计

### 3.1 案件中心（`/case-center`）

**整合来源**：案件管理(`/cases`) + 案源管理(`/leads`) + 任务中心(`/tasks`)

**功能结构**：
```
案件中心
├─ Tab: 我的案件        ← 原案件管理（列表/看板视图、搜索/筛选、归档）
├─ Tab: 案源线索        ← 原案源管理（线索列表、跟进状态、转化案件）
├─ Tab: 任务与审批      ← 原任务中心（任务分配、审批流、进度跟踪）
└─ 案件详情页           ← 原 /cases/:id 保持不变，路由改为 /case-center/:id
```

**设计要点**：
- 顶部 Tab 切换三个子视图，保持在同一页面上下文
- 案件详情页保持独立路由，支持从三个 Tab 跳转
- 移除导航栏的"任务中心"独立入口
- 旧路由 `/cases` `/leads` `/tasks` 重定向到 `/case-center`

**涉及文件**：
- 新建: `pages/CaseCenter.tsx`（Tab 容器）
- 复用: `pages/Cases.tsx` → 抽取为 `components/case-center/CaseList.tsx`
- 复用: `pages/Leads.tsx` → 抽取为 `components/case-center/LeadList.tsx`
- 复用: `pages/Tasks.tsx` → 抽取为 `components/case-center/TaskBoard.tsx`
- 修改: `pages/CaseDetail.tsx`（路由从 `/cases/:id` → `/case-center/:id`）

### 3.2 管理中心（`/management`）

**整合来源**：合同管理(`/contracts`) + 合规自检(`/compliance-check`) + 合同审查(`/contract-review`)

**功能结构**：
```
管理中心
├─ Tab: 合同管理        ← 原合同管理（合同列表、AI审查入口、状态跟踪）
│   ├─ 合同审查详情     ← 原 /contract-review（内联或弹窗展示）
│   ├─ 采购合同跟踪     ← 新增：采购合同全生命周期管理
│   └─ 销售合同跟踪     ← 新增：销售合同风险预警
├─ Tab: 合规管理        ← 原合规自检（企业制度管理、管理体系检查）
│   ├─ 制度文件库       ← 新增：企业现有制度和管理体系的存档管理
│   └─ 合规自检报告     ← 原合规自检报告生成功能
└─ Tab: 风险预警        ← 新增：合同到期、条款风险、合规缺口预警
```

**设计要点**：
- 三个 Tab：合同管理 | 合规管理 | 风险预警
- 合同审查流程内联在合同管理 Tab 中（点击合同 → 审查详情）
- 风险预警 Tab 汇总显示所有合同和合规相关的风险项
- 旧路由 `/contracts` `/compliance-check` `/contract-review` 重定向到 `/management`

**涉及文件**：
- 新建: `pages/ManagementCenter.tsx`（Tab 容器）
- 复用: `pages/Contracts.tsx` → 抽取为 `components/management/ContractList.tsx`
- 复用: `pages/ComplianceCheck.tsx` → 抽取为 `components/management/CompliancePanel.tsx`
- 复用: `pages/ContractReview.tsx` → 抽取为 `components/management/ContractReview.tsx`

### 3.3 律师精英（`/find-lawyer`）

**变更**：仅重命名，路由不变

- 导航栏标签：找律师 → **律师精英**
- 路由保持 `/find-lawyer` 不变（避免不必要的路由迁移）
- 页面组件 `FindLawyer.tsx` 不变

### 3.4 智能文档（`/documents`）

**变更**：重命名 + 功能增强 + 布局优化

**新增能力**：
```
智能文档
├─ 文件夹管理          ← 新增：创建/重命名/删除文件夹，拖拽归类
├─ 文档管理            ← 新增：新建文档、导入文档、批量操作
├─ 文档列表视图        ← 优化：网格/列表切换、排序、搜索、标签筛选
├─ 文档编辑器          ← 保留：在线协作编辑（Yjs）
└─ AI 文档助手         ← 保留：AI 辅助写作、优化建议
```

**布局设计**（遵循 design-system.md 规范）：
- 左侧：文件夹树形导航（可收起，宽度 220px）
- 右侧：文档列表/编辑区域（flex-1）
- 顶部工具栏：新建文档、新建文件夹、导入、搜索、视图切换
- 遵循琥珀橙品牌色体系、暖灰调中性色
- 响应式：移动端文件夹树收起为抽屉

**涉及文件**：
- 重构: `pages/DocumentWorkbench.tsx`
- 新建: `components/smart-docs/FolderTree.tsx`
- 新建: `components/smart-docs/DocumentList.tsx`
- 新建: `components/smart-docs/DocumentToolbar.tsx`
- 复用: 现有文档编辑器组件

### 3.5 舆情监测（`/monitoring`）— 原"智能调查"

**模块重命名**：智能调查 → **舆情监测**
**顶部导航路径**：`/monitoring`
**子模块**：2 个（从原来的 8 个精简）

#### 3.5.1 舆情中心（`/monitoring`，默认首页）

**功能结构**：
```
舆情中心
├─ 大盘概览            ← 关注企业总数、新增舆情数、风险等级分布
├─ 监测对象管理        ← 添加/移除监测企业、设置监测频率
├─ 舆情动态时间线      ← 按时间倒序展示最新舆情事件
├─ 风险预警通知        ← 重大舆情变动的推送和提醒
└─ 历史数据            ← 每个监测对象的历史舆情缓存、趋势图
```

**设计要点**：
- 被监测对象有本地缓存 + 后台定时自动更新
- 大盘数据：卡片式统计 + 趋势图 + 风险热力图
- 点击监测对象进入详情（内联展示，非新路由）
- 新组件，基于原 `SentimentDashboard.tsx` 扩展

#### 3.5.2 智能调查（`/investigation`）

**功能结构**：
```
智能调查
├─ 搜索入口            ← 企业搜索/爬取输入框（保留原 SearchBar）
├─ 历史搜索记录        ← 最近查询的企业列表
├─ 热点推荐            ← 基于行业/区域的热门调查对象
└─ 调查详情（内联）    ← 点击企业后展开，以下功能内联展示：
    ├─ 调查概览        ← 原 InvestigationOverview（企业基本信息+进度）
    ├─ 风险评估        ← 原 InvestigationProgress + RiskTimeline
    ├─ 诉讼分析        ← 原 LegalCases
    ├─ 信用合规        ← 原 ComplianceReport
    ├─ 关系图谱        ← 原 InteractiveGraph
    ├─ 调查报告        ← 原 InvestigationReport
    ├─ 风险推演        ← 原 ScenarioSimulation（整合进来）
    └─ 返回按钮        ← 返回搜索列表
```

**设计要点**：
- 所有子功能**不再作为独立导航项**，而是在调查详情中**内联展示**
- 子功能间通过页内 Tab 或锚点切换，有明确的"返回"按钮
- 搜索页面 = 调查首页，展示搜索框 + 历史 + 热点
- 调查详情 = 展开状态，URL 可以是 `/investigation/:companyId`
- 原 8 个子路由全部移除，改为组件内部状态切换

**涉及文件**：
- 新建: `pages/MonitoringCenter.tsx`（舆情中心）
- 重构: `pages/DueDiligence.tsx` → `pages/Investigation.tsx`（智能调查）
- 复用: 所有 `components/due-diligence/` 组件（保留，调整引用方式）
- 新建: `components/monitoring/MonitorDashboard.tsx`
- 新建: `components/monitoring/MonitorTargetList.tsx`
- 新建: `components/monitoring/SentimentTimeline.tsx`

---

## 4. 路由变更映射

### 4.1 新路由定义

| 新路由 | 页面组件 | 说明 |
|--------|---------|------|
| `/case-center` | CaseCenter | 案件中心（Tab: 案件/案源/任务） |
| `/case-center/:id` | CaseDetail | 案件详情 |
| `/management` | ManagementCenter | 管理中心（Tab: 合同/合规/预警） |
| `/find-lawyer` | FindLawyer | 律师精英（路由不变） |
| `/documents` | SmartDocuments | 智能文档（路由不变，组件重构） |
| `/monitoring` | MonitoringCenter | 舆情中心 |
| `/investigation` | Investigation | 智能调查 |
| `/investigation/:companyId` | Investigation | 调查详情（内联） |

### 4.2 旧路由重定向

| 旧路由 | 重定向到 |
|--------|---------|
| `/cases` | `/case-center` |
| `/cases/:id` | `/case-center/:id` |
| `/leads` | `/case-center` (Tab: 案源线索) |
| `/tasks` | `/case-center` (Tab: 任务与审批) |
| `/contracts` | `/management` |
| `/contract-review` | `/management` |
| `/compliance-check` | `/management` (Tab: 合规管理) |
| `/due-diligence` | `/investigation` |
| `/due-diligence/*` | `/investigation` |

### 4.3 导航配置变更

```typescript
// Layout.tsx — navGroups 更新
const navGroups = [
  { id: 'ai-legal',    label: 'AI法务',   path: '/chat' },
  { id: 'collaboration', label: '智能协作', path: '/case-center' },
  { id: 'monitoring',  label: '舆情监测',  path: '/monitoring' },
  { id: 'knowledge',   label: '法律智库',  path: '/knowledge-base' },
]

// Layout.tsx — 智能协作侧边栏 (4项)
collaboration: [
  { id: 'case-center',  path: '/case-center',  label: '案件中心',  icon: Briefcase },
  { id: 'management',   path: '/management',   label: '管理中心',  icon: Shield },
  { id: 'find-lawyer',  path: '/find-lawyer',  label: '律师精英',  icon: Users },
  { id: 'documents',    path: '/documents',    label: '智能文档',  icon: FileText },
]

// Layout.tsx — 舆情监测侧边栏 (2项)
monitoring: [
  { id: 'monitoring',     path: '/monitoring',     label: '舆情中心',  icon: Activity },
  { id: 'investigation',  path: '/investigation',  label: '智能调查',  icon: Search },
]

// Layout.tsx — 系统功能 (移除任务中心)
systemItems: []  // 任务中心已整合入案件中心
```

---

## 5. 实施步骤

### Phase 1: 导航框架（无功能变更）
1. 更新 `Layout.tsx` 导航配置（navGroups + 侧边栏菜单）
2. 更新 `App.tsx` 路由定义（新路由 + 旧路由重定向）
3. 创建新页面骨架（CaseCenter / ManagementCenter / MonitoringCenter / Investigation）
4. 验证所有旧路由正确重定向

### Phase 2: 模块合并
5. CaseCenter: 将 Cases/Leads/Tasks 抽取为子组件，组装 Tab 容器
6. ManagementCenter: 将 Contracts/ComplianceCheck/ContractReview 抽取为子组件
7. Investigation: 重构 DueDiligence，改为搜索+内联详情模式

### Phase 3: 新功能开发
8. MonitoringCenter: 舆情大盘、监测对象管理、动态时间线
9. SmartDocuments: 文件夹树、文档 CRUD、布局优化

### Phase 4: 清理
10. 移除已废弃的页面文件（不再独立使用的原始页面）
11. 更新所有内部链接和跳转引用
12. 更新产品架构文档和设计系统文档

---

## 6. 设计规范遵循

本次重构严格遵循 `docs/design-system.md` 规范：

- **品牌色**: 琥珀橙 `--primary-*` 系列
- **字体**: PingFang SC / HarmonyOS Sans SC
- **间距**: 4px 基准网格
- **圆角**: 组件级 radius-md(8px)，卡片级 radius-lg(12px)
- **动效**: fast(150ms) 进入，normal(250ms) 切换
- **响应式**: mobile(<768px) 单栏 + 底部 Tab，desktop(>=1024px) 多栏
- **无障碍**: WCAG 2.2 AA，触摸目标 44px，焦点环 3px
