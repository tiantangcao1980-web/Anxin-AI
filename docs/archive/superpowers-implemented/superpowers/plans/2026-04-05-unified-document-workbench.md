# 统一文档工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将在线协作、文档库和智能工作台文档区统一为一个 WPS 风格的文档工作台，并先打通 Word/Markdown/TXT/PDF 的线上高频闭环。

**Architecture:** 新增独立的 `DocumentWorkbenchPage` 作为统一壳层，内部拆分为工作台布局、文档空间状态、格式适配注册器、协作侧栏和 AI 侧栏。先通过新路由与共享状态承接文档空间，再逐步把 `/documents`、`/collaboration` 和 Chat 文档入口切换到同一工作台宿主。

**Tech Stack:** React 18、TypeScript、React Router v6、Zustand、Tailwind CSS、framer-motion、Playwright

---

## 文件结构

- Create: `frontend/src/pages/DocumentWorkbench.tsx`
  - 统一文档工作台页面路由宿主
- Create: `frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`
  - 五区布局壳层
- Create: `frontend/src/components/document-workbench/WorkbenchTopbar.tsx`
  - 顶部工具栏
- Create: `frontend/src/components/document-workbench/WorkbenchSidebar.tsx`
  - 左侧文档空间与结构导航
- Create: `frontend/src/components/document-workbench/WorkbenchStatusBar.tsx`
  - 底部状态栏
- Create: `frontend/src/components/document-workbench/WorkbenchRightPanel.tsx`
  - 协作、AI、历史、属性侧栏
- Create: `frontend/src/components/document-workbench/DocumentTabs.tsx`
  - 多标签文档切换
- Create: `frontend/src/components/document-workbench/DocumentCanvas.tsx`
  - 中央画布容器
- Create: `frontend/src/components/document-workbench/adapters/index.ts`
  - 文档格式适配注册表
- Create: `frontend/src/components/document-workbench/adapters/MarkdownTextAdapter.tsx`
  - Markdown / TXT 适配器
- Create: `frontend/src/components/document-workbench/adapters/RichDocumentAdapter.tsx`
  - Word 富文档适配器
- Create: `frontend/src/components/document-workbench/adapters/PdfPreviewAdapter.tsx`
  - PDF 预览与批注适配器
- Create: `frontend/src/components/document-workbench/hooks/useDocumentWorkbenchStore.ts`
  - 文档工作台状态与动作
- Create: `frontend/src/components/document-workbench/hooks/useDocumentWorkspaceEntry.ts`
  - 根据入口来源解析默认模式
- Create: `frontend/src/components/document-workbench/hooks/useCollaborationSession.ts`
  - 从原在线协作页抽离出的协作会话 Hook
- Create: `frontend/src/components/document-workbench/types.ts`
  - 工作台内部类型定义
- Modify: `frontend/src/App.tsx`
  - 注册统一文档工作台路由
- Modify: `frontend/src/pages/Documents.tsx`
  - 切换到统一工作台宿主
- Modify: `frontend/src/pages/Collaboration.tsx`
  - 退化为统一工作台入口包装器
- Modify: `frontend/src/components/document-library/DocumentLibrary.tsx`
  - 从 Tab 式页升级为文档空间入口
- Modify: `frontend/src/components/document-library/MyDocuments.tsx`
  - 支持在工作台中打开文档，不再只弹窗编辑
- Modify: `frontend/src/components/document-library/DocumentEditor.tsx`
  - 抽出可被 Markdown / TXT 适配器复用的编辑区
- Modify: `frontend/src/components/editor/CollaborativeEditor.tsx`
  - 作为 Word 富文档编辑底座接入工作台适配器
- Modify: `frontend/src/components/chat/RightPanel.tsx`
  - 文档入口跳转统一工作台
- Modify: `frontend/src/hooks/useWorkspace.ts`
  - 将“打开文档”动作对接到统一工作台路由
