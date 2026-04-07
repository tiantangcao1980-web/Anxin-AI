# Chat 输入编排栏整合 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将聊天输入区的快捷动作、模板、知识库整合为单一输入编排栏，只保留少量高频入口，其余统一折叠，同时保持现有聊天工作流与业务回调不变。

**Architecture:** 在 `Chat.tsx` 上层引入新的 `InputOrchestrationBar` 容器，统一装配 `QuickActionsBar` 与 `KnowledgeBaseSelector` 的可视区域与弹层入口。复用既有动作配置、模板弹层和知识库数据逻辑，只调整组件边界、布局层级与响应式折叠规则。

**Tech Stack:** React 18、TypeScript、Tailwind CSS、framer-motion、Radix Popover、Playwright

---

## 文件结构

- Create: `frontend/src/components/chat/InputOrchestrationBar.tsx`
  - 统一输入编排栏容器
  - 负责高频动作、知识库入口、更多入口的布局和折叠
- Modify: `frontend/src/components/chat/QuickActionsBar.tsx`
  - 从完整工具栏调整为可嵌入式动作区
  - 暴露更清晰的“主动作 + 更多 + 模板”行为边界
- Modify: `frontend/src/components/chat/KnowledgeBaseSelector.tsx`
  - 支持嵌入统一编排栏
  - 将“添加知识库”按钮改为上下文态入口
- Modify: `frontend/src/pages/Chat.tsx`
  - 用 `InputOrchestrationBar` 替换当前顺序挂载的两段区域
- Modify: `frontend/e2e/harness-flows.spec.ts`
  - 更新快捷操作栏的可见性与交互断言

---

### Task 1: 创建统一输入编排栏容器

