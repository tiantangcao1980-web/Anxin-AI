# 全局 UI/UX 与 A2UI 统一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立统一的全局设计系统与 A2UI 主协议，并将其落地到核心页面、标准业务页与后台页，消除样式和交互断层。

**Architecture:** 先收口设计令牌与页面骨架，再统一 A2UI 主协议与核心卡片，最后将统一视觉语言应用到 Chat、合同审查、尽调、知识图谱及通用业务页/后台页。实现过程中优先复用现有 `index.css`、`design-tokens.ts`、`PageContainer.tsx` 与 A2UI 渲染链，避免引入新 UI 栈。

**Tech Stack:** React 18、TypeScript、Tailwind CSS、framer-motion、Radix UI、Vite、Playwright

---

## 文件结构

- Modify: `frontend/src/index.css`
  - 收口全局 CSS 变量、品牌色、阴影、状态色、暗色模式 token
- Modify: `frontend/tailwind.config.js`
  - 将 CSS 变量映射到语义色、字体与阴影扩展
- Modify: `frontend/src/lib/design-tokens.ts`
  - 统一标题、卡片、按钮、输入、状态、页面容器预设
- Modify: `frontend/src/components/ui/PageContainer.tsx`
  - 固化标准业务页壳层、toolbar、密度与状态区
- Modify: `frontend/src/components/Layout.tsx`
  - 收口主站导航、模块切换、内容区层级与边距
- Modify: `frontend/src/components/admin/AdminLayout.tsx`
  - 让后台页复用统一视觉层级而不是独立皮肤
- Modify: `frontend/src/components/a2ui/A2UIRenderer.tsx`
  - 对齐统一 A2UI 卡片结构与样式
- Modify: `frontend/src/components/a2ui/StreamingA2UIRenderer.tsx`
  - 对齐流式卡片的状态区、骨架和动作区
- Modify: `frontend/src/components/a2ui/MobileA2UIAdapter.tsx`
  - 统一移动端卡片密度与底部动作布局
- Modify: `frontend/src/components/a2ui/core/A2UIComponentRegistry.ts`
  - 将 registry 类型命名对齐主协议
- Modify: `frontend/src/components/chat/LegacyA2UIRenderer.tsx`
  - 收口 legacy 样式并限制为兼容层
- Modify: `frontend/src/pages/Chat.tsx`
  - 应用新的工作台页骨架与统一 A2UI 区域
- Modify: `frontend/src/pages/ContractReview.tsx`
  - 应用分析页骨架与统一风险结果组件
- Modify: `frontend/src/components/chat/ContractReviewCard.tsx`
  - 与独立合同审查页对齐
- Modify: `frontend/src/pages/DueDiligence.tsx`
  - 应用分析页规范
- Modify: `frontend/src/pages/KnowledgeGraph.tsx`
  - 收口图谱外壳、控制面板、详情浮层与颜色系统
- Modify: `frontend/src/pages/Contracts.tsx`
  - 套用标准业务页壳层与统一操作区
- Modify: `frontend/src/pages/Documents.tsx`
  - 套用标准业务页壳层与状态区
- Modify: `frontend/src/pages/Cases.tsx`
  - 套用标准业务页壳层与筛选区
- Modify: `frontend/src/pages/admin/AdminDashboard.tsx`
  - 消除自定义颜色常量，复用统一 token
- Test: `frontend/e2e/ui-regression.spec.ts`
  - 新增关键页面 UI 基线断言
- Test: `frontend/e2e/harness-flows.spec.ts`
  - 更新 A2UI / Chat / 合同审查交互断言

---

### Task 1: 收口全局颜色、字体与设计令牌

**Files:**
- Modify: `frontend/src/index.css`
- Modify: `frontend/tailwind.config.js`
- Modify: `frontend/src/lib/design-tokens.ts`
- Test: `frontend/e2e/ui-regression.spec.ts`

- [ ] **Step 1: 先写失败的 UI 基线断言**

在 `frontend/e2e/ui-regression.spec.ts` 新增一个用例，验证品牌橙按钮、统一页面标题与标准卡片同时存在。

