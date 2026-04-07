# 模板深度融入知识库 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将聊天输入区中的模板能力从独立入口彻底移除，并作为知识库资源类型深度融入统一资源选择器，同时保持单行编排栏布局为“知识库在左、高频动作居中、更多在右”。

**Architecture:** 以 `InputOrchestrationBar` 为单行布局容器，调整顺序为“知识库 → 快速咨询 / 合同审查 / 文书起草 → 更多”。将 `KnowledgeBaseSelector` 升级为统一资源选择器，新增模板资源视图与模板选中状态；`QuickActionsBar` 则删除模板 UI 和模板弹层，只保留动作入口与低频动作收纳。聊天发送链路在 `Chat.tsx` 与 `api.ts` 中显式带出模板上下文，避免继续依赖旧的模板提示词注入。

**Tech Stack:** React 18、TypeScript、Tailwind CSS、Radix Popover、framer-motion、Playwright

---

## 文件结构

- Modify: `frontend/src/components/chat/InputOrchestrationBar.tsx`
  - 调整单行编排栏顺序，保证知识库左侧、更多右侧
- Modify: `frontend/src/components/chat/QuickActionsBar.tsx`
  - 删除模板入口、模板弹层和模板相关状态
  - 仅保留 3 个高频动作与更多菜单
- Modify: `frontend/src/components/chat/KnowledgeBaseSelector.tsx`
  - 升级为统一资源选择器
  - 引入模板资源视图、模板选中态与状态摘要
- Modify: `frontend/src/components/chat/TemplateSelector.tsx`
  - 退出聊天主链路，如无其他引用则删除或降级为资源数据导出
- Modify: `frontend/src/pages/Chat.tsx`
  - 管理知识库 + 模板的会话级上下文状态
  - 发送消息时显式附带模板上下文
- Modify: `frontend/src/lib/api.ts`
  - 扩展聊天请求类型，支持模板上下文字段
- Modify: `frontend/e2e/harness-flows.spec.ts`
  - 更新输入区布局断言、模板移除断言、知识库资源视图断言

---

### Task 1: 固定单行编排栏顺序并删除主栏模板入口