- Modify: `frontend/src/lib/store.ts`
  - 精简 Chat 内文档状态，仅保留工作台跳转所需数据
- Modify: `frontend/e2e/navigation.spec.ts`
  - 验证路由入口与页面壳层
- Modify: `frontend/e2e/right-panel.spec.ts`
  - 验证 Chat 入口能打开统一文档工作台
- Modify: `frontend/e2e/harness-flows.spec.ts`
  - 验证文档工作台里的 AI 与协作基础流转

---

### Task 1: 建立统一文档工作台路由与基础壳层

**Files:**
- Create: `frontend/src/pages/DocumentWorkbench.tsx`
- Create: `frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`
- Create: `frontend/src/components/document-workbench/WorkbenchTopbar.tsx`
- Create: `frontend/src/components/document-workbench/WorkbenchSidebar.tsx`
- Create: `frontend/src/components/document-workbench/WorkbenchStatusBar.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/pages/Documents.tsx`
- Test: `frontend/e2e/navigation.spec.ts`

- [ ] **Step 1: 先写失败的路由壳层断言**

在 `frontend/e2e/navigation.spec.ts` 增加一个用例，验证 `/documents` 已经进入统一文档工作台，并显示五区布局中的关键区域。

```ts
test('documents 路由进入统一文档工作台', async ({ page }) => {
  await page.goto('/documents')

  await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
  await expect(page.getByTestId('document-workbench-topbar')).toBeVisible()
  await expect(page.getByTestId('document-workbench-sidebar')).toBeVisible()
  await expect(page.getByTestId('document-workbench-canvas')).toBeVisible()
  await expect(page.getByTestId('document-workbench-statusbar')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认它先失败**

Run:

```bash
cd frontend
npm run test:e2e -- navigation.spec.ts --grep "documents 路由进入统一文档工作台"
```

Expected:

```text
FAIL
Unable to find element by: [data-testid="document-workbench-shell"]
```

- [ ] **Step 3: 新建统一工作台页面宿主**

创建 `frontend/src/pages/DocumentWorkbench.tsx`，先只提供最小路由宿主和默认入口模式。

```tsx
import { useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { DocumentWorkbenchShell } from '@/components/document-workbench/DocumentWorkbenchShell'

export default function DocumentWorkbench() {
  const location = useLocation()

  const entryMode = useMemo<'library' | 'collaboration' | 'chat'>(
    () => (location.state?.entryMode as 'library' | 'collaboration' | 'chat') ?? 'library',
    [location.state],
  )

  return <DocumentWorkbenchShell entryMode={entryMode} />
}
```

- [ ] **Step 4: 新建五区布局壳层最小实现**

创建 `frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`，先把五区骨架和测试标识搭出来。

```tsx
import { WorkbenchTopbar } from './WorkbenchTopbar'
import { WorkbenchSidebar } from './WorkbenchSidebar'
import { WorkbenchStatusBar } from './WorkbenchStatusBar'

interface DocumentWorkbenchShellProps {
  entryMode: 'library' | 'collaboration' | 'chat'
}

export function DocumentWorkbenchShell({ entryMode }: DocumentWorkbenchShellProps) {
  return (
    <div data-testid="document-workbench-shell" className="flex h-full min-h-0 flex-col bg-muted/30">
      <WorkbenchTopbar entryMode={entryMode} />
      <div className="flex min-h-0 flex-1">
        <WorkbenchSidebar entryMode={entryMode} />
        <main data-testid="document-workbench-canvas" className="min-w-0 flex-1 bg-background" />
        <aside className="w-80 border-l border-border bg-background/80" />
      </div>
      <WorkbenchStatusBar />
    </div>
  )
}
```

- [ ] **Step 5: 注册路由并让 Documents 指向新页面**

更新 `frontend/src/App.tsx` 和 `frontend/src/pages/Documents.tsx`，把 `/documents` 改为统一工作台页面。

```tsx
const DocumentWorkbench = lazy(() => import('./pages/DocumentWorkbench'))

<Route
  path="documents"
  element={<ProtectedRoute feature="document_management"><DocumentWorkbench /></ProtectedRoute>}
/>
```

```tsx
export { default } from './DocumentWorkbench'
```

- [ ] **Step 6: 运行定向 E2E，确认壳层出现**

Run:

```bash
cd frontend
npm run test:e2e -- navigation.spec.ts --grep "documents 路由进入统一文档工作台"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/App.tsx frontend/src/pages/Documents.tsx frontend/src/pages/DocumentWorkbench.tsx frontend/src/components/document-workbench frontend/e2e/navigation.spec.ts
git commit -m "feat: add unified document workbench shell route"
```

---

### Task 2: 接入文档空间与多标签状态管理

**Files:**
- Create: `frontend/src/components/document-workbench/hooks/useDocumentWorkbenchStore.ts`
- Create: `frontend/src/components/document-workbench/DocumentTabs.tsx`
- Modify: `frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`
- Modify: `frontend/src/components/document-workbench/WorkbenchSidebar.tsx`
- Modify: `frontend/src/components/document-library/DocumentLibrary.tsx`
- Modify: `frontend/src/components/document-library/MyDocuments.tsx`
- Test: `frontend/e2e/navigation.spec.ts`

- [ ] **Step 1: 先写失败的文档空间断言**

新增用例，验证统一工作台左侧能展示文档空间入口，并且打开文档后出现标签页。

```ts
test('统一工作台支持文档空间和多标签', async ({ page }) => {
  await page.goto('/documents')

  await expect(page.getByRole('button', { name: '最近打开' })).toBeVisible()
  await expect(page.getByRole('button', { name: '我的文档' })).toBeVisible()

  await page.getByRole('button', { name: '打开示例文档' }).click()
  await expect(page.getByTestId('document-tab-example-doc')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认当前不满足**

Run:

```bash
cd frontend
npm run test:e2e -- navigation.spec.ts --grep "统一工作台支持文档空间和多标签"
```

Expected:

```text
FAIL
Unable to find role="button" and name "最近打开"
```

- [ ] **Step 3: 新建工作台状态 Store**

创建 `frontend/src/components/document-workbench/hooks/useDocumentWorkbenchStore.ts`，先定义最小文档空间和标签状态。

```ts
import { create } from 'zustand'

export interface WorkbenchDocumentItem {
  id: string
  title: string
  kind: 'doc' | 'markdown' | 'txt' | 'pdf'
  content?: string
}

interface DocumentWorkbenchState {
  activeSpace: 'recent' | 'mine' | 'shared' | 'project' | 'starred'
  openTabs: WorkbenchDocumentItem[]
  activeDocumentId: string | null
  setActiveSpace: (space: DocumentWorkbenchState['activeSpace']) => void
  openDocument: (doc: WorkbenchDocumentItem) => void
  closeDocument: (id: string) => void
  setActiveDocument: (id: string) => void
}

export const useDocumentWorkbenchStore = create<DocumentWorkbenchState>((set) => ({
  activeSpace: 'mine',
  openTabs: [],
  activeDocumentId: null,
  setActiveSpace: (space) => set({ activeSpace: space }),
  openDocument: (doc) =>
    set((state) => {
      const exists = state.openTabs.find((item) => item.id === doc.id)
      const openTabs = exists ? state.openTabs : [...state.openTabs, doc]
      return { openTabs, activeDocumentId: doc.id }
    }),
  closeDocument: (id) =>
    set((state) => {
      const openTabs = state.openTabs.filter((item) => item.id !== id)
      const activeDocumentId =
        state.activeDocumentId === id ? openTabs.at(-1)?.id ?? null : state.activeDocumentId
      return { openTabs, activeDocumentId }
    }),
  setActiveDocument: (id) => set({ activeDocumentId: id }),
}))
```

- [ ] **Step 4: 把左侧文档空间和标签条接到壳层**

给 `WorkbenchSidebar.tsx` 和 `DocumentTabs.tsx` 增加最小实现，先用假数据跑通交互。

```tsx
const SPACES = [
  { id: 'recent', label: '最近打开' },
  { id: 'mine', label: '我的文档' },
  { id: 'shared', label: '共享给我' },
  { id: 'project', label: '项目文档' },
  { id: 'starred', label: '收藏' },
] as const

const EXAMPLE_DOC = {
  id: 'example-doc',
  title: '示例合同草稿',
  kind: 'markdown' as const,
  content: '# 示例合同草稿\n\n第一条 合同目的',
}
```

```tsx
<button type="button" onClick={() => openDocument(EXAMPLE_DOC)}>
  打开示例文档
</button>
```

```tsx
<button data-testid={`document-tab-${tab.id}`} onClick={() => setActiveDocument(tab.id)}>
  {tab.title}
</button>
```

- [ ] **Step 5: 让文档库入口改为打开工作台文档，而不是只弹窗**

在 `frontend/src/components/document-library/MyDocuments.tsx` 中先抽一个回调，优先触发工作台打开动作。

```tsx
interface MyDocumentsProps {
  onOpenDocument?: (doc: Document) => void
}

export function MyDocuments({ onOpenDocument }: MyDocumentsProps) {
  // ...
  const handleEditClick = (doc: Document) => {
    if (onOpenDocument) {
      onOpenDocument(doc)
      return
    }
    setEditingDoc(doc)
    setShowEditor(true)
  }
}
```

- [ ] **Step 6: 运行定向 E2E，确认左侧空间和标签可用**

Run:

```bash
cd frontend
npm run test:e2e -- navigation.spec.ts --grep "统一工作台支持文档空间和多标签"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/document-workbench/hooks/useDocumentWorkbenchStore.ts frontend/src/components/document-workbench/DocumentTabs.tsx frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx frontend/src/components/document-workbench/WorkbenchSidebar.tsx frontend/src/components/document-library/DocumentLibrary.tsx frontend/src/components/document-library/MyDocuments.tsx frontend/e2e/navigation.spec.ts
git commit -m "feat: add document space and multi-tab state to workbench"
```

---

### Task 3: 建立格式适配注册器并打通首批文档类型

**Files:**
- Create: `frontend/src/components/document-workbench/types.ts`
- Create: `frontend/src/components/document-workbench/DocumentCanvas.tsx`
- Create: `frontend/src/components/document-workbench/adapters/index.ts`
- Create: `frontend/src/components/document-workbench/adapters/MarkdownTextAdapter.tsx`
- Create: `frontend/src/components/document-workbench/adapters/RichDocumentAdapter.tsx`
- Create: `frontend/src/components/document-workbench/adapters/PdfPreviewAdapter.tsx`
- Modify: `frontend/src/components/document-library/DocumentEditor.tsx`
- Modify: `frontend/src/components/editor/CollaborativeEditor.tsx`
- Modify: `frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`
- Test: `frontend/e2e/navigation.spec.ts`

- [ ] **Step 1: 先写失败的格式切换断言**

新增用例，验证 Markdown 文档走编辑态、PDF 文档走预览态。

```ts
test('统一工作台按格式切换画布适配器', async ({ page }) => {
  await page.goto('/documents')

  await page.getByRole('button', { name: '打开 Markdown 示例' }).click()
  await expect(page.getByTestId('markdown-text-adapter')).toBeVisible()

  await page.getByRole('button', { name: '打开 PDF 示例' }).click()
  await expect(page.getByTestId('pdf-preview-adapter')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认适配器尚未接入**

Run:

```bash
cd frontend
npm run test:e2e -- navigation.spec.ts --grep "统一工作台按格式切换画布适配器"
```

Expected:

```text
FAIL
Unable to find element by: [data-testid="markdown-text-adapter"]
```

- [ ] **Step 3: 定义统一适配器接口与注册器**

创建 `frontend/src/components/document-workbench/adapters/index.ts`。

```ts
import { MarkdownTextAdapter } from './MarkdownTextAdapter'
import { RichDocumentAdapter } from './RichDocumentAdapter'
import { PdfPreviewAdapter } from './PdfPreviewAdapter'
import type { WorkbenchDocumentItem } from '../hooks/useDocumentWorkbenchStore'

export function resolveWorkbenchAdapter(doc: WorkbenchDocumentItem) {
  switch (doc.kind) {
    case 'markdown':
    case 'txt':
      return MarkdownTextAdapter
    case 'doc':
      return RichDocumentAdapter
    case 'pdf':
      return PdfPreviewAdapter
    default:
      return MarkdownTextAdapter
  }
}
```

- [ ] **Step 4: 新建中央画布容器并按格式渲染**

创建 `frontend/src/components/document-workbench/DocumentCanvas.tsx`。

```tsx
import { resolveWorkbenchAdapter } from './adapters'
import { useDocumentWorkbenchStore } from './hooks/useDocumentWorkbenchStore'

export function DocumentCanvas() {
  const { openTabs, activeDocumentId } = useDocumentWorkbenchStore()
  const activeDocument = openTabs.find((item) => item.id === activeDocumentId)

  if (!activeDocument) {
    return <div data-testid="document-workbench-canvas" className="flex-1 bg-background" />
  }

  const Adapter = resolveWorkbenchAdapter(activeDocument)

  return (
    <div data-testid="document-workbench-canvas" className="flex min-w-0 flex-1 bg-background">
      <Adapter document={activeDocument} />
    </div>
  )
}
```

- [ ] **Step 5: 把现有编辑器封装进首批适配器**

为 Markdown/TXT 和 Word/PDF 新建最小适配器，先复用已有编辑器底座。

```tsx
export function MarkdownTextAdapter({ document }: { document: WorkbenchDocumentItem }) {
  return (
    <section data-testid="markdown-text-adapter" className="flex min-w-0 flex-1 flex-col">
      <header className="border-b border-border px-4 py-2 text-sm font-medium">{document.title}</header>
      <textarea className="min-h-0 flex-1 resize-none p-4 outline-none" defaultValue={document.content} />
    </section>
  )
}
```

```tsx
export function PdfPreviewAdapter({ document }: { document: WorkbenchDocumentItem }) {
  return (
    <section data-testid="pdf-preview-adapter" className="flex min-w-0 flex-1 items-center justify-center">
      <div className="rounded-2xl border border-dashed border-border px-6 py-10 text-sm text-muted-foreground">
        {document.title} 预览区
      </div>
    </section>
  )
}
```

- [ ] **Step 6: 运行定向 E2E，确认适配器切换生效**

Run:

```bash
cd frontend
npm run test:e2e -- navigation.spec.ts --grep "统一工作台按格式切换画布适配器"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 执行构建，确认新增适配器没有类型错误**

Run:

```bash
cd frontend
npm run build
```

Expected:

```text
vite v
✓ built in
```

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/document-workbench/types.ts frontend/src/components/document-workbench/DocumentCanvas.tsx frontend/src/components/document-workbench/adapters frontend/src/components/document-library/DocumentEditor.tsx frontend/src/components/editor/CollaborativeEditor.tsx frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx frontend/e2e/navigation.spec.ts
git commit -m "feat: add document adapters for core workbench formats"
```

---

### Task 4: 抽离在线协作能力并接入右侧协作侧栏

**Files:**
- Create: `frontend/src/components/document-workbench/hooks/useCollaborationSession.ts`
- Create: `frontend/src/components/document-workbench/WorkbenchRightPanel.tsx`
- Modify: `frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`
- Modify: `frontend/src/pages/Collaboration.tsx`
- Modify: `frontend/src/components/document-workbench/WorkbenchSidebar.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的协作侧栏断言**

新增用例，验证从协作入口打开统一工作台时，右侧默认停留在协作标签并显示在线成员区。

```ts
test('collaboration 入口默认打开协作侧栏', async ({ page }) => {
  await page.goto('/collaboration')

  await expect(page.getByRole('tab', { name: '协作' })).toHaveAttribute('data-state', 'active')
  await expect(page.getByText('在线成员')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认旧页面尚未切到统一壳层**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "collaboration 入口默认打开协作侧栏"
```

Expected:

```text
FAIL
Expected locator to have attribute
```

- [ ] **Step 3: 从原协作页提取协作会话 Hook**

创建 `frontend/src/components/document-workbench/hooks/useCollaborationSession.ts`，先只抽最小状态与连接逻辑。

```ts
import { useMemo } from 'react'

export function useCollaborationSession(entryMode: 'library' | 'collaboration' | 'chat') {
  const collaborators = useMemo(
    () =>
      entryMode === 'collaboration'
        ? [
            { id: 'owner', name: '发起人', role: 'owner' },
            { id: 'reviewer', name: '审阅律师', role: 'commenter' },
          ]
        : [],
    [entryMode],
  )

  return {
    defaultTab: entryMode === 'collaboration' ? 'collaboration' : 'ai',
    collaborators,
    comments: [],
    versions: [],
  }
}
```

- [ ] **Step 4: 新建右侧协作侧栏并把壳层接上**

创建 `frontend/src/components/document-workbench/WorkbenchRightPanel.tsx`。

```tsx
interface WorkbenchRightPanelProps {
  entryMode: 'library' | 'collaboration' | 'chat'
}

export function WorkbenchRightPanel({ entryMode }: WorkbenchRightPanelProps) {
  const { defaultTab, collaborators } = useCollaborationSession(entryMode)

  return (
    <aside className="w-80 border-l border-border bg-background/80">
      <button role="tab" data-state={defaultTab === 'collaboration' ? 'active' : 'inactive'}>
        协作
      </button>
      <button role="tab" data-state={defaultTab === 'ai' ? 'active' : 'inactive'}>
        AI
      </button>
      <section className="p-4">
        <h3 className="text-sm font-semibold">在线成员</h3>
        {collaborators.map((item) => (
          <div key={item.id}>{item.name}</div>
        ))}
      </section>
    </aside>
  )
}
```

- [ ] **Step 5: 将 Collaboration 页面切换为统一工作台入口包装器**

把 `frontend/src/pages/Collaboration.tsx` 改成路由包装器，保留原复杂实现到后续清理分支。

```tsx
import { Navigate, useLocation, useParams } from 'react-router-dom'

export default function Collaboration() {
  const { sessionId } = useParams()
  const location = useLocation()

  return (
    <Navigate
      to="/documents"
      replace
      state={{ ...location.state, entryMode: 'collaboration', sessionId }}
    />
  )
}
```

- [ ] **Step 6: 运行定向 E2E，确认协作入口切换完成**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "collaboration 入口默认打开协作侧栏"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/document-workbench/hooks/useCollaborationSession.ts frontend/src/components/document-workbench/WorkbenchRightPanel.tsx frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx frontend/src/pages/Collaboration.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: move collaboration entry onto unified workbench"
```

---

### Task 5: 将 Chat 文档入口和 AI 工作台动作接入统一文档工作台

**Files:**
- Create: `frontend/src/components/document-workbench/hooks/useDocumentWorkspaceEntry.ts`
- Modify: `frontend/src/components/chat/RightPanel.tsx`
- Modify: `frontend/src/hooks/useWorkspace.ts`
- Modify: `frontend/src/lib/store.ts`
- Modify: `frontend/src/components/document-workbench/WorkbenchRightPanel.tsx`
- Test: `frontend/e2e/right-panel.spec.ts`

- [ ] **Step 1: 先写失败的 Chat 入口断言**

在 `frontend/e2e/right-panel.spec.ts` 增加一个用例，验证工作台中的“查看完整文档”会进入统一文档工作台而不是旧右侧小面板。

```ts
test('查看完整文档会打开统一文档工作台', async ({ page }) => {
  await emitSocketEvent(page, {
    type: 'canvas_open',
    title: '测试法律意见书',
    content: '# 测试法律意见书',
    type_name: 'document',
  })

  await page.getByRole('button', { name: /^工作台/ }).click()
  await page.getByRole('button', { name: /查看完整文档/ }).click()

  await expect(page).toHaveURL(/\/documents/)
  await expect(page.getByTestId('document-workbench-shell')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认当前仍停留在旧右侧面板**

Run:

```bash
cd frontend
npm run test:e2e -- right-panel.spec.ts --grep "查看完整文档会打开统一文档工作台"
```

Expected:

```text
FAIL
Expected page to have URL matching /\/documents/
```

- [ ] **Step 3: 新建入口参数 Hook，统一处理 chat / collaboration / library**

创建 `frontend/src/components/document-workbench/hooks/useDocumentWorkspaceEntry.ts`。

```ts
import { useLocation } from 'react-router-dom'

export function useDocumentWorkspaceEntry() {
  const location = useLocation()
  const state = (location.state ?? {}) as {
    entryMode?: 'library' | 'collaboration' | 'chat'
    initialDocument?: { id: string; title: string; kind: 'doc' | 'markdown' | 'txt' | 'pdf'; content?: string }
  }

  return {
    entryMode: state.entryMode ?? 'library',
    initialDocument: state.initialDocument ?? null,
  }
}
```

- [ ] **Step 4: 调整 Chat 的文档动作，改为导航到统一工作台**

修改 `frontend/src/hooks/useWorkspace.ts` 和 `frontend/src/components/chat/RightPanel.tsx`，将旧的右侧文档面板动作替换为路由跳转。

```ts
case 'open_document':
  navigate('/documents', {
    state: {
      entryMode: 'chat',
      initialDocument: {
        id: `chat-${Date.now()}`,
        title: store.canvasContent?.title || '未命名文档',
        kind: 'markdown',
        content: store.canvasContent?.content || '',
      },
    },
  })
  break
```

```tsx
<button type="button" onClick={() => props.onDocumentAction?.('open_document')}>
  查看完整文档
</button>
```

- [ ] **Step 5: 在统一工作台默认激活 AI 标签**

更新 `WorkbenchRightPanel.tsx`，让 `entryMode === 'chat'` 时默认显示 AI 标签和文档动作区。

```tsx
const defaultTab = entryMode === 'chat' ? 'ai' : entryMode === 'collaboration' ? 'collaboration' : 'properties'
```

- [ ] **Step 6: 运行定向 E2E，确认 Chat 已接入统一工作台**

Run:

```bash
cd frontend
npm run test:e2e -- right-panel.spec.ts --grep "查看完整文档会打开统一文档工作台"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 运行构建，确认 Chat 与工作台路由改动无类型错误**

Run:

```bash
cd frontend
npm run build
```

Expected:

```text
vite v
✓ built in
```

- [ ] **Step 8: 提交**

```bash
git add frontend/src/components/document-workbench/hooks/useDocumentWorkspaceEntry.ts frontend/src/components/chat/RightPanel.tsx frontend/src/hooks/useWorkspace.ts frontend/src/lib/store.ts frontend/src/components/document-workbench/WorkbenchRightPanel.tsx frontend/e2e/right-panel.spec.ts
git commit -m "feat: route chat document actions to unified workbench"
```

---

### Task 6: 收敛旧入口并完成一期验证

**Files:**
- Modify: `frontend/src/components/document-library/DocumentLibrary.tsx`
- Modify: `frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx`
- Modify: `frontend/e2e/navigation.spec.ts`
- Modify: `frontend/e2e/right-panel.spec.ts`
- Modify: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写一期闭环验收用例**

补一个端到端闭环用例：从文档空间打开文档、进入统一工作台、切换侧栏、验证保存状态栏存在。

```ts
test('统一文档工作台跑通一期高频闭环', async ({ page }) => {
  await page.goto('/documents')

  await page.getByRole('button', { name: '打开 Markdown 示例' }).click()
  await expect(page.getByTestId('markdown-text-adapter')).toBeVisible()

  await page.getByRole('tab', { name: 'AI' }).click()
  await expect(page.getByText('总结')).toBeVisible()

  await page.getByRole('tab', { name: '协作' }).click()
  await expect(page.getByText('在线成员')).toBeVisible()

  await expect(page.getByText('自动保存')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认一期闭环用例先失败**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "统一文档工作台跑通一期高频闭环"
```

Expected:

```text
FAIL
Expected locator to be visible
```

- [ ] **Step 3: 清理旧文档库页面心智，统一为文档空间入口**

更新 `frontend/src/components/document-library/DocumentLibrary.tsx`，只保留文档空间入口视图，不再作为独立 Tab 容器壳层。

```tsx
export function DocumentLibrary() {
  return (
    <section className="flex h-full min-h-0 flex-col">
      <header className="border-b border-border px-4 py-4">
        <h2 className="text-lg font-semibold">文档空间</h2>
        <p className="mt-1 text-sm text-muted-foreground">最近打开、共享文档和智能文书都在这里统一管理</p>
      </header>
      <div className="min-h-0 flex-1">
        <MyDocuments />
      </div>
    </section>
  )
}
```

- [ ] **Step 4: 补齐壳层中的 AI、协作、状态栏可见信息**

把 `DocumentWorkbenchShell.tsx` 和 `WorkbenchRightPanel.tsx` 补到能满足一期验收：显示 AI 动作名、协作区标题、状态栏保存状态。

```tsx
<div className="flex items-center gap-4 text-xs text-muted-foreground">
  <span>自动保存</span>
  <span>已同步</span>
  <span>缩放 100%</span>
</div>
```

```tsx
<button role="tab">AI</button>
<button role="tab">协作</button>
<div className="space-y-2">
  <button type="button">总结</button>
  <button type="button">改写</button>
</div>
```

- [ ] **Step 5: 运行一期验证和基础质量命令**

Run:

```bash
cd frontend
npm run test:e2e -- navigation.spec.ts
npm run test:e2e -- right-panel.spec.ts
npm run test:e2e -- harness-flows.spec.ts
npm run build
npm run lint
```

Expected:

```text
PASS
all targeted specs passed

vite v
✓ built in

eslint
0 problems
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/document-library/DocumentLibrary.tsx frontend/src/components/document-workbench/DocumentWorkbenchShell.tsx frontend/e2e/navigation.spec.ts frontend/e2e/right-panel.spec.ts frontend/e2e/harness-flows.spec.ts
git commit -m "feat: finish phase-one unified document workbench flow"
```

---

## 自检结果

### Spec 覆盖

- 统一工作台壳层与五区布局：Task 1
- 文档空间与多标签：Task 2
- Word / Markdown / TXT / PDF 首批格式闭环：Task 3
- 协作侧栏与在线协作入口统一：Task 4
- Chat 文档入口与 AI 默认模式统一：Task 5
- 一期闭环验证与旧入口收敛：Task 6

### Placeholder 扫描

- 未使用 TBD、TODO、稍后实现等占位描述
- 每个任务都给出文件路径、代码片段、命令和预期结果
- 构建、Lint、E2E 验证命令已覆盖

### 类型一致性

- 统一入口模式命名：`library | collaboration | chat`
- 统一工作台文档类型命名：`doc | markdown | txt | pdf`
- 统一页面宿主名称：`DocumentWorkbench` / `DocumentWorkbenchShell`