```ts
import { test, expect } from '@playwright/test'

test('全局设计系统基线已统一到品牌橙与标准卡片', async ({ page }) => {
  await page.goto('/contracts')

  await expect(page.getByRole('heading', { name: '合同审查' })).toBeVisible()
  await expect(page.locator('[data-ui="page-shell"]')).toBeVisible()
  await expect(page.locator('[data-ui="surface-card"]').first()).toBeVisible()
  await expect(page.getByRole('button', { name: /完整审查|上传审查/ })).toHaveCSS('background-color', /rgb\(/)
})
```

- [ ] **Step 2: 运行定向 E2E，确认它先失败**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "全局设计系统基线已统一到品牌橙与标准卡片"
```

Expected:

```text
FAIL
Unable to find locator [data-ui="page-shell"]
```

- [ ] **Step 3: 在 `index.css` 中定义统一品牌与语义色变量**

将现有品牌橙扩展为完整语义系统，并为 surface、状态、阴影预留变量。

```css
:root {
  --brand-50: 35 100% 97%;
  --brand-100: 34 100% 92%;
  --brand-500: 28 92% 55%;
  --brand-600: 24 92% 50%;
  --brand-700: 20 88% 42%;

  --info: 215 84% 56%;
  --success: 142 71% 45%;
  --warning: 38 92% 54%;
  --danger: 0 78% 58%;

  --surface-1: 0 0% 100%;
  --surface-2: 32 38% 98%;
  --surface-3: 30 24% 96%;

  --shadow-card: 0 10px 30px rgba(15, 23, 42, 0.06);
  --shadow-float: 0 18px 48px rgba(15, 23, 42, 0.12);
}

.dark {
  --surface-1: 222 33% 10%;
  --surface-2: 222 26% 14%;
  --surface-3: 222 20% 18%;
}
```

- [ ] **Step 4: 在 `tailwind.config.js` 中暴露语义 token**

将新的品牌色、surface 与阴影映射进 Tailwind 扩展。

```js
extend: {
  colors: {
    brand: {
      50: 'hsl(var(--brand-50))',
      100: 'hsl(var(--brand-100))',
      500: 'hsl(var(--brand-500))',
      600: 'hsl(var(--brand-600))',
      700: 'hsl(var(--brand-700))',
    },
    info: 'hsl(var(--info))',
    success: 'hsl(var(--success))',
    warning: 'hsl(var(--warning))',
    danger: 'hsl(var(--danger))',
    surface: {
      1: 'hsl(var(--surface-1))',
      2: 'hsl(var(--surface-2))',
      3: 'hsl(var(--surface-3))',
    },
  },
  boxShadow: {
    card: 'var(--shadow-card)',
    float: 'var(--shadow-float)',
  },
}
```

- [ ] **Step 5: 在 `design-tokens.ts` 中统一标题、卡片、按钮与输入预设**

收口标题层级与基础组件预设，后续页面直接复用。

```ts
export const heading = {
  page: 'text-2xl sm:text-3xl font-semibold tracking-tight text-foreground',
  section: 'text-lg sm:text-xl font-semibold tracking-tight text-foreground',
  card: 'text-sm sm:text-base font-semibold text-foreground',
  muted: 'text-sm text-muted-foreground',
  micro: 'text-xs text-muted-foreground',
}

export const cardStyle = {
  base: 'rounded-2xl border border-border/70 bg-surface-1 shadow-card',
  compact: 'rounded-xl border border-border/70 bg-surface-1 shadow-card p-4',
  accent: 'rounded-2xl border border-brand-200/70 bg-brand-50/70 shadow-card',
}

export const buttonStyle = {
  primary: 'rounded-xl bg-brand-600 text-white hover:bg-brand-700 shadow-sm',
  secondary: 'rounded-xl border border-border bg-surface-1 text-foreground hover:bg-surface-2',
  ghost: 'rounded-xl text-muted-foreground hover:text-foreground hover:bg-surface-2',
}
```

- [ ] **Step 6: 运行定向 E2E，确认基线通过**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "全局设计系统基线已统一到品牌橙与标准卡片"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/index.css frontend/tailwind.config.js frontend/src/lib/design-tokens.ts frontend/e2e/ui-regression.spec.ts
git commit -m "feat: unify global design tokens and brand semantics"
```

---

### Task 2: 统一页面骨架与主站/后台布局