**Files:**
- Modify: `frontend/src/components/chat/InputOrchestrationBar.tsx`
- Modify: `frontend/src/components/chat/QuickActionsBar.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的布局断言**

在 `frontend/e2e/harness-flows.spec.ts` 里新增一个用例，验证单行编排栏的可见入口顺序为“知识库 → 快速咨询 → 合同审查 → 文书起草 → 更多”，且主栏不再出现模板。

```ts
test('输入编排栏固定为知识库在左更多在右且无模板主入口', async ({ page }, testInfo) => {
  test.skip(testInfo.project.name === 'mobile', 'mobile has a compact layout')

  const bar = page.getByTestId('input-orchestration-bar')

  await expect(bar.getByTestId('knowledge-base-trigger')).toBeVisible()
  await expect(bar.getByRole('button', { name: '快速咨询' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '合同审查' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '文书起草' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '更多' })).toBeVisible()
  await expect(bar.getByRole('button', { name: '模板' })).not.toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认现状先失败**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "输入编排栏固定为知识库在左更多在右且无模板主入口" --project=chromium
```

Expected:

```text
FAIL
Expected locator to be visible / or found unexpected 模板 button
```

- [ ] **Step 3: 调整 `InputOrchestrationBar` 的顺序与布局**

把知识库入口移到左侧，更多保持在 `QuickActionsBar` 内部的最右侧，并让动作区在中间占据弹性空间。

```tsx
export function InputOrchestrationBar({
  onFillInput,
  isProcessing,
  isMobile,
  activeActionId = null,
  attachmentName = null,
  selectedKbIds,
  selectedTemplateId,
  onKnowledgeSelectionChange,
  onTemplateSelectionChange,
}: InputOrchestrationBarProps) {
  return (
    <div
      data-testid="input-orchestration-bar"
      className="mb-2 flex items-center gap-1.5 overflow-hidden rounded-2xl border border-border/80 bg-background px-2.5 py-2 shadow-sm"
    >
      <KnowledgeBaseSelector
        selectedKbIds={selectedKbIds}
        selectedTemplateId={selectedTemplateId}
        onKnowledgeSelectionChange={onKnowledgeSelectionChange}
        onTemplateSelectionChange={onTemplateSelectionChange}
        disabled={isProcessing}
        embedded
      />
      <QuickActionsBar
        onFillInput={onFillInput}
        isProcessing={isProcessing}
        isMobile={isMobile}
        activeActionId={activeActionId}
        attachmentName={attachmentName}
        className="min-w-0 flex-1 overflow-hidden"
      />
    </div>
  )
}
```

- [ ] **Step 4: 删除 `QuickActionsBar` 中的模板按钮与模板弹层**

把模板从主栏与更多里彻底移除，只保留 3 个高频动作与低频动作收纳。

```tsx
const orderedActions = useMemo(
  () => actions || getPersonalizedActions(5).filter((action) => action.id !== 'qa-template'),
  [actions],
)

const maxVisible = visibleActionCount ?? (isMobile ? 2 : 3)
const visibleActions = orderedActions.slice(0, maxVisible)
const hiddenActions = orderedActions.slice(maxVisible)

return (
  <div className={className}>
    <div className="flex items-center justify-end gap-1.5 overflow-hidden whitespace-nowrap">
      {visibleActions.map((action) => renderActionButton(action))}
      {hiddenActions.length > 0 ? (
        <div className="relative flex-shrink-0" ref={moreRef}>
          <button ...>
            <icons.MoreHorizontal className="w-3.5 h-3.5" />
            <span>更多</span>
          </button>
          {moreOpen && createPortal(
            <div ref={portalRef}>
              <AnimatePresence>
                <motion.div ...>
                  {hiddenActions.map((action) => renderActionButton(action, true))}
                </motion.div>
              </AnimatePresence>
            </div>,
            document.body
          )}
        </div>
      ) : null}
    </div>
  </div>
)
```

- [ ] **Step 5: 运行新增布局断言**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "输入编排栏固定为知识库在左更多在右且无模板主入口" --project=chromium
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/chat/InputOrchestrationBar.tsx frontend/src/components/chat/QuickActionsBar.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: align chat orchestration bar and remove template entry"
```

---

### Task 2: 把知识库选择器升级为统一资源选择器

**Files:**
- Modify: `frontend/src/components/chat/KnowledgeBaseSelector.tsx`
- Modify: `frontend/src/components/chat/TemplateSelector.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的资源视图断言**

新增一个用例，验证知识库弹层中存在“全部 / 知识库 / 模板”视图，且能看到模板资源项。

```ts
test('知识库入口升级为资源选择器并包含模板视图', async ({ page }) => {
  const trigger = page.getByTestId('knowledge-base-trigger')
  await trigger.click()

  await expect(page.getByRole('tab', { name: '全部' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '知识库' })).toBeVisible()
  await expect(page.getByRole('tab', { name: '模板' })).toBeVisible()

  await page.getByRole('tab', { name: '模板' }).click()
  await expect(page.getByText('法律意见书')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认它先失败**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "知识库入口升级为资源选择器并包含模板视图" --project=chromium
```

Expected:

```text
FAIL
Unable to find role="tab" name="模板"
```

- [ ] **Step 3: 在 `KnowledgeBaseSelector.tsx` 中定义统一资源模型**

把知识库与模板统一到一个资源列表结构中，模板先沿用内置模板数据。

```tsx
type ResourceType = 'knowledge' | 'template'

interface TemplateResource {
  id: string
  name: string
  description?: string
  resourceType: 'template'
}

interface KnowledgeResource extends KnowledgeBase {
  resourceType: 'knowledge'
}

type ContextResource = TemplateResource | KnowledgeResource

const BUILTIN_TEMPLATES: TemplateResource[] = [
  { id: 'nda', name: '保密协议', description: '适用于商业合作前的保密约定', resourceType: 'template' },
  { id: 'labor', name: '劳动合同', description: '标准劳动合同模板', resourceType: 'template' },
  { id: 'service', name: '服务协议', description: '技术/咨询服务合同', resourceType: 'template' },
  { id: 'lawyer-letter', name: '律师函', description: '催告、警告、协商函', resourceType: 'template' },
  { id: 'legal-opinion', name: '法律意见书', description: '专项法律问题分析意见', resourceType: 'template' },
]
```

- [ ] **Step 4: 为弹层增加资源类型切换与统一列表**

在弹层顶部加入视图切换，并把知识库与模板用统一卡片结构渲染。

```tsx
const [resourceView, setResourceView] = useState<'all' | 'knowledge' | 'template'>('all')

const allResources = useMemo<ContextResource[]>(
  () => [
    ...knowledgeBases.map((kb) => ({ ...kb, resourceType: 'knowledge' as const })),
    ...BUILTIN_TEMPLATES,
  ],
  [knowledgeBases],
)

const filteredResources = useMemo(() => {
  const keyword = searchQuery.trim().toLowerCase()
  return allResources.filter((item) => {
    const matchesType = resourceView === 'all' || item.resourceType === resourceView
    const haystack = [item.name, item.description].filter(Boolean).join(' ').toLowerCase()
    const matchesQuery = !keyword || haystack.includes(keyword)
    return matchesType && matchesQuery
  })
}, [allResources, resourceView, searchQuery])
```

```tsx
<div className="flex items-center gap-1 rounded-lg bg-muted p-1">
  {['all', 'knowledge', 'template'].map((view) => (
    <button
      key={view}
      type="button"
      role="tab"
      aria-selected={resourceView === view}
      onClick={() => setResourceView(view as 'all' | 'knowledge' | 'template')}
      className={resourceView === view ? 'bg-background text-foreground shadow-sm ...' : 'text-muted-foreground ...'}
    >
      {view === 'all' ? '全部' : view === 'knowledge' ? '知识库' : '模板'}
    </button>
  ))}
</div>
```

- [ ] **Step 5: 让 `TemplateSelector.tsx` 退出聊天链路**

把内置模板数据迁移到 `KnowledgeBaseSelector` 使用；如果聊天页中已无引用，则删除 `TemplateSelector.tsx`；如果暂时保留，则至少将其改为只导出模板常量。

```ts
export const BUILTIN_TEMPLATE_RESOURCES = [
  { id: 'nda', name: '保密协议', description: '适用于商业合作前的保密约定' },
  { id: 'labor', name: '劳动合同', description: '标准劳动合同模板' },
  { id: 'service', name: '服务协议', description: '技术/咨询服务合同' },
  { id: 'lawyer-letter', name: '律师函', description: '催告、警告、协商函' },
  { id: 'legal-opinion', name: '法律意见书', description: '专项法律问题分析意见' },
] as const
```

- [ ] **Step 6: 运行资源视图断言**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "知识库入口升级为资源选择器并包含模板视图" --project=chromium
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/chat/KnowledgeBaseSelector.tsx frontend/src/components/chat/TemplateSelector.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: turn knowledge selector into unified context resource picker"
```

---

### Task 3: 把模板选择升级为会话级上下文状态

**Files:**
- Modify: `frontend/src/components/chat/InputOrchestrationBar.tsx`
- Modify: `frontend/src/components/chat/KnowledgeBaseSelector.tsx`
- Modify: `frontend/src/pages/Chat.tsx`
- Modify: `frontend/src/lib/api.ts`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的交互断言**

新增一个用例，验证用户在知识库弹层中选择模板后，触发器文案会反映模板状态。

```ts
test('选择模板后知识库触发器显示模板上下文', async ({ page }) => {
  const trigger = page.getByTestId('knowledge-base-trigger')
  await trigger.click()
  await page.getByRole('tab', { name: '模板' }).click()
  await page.getByLabel('法律意见书').click()

  await expect(trigger).toContainText('模板')
})
```

- [ ] **Step 2: 运行定向 E2E，确认它先失败**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "选择模板后知识库触发器显示模板上下文" --project=chromium
```

Expected:

```text
FAIL
Expected string to contain "模板"
```

- [ ] **Step 3: 扩展 `Chat.tsx` 的会话级资源状态**

新增模板选中状态，并按会话维度保存。

```tsx
const [selectedKbIdsByConversation, setSelectedKbIdsByConversation] = useState<Record<string, string[]>>({})
const [selectedTemplateIdsByConversation, setSelectedTemplateIdsByConversation] = useState<Record<string, string | null>>({})

const conversationSelectionKey = conversationId || '__draft__'
const selectedKbIds = selectedKbIdsByConversation[conversationSelectionKey] || []
const selectedTemplateId = selectedTemplateIdsByConversation[conversationSelectionKey] || null

const handleSelectedTemplateChange = useCallback((templateId: string | null) => {
  setSelectedTemplateIdsByConversation((prev) => ({
    ...prev,
    [conversationSelectionKey]: templateId,
  }))
}, [conversationSelectionKey])
```

- [ ] **Step 4: 扩展 `KnowledgeBaseSelector` 触发器与回调接口**

把模板状态纳入知识库触发器文案，并支持模板单选。

```tsx
interface KnowledgeBaseSelectorProps {
  selectedKbIds: string[]
  selectedTemplateId: string | null
  onKnowledgeSelectionChange: (ids: string[]) => void
  onTemplateSelectionChange: (id: string | null) => void
  disabled?: boolean
  embedded?: boolean
}

const triggerLabel = useMemo(() => {
  if (selectedKbIds.length > 0 && selectedTemplateId) {
    return `知识库 · 资料 ${selectedKbIds.length} · 模板 1`
  }
  if (selectedTemplateId) {
    return '知识库 · 模板 1'
  }
  if (selectedKbIds.length > 0) {
    return `知识库 · ${selectedKbIds.length}`
  }
  return '知识库'
}, [selectedKbIds, selectedTemplateId])
```

- [ ] **Step 5: 扩展聊天请求协议**

在 `frontend/src/lib/api.ts` 中为聊天请求增加模板上下文字段，并在 `Chat.tsx` 发送时显式带上。

```ts
export interface ChatMessage {
  content: string
  conversation_id?: string
  case_id?: string
  agent_name?: string
  mode?: string
  knowledge_base_ids?: string[]
  template_id?: string
}
```

```tsx
const chatReq = {
  content,
  conversation_id: conversationId,
  mode: actionModeOverride ?? quickActionMode,
  knowledge_base_ids: selectedKbIds.length > 0 ? selectedKbIds : undefined,
  template_id: selectedTemplateId || undefined,
}
```

- [ ] **Step 6: 运行模板上下文断言**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "选择模板后知识库触发器显示模板上下文" --project=chromium
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 7: 提交**

```bash
git add frontend/src/components/chat/InputOrchestrationBar.tsx frontend/src/components/chat/KnowledgeBaseSelector.tsx frontend/src/pages/Chat.tsx frontend/src/lib/api.ts frontend/e2e/harness-flows.spec.ts
git commit -m "feat: persist template context in chat resource state"
```

---

### Task 4: 清理旧模板链路并完成回归验证

**Files:**
- Modify: `frontend/src/components/chat/QuickActionsBar.tsx`
- Modify: `frontend/src/pages/Chat.tsx`
- Test: `frontend/e2e/harness-flows.spec.ts`

- [ ] **Step 1: 先写失败的回归断言**

新增一个回归用例，确保文书起草仍可触发输入引导，且模板只能从知识库入口中选择。

```ts
test('文书起草保留快捷动作而模板仅存在于知识库入口', async ({ page }) => {
  const bar = page.getByTestId('input-orchestration-bar')

  await bar.getByRole('button', { name: '文书起草' }).click()
  await expect(page.getByPlaceholder(/起草|请描述/)).toBeVisible()

  await expect(bar.getByRole('button', { name: '模板' })).not.toBeVisible()
  await bar.getByTestId('knowledge-base-trigger').click()
  await page.getByRole('tab', { name: '模板' }).click()
  await expect(page.getByText('保密协议')).toBeVisible()
})
```

- [ ] **Step 2: 运行定向 E2E，确认回归场景完整**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "文书起草保留快捷动作而模板仅存在于知识库入口" --project=chromium
```

Expected:

```text
PASS
1 passed
```

- [ ] **Step 3: 清理聊天页中的旧模板依赖**

确保 `Chat.tsx` 不再依赖模板提示词注入入口，所有模板使用都经过资源上下文。

```tsx
<InputOrchestrationBar
  onFillInput={...}
  isProcessing={isProcessing}
  isMobile={isMobile}
  activeActionId={activeActionId}
  attachmentName={pendingFile?.name ?? null}
  selectedKbIds={selectedKbIds}
  selectedTemplateId={selectedTemplateId}
  onKnowledgeSelectionChange={handleSelectedKbIdsChange}
  onTemplateSelectionChange={handleSelectedTemplateChange}
/>
```

- [ ] **Step 4: 跑完整前端验证**

Run:

```bash
cd frontend
npx playwright test e2e/harness-flows.spec.ts --grep "输入编排栏固定为知识库在左更多在右且无模板主入口|知识库入口升级为资源选择器并包含模板视图|选择模板后知识库触发器显示模板上下文|文书起草保留快捷动作而模板仅存在于知识库入口" --project=chromium
npm run build
```

Expected:

```text
PASS
all selected tests passed
vite build completed successfully
```

- [ ] **Step 5: 人工预览检查**

Run:

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 3001
```

检查点：

```text
1. 输入区只有一行
2. 知识库在左，更多在右
3. 主栏不再出现模板
4. 知识库弹层有“全部 / 知识库 / 模板”
5. 选中模板后触发器文案会反映模板上下文
6. 文书起草与知识库模板组合使用时不出现重复入口
```

- [ ] **Step 6: 提交**

```bash
git add frontend/src/components/chat/QuickActionsBar.tsx frontend/src/pages/Chat.tsx frontend/e2e/harness-flows.spec.ts
git commit -m "feat: deeply integrate templates into knowledge resources"
```

---

## 自检

### Spec 覆盖

- 单行布局与左右顺序：Task 1 覆盖
- 删除模板独立入口：Task 1 + Task 4 覆盖
- 知识库升级为资源选择器：Task 2 覆盖
- 模板作为知识库资源类型：Task 2 + Task 3 覆盖
- 模板进入会话级上下文：Task 3 覆盖
- 回归验证与构建：Task 4 覆盖

### Placeholder 扫描

- 未使用 TBD / TODO / “后续补充”
- 所有实现步骤都给出明确代码方向
- 所有验证步骤都给出具体命令与预期输出

### 类型与命名一致性

- 统一使用 `selectedTemplateId` 表示模板单选状态
- 统一使用 `onKnowledgeSelectionChange` 与 `onTemplateSelectionChange` 区分两类资源回调
- 统一使用“资源选择器”表达升级后的知识库入口语义

---

Plan complete and saved to `docs/superpowers/plans/2026-04-05-template-into-knowledge-base.md`. Two execution options:

1. **Subagent-Driven (recommended)** - 我按任务逐个分发执行并在任务间复核  
2. **Inline Execution** - 我在当前会话直接按计划连续实现并分段验证

请选择一种方式。