**Files:**
- Create: `frontend/src/components/chat/InputOrchestrationBar.tsx`
- Modify: `frontend/src/pages/Chat.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的界面断言**

在 `frontend/e2e/harness-flows.spec.ts` 的“快捷操作栏”分组中新增一个用例，验证聊天输入区只出现一个编排容器，并同时包含高频动作与知识库入口。

```ts
test('输入编排栏整合了动作与知识库入口', async ({ page }) => {
  const orchestrationBar = page.getByTestId('input-orchestration-bar')

  await expect(orchestrationBar).toBeVisible()
  await expect(orchestrationBar.getByRole('button', { name: '快速咨询' })).toBeVisible()
  await expect(orchestrationBar.getByRole('button', { name: '合同审查' })).toBeVisible()
  await expect(orchestrationBar.getByRole('button', { name: /知识库/ })).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认它先失败**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "输入编排栏整合了动作与知识库入口"
```

Expected:

```text
FAIL
Unable to find element by: [data-testid="input-orchestration-bar"]
```

- [ ] **Step 3: 新建 `InputOrchestrationBar` 最小实现**

创建 `frontend/src/components/chat/InputOrchestrationBar.tsx`，先只负责统一容器与现有子组件挂载，不改变业务回调。

```tsx
import { QuickActionsBar, type QuickActionFillPayload } from './QuickActionsBar'
import { KnowledgeBaseSelector } from './KnowledgeBaseSelector'

interface InputOrchestrationBarProps {
  onFillInput: (payload: QuickActionFillPayload) => void
  isProcessing: boolean
  isMobile: boolean
  activeActionId?: string | null
  attachmentName?: string | null
  selectedKbIds: string[]
  onSelectionChange: (ids: string[]) => void
}

export function InputOrchestrationBar({
  onFillInput,
  isProcessing,
  isMobile,
  activeActionId = null,
  attachmentName = null,
  selectedKbIds,
  onSelectionChange,
}: InputOrchestrationBarProps) {
  return (
    <div
      data-testid="input-orchestration-bar"
      className="mb-2 rounded-2xl border border-border/80 bg-background px-2.5 py-2 shadow-sm"
    >
      <div className="flex flex-wrap items-center gap-2">
        <QuickActionsBar
          onFillInput={onFillInput}
          isProcessing={isProcessing}
          isMobile={isMobile}
          activeActionId={activeActionId}
          attachmentName={attachmentName}
        />
        <KnowledgeBaseSelector
          selectedKbIds={selectedKbIds}
          onSelectionChange={onSelectionChange}
          disabled={isProcessing}
          embedded
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 4: 在 `Chat.tsx` 中替换现有双区装配**

把 `QuickActionsBar` 与 `KnowledgeBaseSelector` 的顺序挂载替换为统一容器。

```tsx
<InputOrchestrationBar
  onFillInput={({ text, actionId, mode: filledMode }) => {
    setInput(text)
    setActiveActionId(actionId ?? null)
    setActionModeOverride(filledMode ?? null)
    setTimeout(() => {
      const el = chatInputRef.current
      if (el) {
        el.focus()
        el.setSelectionRange(text.length, text.length)
      }
    }, 50)
  }}
  isProcessing={isProcessing}
  isMobile={isMobile}
  activeActionId={activeActionId}
  attachmentName={pendingFile?.name ?? null}
  selectedKbIds={selectedKbIds}
  onSelectionChange={handleSelectedKbIdsChange}
/>
```

- [ ] **Step 5: 运行定向 E2E，确认容器已出现**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "输入编排栏整合了动作与知识库入口"
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/chat/InputOrchestrationBar.tsx frontend/src/pages/Chat.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: add unified chat input orchestration bar shell"
```

---

### Task 2: 调整快捷动作栏为可嵌入式主动作区

**Files:**
- Modify: `frontend/src/components/chat/QuickActionsBar.tsx`
- Modify: `frontend/src/components/chat/workflowConfig.ts`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的交互断言**

新增一个用例，验证桌面端首屏只保留高频动作，扩展动作被收纳到“更多”。

```ts
test('桌面端只展示高频动作，其余收纳到更多', async ({ page }) => {
  const bar = page.getByTestId('input-orchestration-bar')

  await expect(bar.getByRole('button', { name: '快速咨询' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '合同审查' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '文书起草' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '模板' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '更多' })).toBeVisible()

  await expect(bar.getByRole('button', { name: '法律检索' })).not.toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认当前实现不满足**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "桌面端只展示高频动作，其余收纳到更多"
```

Expected:

```text
FAIL
Expected locator not to be visible
```

- [ ] **Step 3: 在 `workflowConfig.ts` 中固定高频动作顺序**

新增统一的高频动作导出，避免 `QuickActionsBar` 自己猜。

```ts
export const PRIMARY_WORKFLOW_ACTION_IDS = [
  'qa-consult',
  'qa-contract',
  'qa-draft',
  'qa-compliance',
] as const

export function getPrimaryWorkflowActions() {
  return PRIMARY_WORKFLOW_ACTION_IDS
    .map((id) => getWorkflowAction(id))
    .filter((action): action is WorkflowActionDefinition => Boolean(action))
}
```

- [ ] **Step 4: 让 `QuickActionsBar` 输出嵌入式主动作区**

将 `QuickActionsBar` 改为只负责主动作和低频动作弹层，不再自带外层 `mb-2` 和整行布局。

```tsx
const PRIMARY_VISIBLE_DESKTOP = 4
const PRIMARY_VISIBLE_MOBILE = 2

const orderedActions = actions || getPrimaryWorkflowActions().concat(
  getPersonalizedActions(MAX_VISIBLE_DESKTOP).filter(
    (action) => !PRIMARY_WORKFLOW_ACTION_IDS.includes(action.id as typeof PRIMARY_WORKFLOW_ACTION_IDS[number])
  )
)

const primaryVisible = orderedActions.slice(0, isMobile ? PRIMARY_VISIBLE_MOBILE : PRIMARY_VISIBLE_DESKTOP)
const overflowActions = orderedActions.slice(primaryVisible.length)

return (
  <div className="flex flex-wrap items-center gap-1.5">
    {primaryVisible.map((action) => renderActionButton(action))}
    <button type="button" ...>模板</button>
    {overflowActions.length > 0 ? <button type="button" ...>更多</button> : null}
  </div>
)
```

- [ ] **Step 5: 运行原有与新增断言**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "快捷操作按钮可见且可点击|桌面端只展示高频动作，其余收纳到更多"
```

Expected:

```text
PASS
2 passed
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/chat/QuickActionsBar.tsx frontend/src/components/chat/workflowConfig.ts frontend/e2e/harness-flows.spec.ts
git commit -m "feat: streamline quick actions into orchestration bar"
```

---

### Task 3: 将知识库入口改为上下文态入口

**Files:**
- Modify: `frontend/src/components/chat/KnowledgeBaseSelector.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的可见性断言**

新增一个用例，验证知识库入口使用状态化文案，而不是独立的“添加知识库”块。

```ts
test('知识库入口以内联上下文按钮展示', async ({ page }) => {
  const bar = page.getByTestId('input-orchestration-bar')
  await expect(bar.getByRole('button', { name: /知识库/ })).toBeVisible()
  await expect(page.getByText('添加知识库')).not.toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认它先失败**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "知识库入口以内联上下文按钮展示"
```

Expected:

```text
FAIL
Found text: 添加知识库
```

- [ ] **Step 3: 给 `KnowledgeBaseSelector` 增加嵌入式模式**

扩展组件 props，使其能在统一编排栏中以内联上下文按钮渲染。

```tsx
interface KnowledgeBaseSelectorProps {
  selectedKbIds: string[]
  onSelectionChange: (ids: string[]) => void
  disabled?: boolean
  embedded?: boolean
}

const triggerClassName = embedded
  ? 'inline-flex h-8 items-center gap-1.5 rounded-full border border-border/80 bg-background px-3 text-xs font-medium text-foreground/80 shadow-sm transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50'
  : 'inline-flex h-8 items-center gap-1.5 rounded-full border border-border/80 bg-background px-3 text-xs font-medium text-foreground/80 shadow-sm transition-colors hover:border-primary/40 hover:bg-primary/5 hover:text-primary disabled:cursor-not-allowed disabled:opacity-50'

const triggerLabel = selectedKbIds.length > 0
  ? `知识库 · ${selectedKbIds.length}`
  : '知识库'
```

- [ ] **Step 4: 隐藏编排栏外部的已选 Badge 行**

在 `embedded` 模式下，不在触发器前单独渲染已选知识库 `Badge` 列表，避免重新形成第二行。

```tsx
return (
  <div className={embedded ? '' : 'mb-2'}>
    <div className="flex flex-wrap items-center gap-2">
      {!embedded && selectedBases.map((kb) => (
        <Badge key={kb.id} ...>{kb.name}</Badge>
      ))}
      <Popover open={open} onOpenChange={setOpen}>
        ...
      </Popover>
    </div>
  </div>
)
```

- [ ] **Step 5: 运行定向断言和 build**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "知识库入口以内联上下文按钮展示"
npm run build
```

Expected:

```text
PASS
1 passed
vite build completed successfully
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/chat/KnowledgeBaseSelector.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: embed knowledge selector into orchestration bar"
```

---

### Task 4: 完成聊天页接入与回归验证

**Files:**
- Modify: `frontend/src/pages/Chat.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的行为断言**

新增一个回归用例，确认点击主动作后仍会填充输入框，且知识库入口仍可打开弹层。

```ts
test('统一编排栏仍可触发填充和知识库选择', async ({ page }) => {
  const bar = page.getByTestId('input-orchestration-bar')

  await bar.getByRole('button', { name: '合同审查' }).click()
  await expect(page.getByPlaceholder(/粘贴合同|上传合同/)).toBeVisible()

  await bar.getByRole('button', { name: /知识库/ }).click()
  await expect(page.getByText('选择知识库')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认接入前失败**

Run:

```bash
cd frontend
npm run test:e2e -- harness-flows.spec.ts --grep "统一编排栏仍可触发填充和知识库选择"
```

Expected:

```text
FAIL
Timed out waiting for selector
```

- [ ] **Step 3: 在 `Chat.tsx` 清理旧挂载与间距**

接入完成后，删除旧的双区块间距，让编排栏成为唯一入口层。

```tsx
<div className="flex-1 flex flex-col min-h-0">
  <AnimatePresence>...</AnimatePresence>

  <InputOrchestrationBar
    onFillInput={...}
    isProcessing={isProcessing}
    isMobile={isMobile}
    activeActionId={activeActionId}
    attachmentName={pendingFile?.name ?? null}
    selectedKbIds={selectedKbIds}
    onSelectionChange={handleSelectedKbIdsChange}
  />

  <div className={`relative flex bg-muted/50 rounded-2xl border border-border ...`}>
```

- [ ] **Step 4: 跑完整前端验证**

Run:

```bash
cd frontend
npm run build
npm run test:e2e -- harness-flows.spec.ts --grep "快捷操作|输入编排栏|知识库入口|统一编排栏"
```

Expected:

```text
PASS
all selected tests passed
```

- [ ] **Step 5: 进行人工浏览器检查**

Run:

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 3001
```

检查点：

```text
1. 聊天输入区只剩一个统一编排栏
2. 首屏可见：快速咨询、合同审查、文书起草、模板、知识库、更多
3. 宽度变窄时，扩展动作收纳到更多
4. 知识库按钮显示“知识库”或“知识库 · N”
5. 激活态、禁用态、暗色模式视觉一致
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/pages/Chat.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: integrate unified orchestration bar into chat input"
```

---

## 自检

### Spec 覆盖

- 单一编排栏：Task 1 + Task 4 覆盖
- 高频入口保留、低频折叠：Task 2 覆盖
- 知识库作为上下文入口：Task 3 覆盖
- Chat 页面只挂统一组件：Task 1 + Task 4 覆盖
- 构建与回归验证：Task 3 + Task 4 覆盖

### Placeholder 扫描

- 未使用 TBD / TODO / “后续补充”
- 所有代码步骤均给出明确代码片段
- 所有验证步骤均给出明确命令和预期

### 类型与命名一致性

- 统一使用 `InputOrchestrationBar`
- 统一使用 `embedded` 表示知识库选择器的嵌入模式
- 统一使用 `selectedKbIds` / `onSelectionChange` 作为知识库状态接口

---

Plan complete and saved to `docs/superpowers/plans/2026-04-05-chat-input-orchestration.md`. Two execution options:

1. **Subagent-Driven (recommended)** - 我按任务逐个分发执行并在任务间复核  
2. **Inline Execution** - 我在当前会话直接按计划连续实现并分段验证

请选择一种方式。