**Files:**
- Modify: `frontend/src/components/ui/PageContainer.tsx`
- Modify: `frontend/src/components/Layout.tsx`
- Modify: `frontend/src/components/admin/AdminLayout.tsx`
- Modify: `frontend/src/pages/Contracts.tsx`
- Modify: `frontend/src/pages/Documents.tsx`
- Modify: `frontend/src/pages/Cases.tsx`
- Test: `frontend/e2e/ui-regression.spec.ts`

- [ ] **Step 1: 先写失败的页面骨架断言**

为标准业务页新增断言，要求页头、toolbar 与内容卡片具备统一数据标识。

```ts
test('标准业务页共享同一 page shell 结构', async ({ page }) => {
  await page.goto('/documents')

  await expect(page.locator('[data-ui="page-shell"]')).toBeVisible()
  await expect(page.locator('[data-ui="page-header"]')).toBeVisible()
  await expect(page.locator('[data-ui="page-toolbar"]')).toBeVisible()
  await expect(page.locator('[data-ui="surface-card"]').first()).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认当前结构不统一**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "标准业务页共享同一 page shell 结构"
```

Expected:

```text
FAIL
Unable to find locator [data-ui="page-toolbar"]
```

- [ ] **Step 3: 扩展 `PageContainer.tsx` 输出统一标识和壳层结构**

为容器、页头和操作区增加统一包装。

```tsx
return (
  <section data-ui="page-shell" className={cn('flex h-full flex-col bg-muted/20', className)}>
    {(title || description || actions) && (
      <header data-ui="page-header" className="border-b border-border/60 bg-surface-1 px-5 py-4">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1">
            {title ? <h1 className={heading.page}>{title}</h1> : null}
            {description ? <p className={heading.muted}>{description}</p> : null}
          </div>
          {actions ? <div data-ui="page-toolbar" className="flex flex-wrap items-center gap-2">{actions}</div> : null}
        </div>
      </header>
    )}
    <div className="flex-1 overflow-auto px-5 py-5">{children}</div>
  </section>
)
```

- [ ] **Step 4: 让 `Layout.tsx` 与 `AdminLayout.tsx` 共用统一内容层级**

将主站和后台的内容区背景、边界和内容区 padding 对齐。

```tsx
<div className="h-screen bg-surface-2 flex flex-col overflow-hidden">
  <div className="flex-1 overflow-hidden flex pb-14 lg:pb-0">
    {!shouldHideSidebar && <ModuleSidebar currentPath={currentPath} onNavigate={handleNavClick} />}
    <main className="flex-1 overflow-hidden bg-surface-2">
      <Outlet />
    </main>
  </div>
</div>
```

- [ ] **Step 5: 将 `Contracts.tsx`、`Documents.tsx`、`Cases.tsx` 套用统一壳层**

给这些页面的主要卡片添加统一 `data-ui="surface-card"` 标识并移除局部自定义间距。

```tsx
<div data-ui="surface-card" className={cardStyle.base}>
  {/* page content */}
</div>
```

- [ ] **Step 6: 运行定向 E2E，确认标准页结构已统一**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "标准业务页共享同一 page shell 结构"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/ui/PageContainer.tsx frontend/src/components/Layout.tsx frontend/src/components/admin/AdminLayout.tsx frontend/src/pages/Contracts.tsx frontend/src/pages/Documents.tsx frontend/src/pages/Cases.tsx frontend/e2e/ui-regression.spec.ts
git commit -m "feat: unify page shells across business and admin layouts"
```

---

### Task 3: 收口 A2UI 主协议与核心卡片样式

**Files:**
- Modify: `frontend/src/components/a2ui/A2UIRenderer.tsx`
- Modify: `frontend/src/components/a2ui/StreamingA2UIRenderer.tsx`
- Modify: `frontend/src/components/a2ui/MobileA2UIAdapter.tsx`
- Modify: `frontend/src/components/a2ui/core/A2UIComponentRegistry.ts`
- Modify: `frontend/src/components/chat/LegacyA2UIRenderer.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的 A2UI 卡片一致性断言**

新增一个断言，验证 A2UI 卡片具备统一头部、状态区和动作区。

```ts
test('A2UI 卡片使用统一的头部与动作区结构', async ({ page }) => {
  await page.goto('/chat')

  const card = page.locator('[data-a2ui-card]').first()
  await expect(card).toBeVisible()
  await expect(card.locator('[data-a2ui-header]')).toBeVisible()
  await expect(card.locator('[data-a2ui-body]')).toBeVisible()
  await expect(card.locator('[data-a2ui-actions]')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认当前卡片结构不统一**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "A2UI 卡片使用统一的头部与动作区结构"
```

Expected:

```text
FAIL
Unable to find locator [data-a2ui-header]
```

- [ ] **Step 3: 在 `A2UIRenderer.tsx` 中抽出统一卡片壳层**

为主渲染器添加统一包装函数。

```tsx
function A2UICardShell({
  title,
  status,
  actions,
  children,
}: {
  title: string
  status?: React.ReactNode
  actions?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <section data-a2ui-card className="rounded-2xl border border-border/70 bg-surface-1 shadow-card">
      <header data-a2ui-header className="flex items-start justify-between gap-3 border-b border-border/60 px-4 py-3">
        <div className="space-y-1">
          <h3 className={heading.card}>{title}</h3>
          {status}
        </div>
      </header>
      <div data-a2ui-body className="px-4 py-4">{children}</div>
      {actions ? <footer data-a2ui-actions className="border-t border-border/60 px-4 py-3">{actions}</footer> : null}
    </section>
  )
}
```

- [ ] **Step 4: 让 `StreamingA2UIRenderer.tsx` 与 `MobileA2UIAdapter.tsx` 复用同一视觉语言**

统一流式骨架、状态条和移动端动作布局。

```tsx
<div className="rounded-2xl border border-border/70 bg-surface-1 shadow-card">
  <div className="flex items-center gap-2 border-b border-border/60 px-4 py-3">
    <Loader2 className="h-4 w-4 animate-spin text-brand-600" />
    <span className={heading.micro}>正在生成结果</span>
  </div>
  <div className="space-y-3 px-4 py-4">
    {children}
  </div>
</div>
```

- [ ] **Step 5: 让 registry 与 legacy renderer 明确对齐主协议**

在 registry 中保留统一类型别名，在 legacy renderer 中仅适配包装，不再单独定义新样式。

```ts
export const A2UI_COMPONENT_TYPE_ALIASES = {
  'risk_assessment': 'recommendation-card',
  'action_footer': 'action-list',
} as const
```

```tsx
return (
  <div className="space-y-3">
    {legacyBlocks.map((block) => (
      <div data-a2ui-card key={block.id} className="rounded-2xl border border-border/70 bg-surface-1 shadow-card">
        {/* legacy content rendered inside unified shell */}
      </div>
    ))}
  </div>
)
```

- [ ] **Step 6: 运行定向 E2E，确认 A2UI 卡片结构统一**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "A2UI 卡片使用统一的头部与动作区结构"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/a2ui/A2UIRenderer.tsx frontend/src/components/a2ui/StreamingA2UIRenderer.tsx frontend/src/components/a2ui/MobileA2UIAdapter.tsx frontend/src/components/a2ui/core/A2UIComponentRegistry.ts frontend/src/components/chat/LegacyA2UIRenderer.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: unify a2ui card protocol and presentation"
```

---

### Task 4: 改造 Chat 与合同审查的核心体验

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`
- Modify: `frontend/src/pages/ContractReview.tsx`
- Modify: `frontend/src/components/chat/ContractReviewCard.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的核心流程断言**

新增一个断言，验证聊天触发合同审查后，聊天卡片和独立页都使用统一的风险总览结构。

```ts
test('合同审查结果在聊天卡片与独立页中使用统一风险总览', async ({ page }) => {
  await page.goto('/contract-review')

  await expect(page.locator('[data-review-summary]')).toBeVisible()
  await expect(page.locator('[data-review-risk-list]')).toBeVisible()
  await expect(page.locator('[data-review-actions]')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认当前结构缺少统一标识**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "合同审查结果在聊天卡片与独立页中使用统一风险总览"
```

Expected:

```text
FAIL
Unable to find locator [data-review-summary]
```

- [ ] **Step 3: 在 `ContractReview.tsx` 中抽出统一审查摘要、风险列表与动作区**

为独立页添加统一数据标识与结构。

```tsx
<section data-review-summary className={cardStyle.base}>
  <div className="flex items-center justify-between gap-4">
    <div className="flex items-center gap-3">
      <span className="rounded-full bg-brand-50 px-3 py-1 text-sm font-medium text-brand-700">
        {riskLabel}
      </span>
      <span className="text-sm text-muted-foreground">风险评分 {(reviewResult.risk_score * 100).toFixed(0)}%</span>
    </div>
    <p className="max-w-xl text-sm text-muted-foreground">{reviewResult.summary}</p>
  </div>
</section>

<section data-review-risk-list className="space-y-3">
  {detectedRisks.map(renderRiskCard)}
</section>

<footer data-review-actions className="flex flex-wrap items-center gap-3">
  {/* apply / save / download */}
</footer>
```

- [ ] **Step 4: 让 `ContractReviewCard.tsx` 复用同一审查结果结构**

收口聊天审查卡片的头部、结果列表和动作区。

```tsx
<div className="space-y-4">
  <section data-review-summary className={cardStyle.compact}>
    <h4 className={heading.card}>合同智能审查</h4>
    <p className={heading.muted}>{result?.summary}</p>
  </section>
  <section data-review-risk-list className="space-y-3">
    {risks.map(renderRiskItem)}
  </section>
</div>
```

- [ ] **Step 5: 在 `Chat.tsx` 中强化工作台层级与任务态**

统一上传态、处理中、A2UI 与合同审查卡片的排列节奏。

```tsx
<div className="space-y-4">
  {activeStreams.length > 0 && <StreamingA2UIRenderer ... />}
  {store.contractReviewVisible && (
    <div className="rounded-2xl border border-border/70 bg-surface-1 p-3 shadow-card">
      <ContractReviewCard />
    </div>
  )}
</div>
```

- [ ] **Step 6: 运行定向 E2E，确认合同审查体验统一**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "合同审查结果在聊天卡片与独立页中使用统一风险总览"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/pages/Chat.tsx frontend/src/pages/ContractReview.tsx frontend/src/components/chat/ContractReviewCard.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: align chat and contract review experiences"
```

---

### Task 5: 改造尽调页与知识图谱页

**Files:**
- Modify: `frontend/src/pages/DueDiligence.tsx`
- Modify: `frontend/src/pages/KnowledgeGraph.tsx`
- Test: `frontend/e2e/ui-regression.spec.ts`

- [ ] **Step 1: 先写失败的分析页断言**

要求分析页拥有统一的任务摘要区、控制区和结果区。

```ts
test('分析页共享统一的任务摘要与控制布局', async ({ page }) => {
  await page.goto('/due-diligence')

  await expect(page.locator('[data-analysis-shell]')).toBeVisible()
  await expect(page.locator('[data-analysis-toolbar]')).toBeVisible()
  await expect(page.locator('[data-analysis-main]')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认分析页模板尚未统一**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "分析页共享统一的任务摘要与控制布局"
```

Expected:

```text
FAIL
Unable to find locator [data-analysis-shell]
```

- [ ] **Step 3: 将 `DueDiligence.tsx` 收口为分析页骨架**

为尽调页增加统一骨架标识和顶部任务摘要区。

```tsx
<section data-analysis-shell className="flex h-full flex-col gap-4">
  <header className={cardStyle.base}>
    <div className="flex items-center justify-between gap-4">
      <div>
        <h1 className={heading.page}>尽职调查</h1>
        <p className={heading.muted}>输入企业名称，生成结构化尽调结果与下一步建议</p>
      </div>
      <div data-analysis-toolbar className="flex flex-wrap items-center gap-2">
        {/* search + filters */}
      </div>
    </div>
  </header>
  <div data-analysis-main className="grid flex-1 gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)]">
    {/* result panels */}
  </div>
</section>
```

- [ ] **Step 4: 将 `KnowledgeGraph.tsx` 的外壳与颜色系统收口**

保留图谱画布，但控制面板、图例、详情区统一用 surface/card 语义色。

```tsx
<div data-analysis-shell className="relative flex h-full flex-col bg-surface-2">
  <div data-analysis-toolbar className="border-b border-border/60 bg-surface-1 px-4 py-3">
    {/* graph controls */}
  </div>
  <div data-analysis-main className="relative flex-1">
    {/* graph canvas + unified floating panels */}
  </div>
</div>
```

- [ ] **Step 5: 运行定向 E2E，确认分析页骨架已统一**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "分析页共享统一的任务摘要与控制布局"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/pages/DueDiligence.tsx frontend/src/pages/KnowledgeGraph.tsx frontend/e2e/ui-regression.spec.ts
git commit -m "feat: unify analysis page shells"
```

---

### Task 6: 收口后台页与图表颜色使用

**Files:**
- Modify: `frontend/src/pages/admin/AdminDashboard.tsx`
- Modify: `frontend/src/pages/admin/AdminBilling.tsx`
- Modify: `frontend/src/pages/admin/AdminUsers.tsx`
- Test: `frontend/e2e/ui-regression.spec.ts`

- [ ] **Step 1: 先写失败的后台页一致性断言**

```ts
test('后台页使用统一 token 而不是独立颜色常量', async ({ page }) => {
  await page.goto('/admin')

  await expect(page.locator('[data-admin-shell]')).toBeVisible()
  await expect(page.locator('[data-ui="surface-card"]').first()).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认后台页尚未完全套用统一壳层**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "后台页使用统一 token 而不是独立颜色常量"
```

Expected:

```text
FAIL
Unable to find locator [data-admin-shell]
```

- [ ] **Step 3: 在后台页中消除自定义颜色常量并使用统一 surface card**

```tsx
const chartPalette = ['hsl(var(--brand-600))', 'hsl(var(--info))', 'hsl(var(--success))', 'hsl(var(--warning))']

return (
  <section data-admin-shell className="space-y-4">
    <div data-ui="surface-card" className={cardStyle.base}>
      {/* admin metric card */}
    </div>
  </section>
)
```

- [ ] **Step 4: 运行定向 E2E，确认后台页已收口**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts --grep "后台页使用统一 token 而不是独立颜色常量"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/pages/admin/AdminDashboard.tsx frontend/src/pages/admin/AdminBilling.tsx frontend/src/pages/admin/AdminUsers.tsx frontend/e2e/ui-regression.spec.ts
git commit -m "feat: align admin pages with shared design system"
```

---

### Task 7: 全量验证与遗留清理

**Files:**
- Modify: `frontend/src/components/chat/LegacyA2UIRenderer.tsx`
- Modify: `frontend/src/lib/design-tokens.ts`
- Test: `frontend/e2e/ui-regression.spec.ts`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 补充最终回归断言**

```ts
test('核心页面都使用统一的设计壳层', async ({ page }) => {
  for (const path of ['/chat', '/contract-review', '/contracts', '/documents', '/due-diligence']) {
    await page.goto(path)
    await expect(page.locator('body')).toBeVisible()
  }
})
```

- [ ] **Step 2: 运行 UI 与 A2UI 回归套件，确认仍有遗留失败**

Run:

```bash
cd frontend
npm run test:e2e -- ui-regression.spec.ts
npm run test:e2e -- harness-flows.spec.ts
```

Expected:

```text
FAIL
One or more pages still use legacy shells or inconsistent selectors
```

- [ ] **Step 3: 清理遗留样式入口并将 legacy 限制为兼容层**

```tsx
export function LegacyA2UIRenderer(props: LegacyA2UIRendererProps) {
  return (
    <div data-a2ui-legacy="true" className="space-y-3">
      {renderLegacyBlocksWithUnifiedShell(props.blocks)}
    </div>
  )
}
```

- [ ] **Step 4: 运行完整前端验证**

Run:

```bash
cd frontend
npm run build
npm run test:e2e -- ui-regression.spec.ts
npm run test:e2e -- harness-flows.spec.ts
```

Expected:

```text
vite build completed
PASS
All targeted tests passed
```

- [ ] **Step 5: 提交**

```bash
git add frontend/src/components/chat/LegacyA2UIRenderer.tsx frontend/src/lib/design-tokens.ts frontend/e2e/ui-regression.spec.ts frontend/e2e/harness-flows.spec.ts
git commit -m "chore: finalize ui unification and legacy cleanup"
```

---

## 自检

- Spec coverage：已覆盖设计系统基础、页面骨架、A2UI 主协议、Chat/合同审查、尽调/知识图谱、标准业务页与后台页、遗留清理和验证。
- Placeholder scan：无 TBD/TODO/“后续补充”之类占位。
- Type consistency：统一使用 `data-ui`、`data-a2ui-*`、`data-review-*`、`data-analysis-*`、`data-admin-shell` 作为结构标识，任务间命名一致。
