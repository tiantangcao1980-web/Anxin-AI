/**
 * V3 任务中心(P2 真业务化)
 *
 * - 三段 Tab:进行中 / 待我审批 / 已完成
 * - 顶部:[+ 新建任务] 弹窗(选 agent_persona + 输入 payload)
 * - 右侧 Drawer(Sheet):点 TaskCard 后展示 TaskTimeline
 * - 5s 轮询刷新列表;Drawer 打开时订阅 SSE 事件流
 */

import { useEffect, useMemo, useState } from 'react'
import { Plus, RefreshCcw, XCircle } from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

import { TaskApprovalCard } from '@/components/v3/tasks/TaskApprovalCard'
import { TaskCard } from '@/components/v3/tasks/TaskCard'
import { TaskTimeline } from '@/components/v3/tasks/TaskTimeline'

import { agentTasksApi, type AgentTaskStatus } from '@/lib/api/agentTasks'
import { useAgentTasksStore } from '@/lib/store/agentTasksStore'

const POLL_INTERVAL_MS = 5_000

const PERSONA_OPTIONS = [
  { value: 'anxin_assistant', label: '🤖 安心助手(通用)' },
  { value: 'contract_steward', label: '📑 合同管家' },
  { value: 'investigator', label: '🔎 调查员' },
  { value: 'litigator', label: '⚖️ 诉讼专员' },
]

const TAB_BUCKETS: Record<'active' | 'approval' | 'finished', AgentTaskStatus[]> = {
  active: ['queued', 'provisioning', 'running', 'reporting'],
  approval: ['needs_approval'],
  finished: ['done', 'failed', 'cancelled'],
}

export default function TasksPage() {
  const tasks = useAgentTasksStore((s) => s.tasks)
  const loading = useAgentTasksStore((s) => s.loading)
  const loadError = useAgentTasksStore((s) => s.loadError)
  const selectedTaskId = useAgentTasksStore((s) => s.selectedTaskId)
  const eventsMap = useAgentTasksStore((s) => s.events)
  const loadTasks = useAgentTasksStore((s) => s.loadTasks)
  const selectTask = useAgentTasksStore((s) => s.selectTask)
  const appendEvent = useAgentTasksStore((s) => s.appendEvent)
  const clearEvents = useAgentTasksStore((s) => s.clearEvents)
  const cancelTaskAction = useAgentTasksStore((s) => s.cancelTask)

  const [tab, setTab] = useState<'active' | 'approval' | 'finished'>('active')
  const [createOpen, setCreateOpen] = useState(false)

  // 初始加载 + 5s 轮询
  useEffect(() => {
    loadTasks()
    const t = window.setInterval(() => {
      loadTasks()
    }, POLL_INTERVAL_MS)
    return () => window.clearInterval(t)
  }, [loadTasks])

  // 当 selectedTaskId 变化时订阅 SSE
  useEffect(() => {
    if (!selectedTaskId) return
    const unsub = agentTasksApi.subscribeTaskEvents(selectedTaskId, (ev) => {
      appendEvent(selectedTaskId, ev)
      // done / error 时刷新一次列表,确保 status / result 同步
      if (ev.event_type === 'done' || ev.event_type === 'error') {
        loadTasks()
      }
    })
    return () => {
      unsub()
    }
  }, [selectedTaskId, appendEvent, loadTasks])

  // 列表分桶
  const grouped = useMemo(() => {
    const buckets = {
      active: [] as typeof tasks,
      approval: [] as typeof tasks,
      finished: [] as typeof tasks,
    }
    for (const t of tasks) {
      if (TAB_BUCKETS.active.includes(t.status)) buckets.active.push(t)
      else if (TAB_BUCKETS.approval.includes(t.status)) buckets.approval.push(t)
      else if (TAB_BUCKETS.finished.includes(t.status)) buckets.finished.push(t)
    }
    return buckets
  }, [tasks])

  const selectedTask = useMemo(
    () => tasks.find((t) => t.id === selectedTaskId) ?? null,
    [tasks, selectedTaskId],
  )
  const selectedEvents = selectedTaskId ? eventsMap[selectedTaskId] ?? [] : []

  const handleCloseDrawer = () => {
    if (selectedTaskId) clearEvents(selectedTaskId)
    selectTask(null)
  }

  const handleCancel = async () => {
    if (!selectedTask) return
    try {
      await cancelTaskAction(selectedTask.id)
      toast.success('已取消任务')
    } catch (e) {
      toast.error(`取消失败: ${e instanceof Error ? e.message : '未知错误'}`)
    }
  }

  const isCancellable =
    selectedTask &&
    !(['done', 'failed', 'cancelled'] as AgentTaskStatus[]).includes(selectedTask.status)

  return (
    <div className="mx-auto flex h-full max-w-6xl flex-col gap-4 p-6">
      {/* 顶栏 */}
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-foreground">任务中心</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            管理智能体执行的全部任务,包括进行中、待审批与已完成。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadTasks()}
            disabled={loading}
          >
            <RefreshCcw className={loading ? 'animate-spin' : ''} />
            刷新
          </Button>
          <CreateTaskDialog open={createOpen} onOpenChange={setCreateOpen} />
        </div>
      </header>

      {loadError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
          加载失败: {loadError}
        </div>
      )}

      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)} className="flex-1">
        <TabsList>
          <TabsTrigger value="active">
            进行中 <span className="ml-1 text-xs opacity-70">({grouped.active.length})</span>
          </TabsTrigger>
          <TabsTrigger value="approval">
            待我审批{' '}
            <span className="ml-1 text-xs opacity-70">({grouped.approval.length})</span>
          </TabsTrigger>
          <TabsTrigger value="finished">
            已完成{' '}
            <span className="ml-1 text-xs opacity-70">({grouped.finished.length})</span>
          </TabsTrigger>
        </TabsList>

        {(['active', 'approval', 'finished'] as const).map((bucket) => (
          <TabsContent key={bucket} value={bucket} className="mt-4">
            <TaskList
              tasks={grouped[bucket]}
              loading={loading && tasks.length === 0}
              eventsMap={eventsMap}
              selectedId={selectedTaskId}
              onSelect={(id) => {
                if (selectedTaskId && selectedTaskId !== id) clearEvents(selectedTaskId)
                selectTask(id)
              }}
            />
          </TabsContent>
        ))}
      </Tabs>

      <Sheet
        open={Boolean(selectedTask)}
        onOpenChange={(open) => {
          if (!open) handleCloseDrawer()
        }}
      >
        <SheetContent
          side="right"
          className="flex w-full flex-col gap-0 p-0 sm:max-w-xl md:max-w-2xl"
        >
          {selectedTask && (
            <>
              <SheetHeader className="border-b">
                <SheetTitle className="text-base">
                  {(typeof selectedTask.payload?.title === 'string'
                    && selectedTask.payload.title)
                    || `任务 ${selectedTask.id.slice(0, 8)}`}
                </SheetTitle>
                <SheetDescription>
                  Persona: {selectedTask.agent_persona} · 状态: {selectedTask.status}
                </SheetDescription>
              </SheetHeader>

              <div className="flex flex-1 flex-col gap-4 overflow-auto p-4">
                {selectedTask.status === 'needs_approval' && (
                  <TaskApprovalCard task={selectedTask} />
                )}
                <TaskTimeline task={selectedTask} events={selectedEvents} />
              </div>

              {isCancellable && (
                <div className="flex justify-end gap-2 border-t p-3">
                  <Button variant="outline" size="sm" onClick={handleCancel}>
                    <XCircle />
                    取消任务
                  </Button>
                </div>
              )}
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  )
}

interface TaskListProps {
  tasks: ReturnType<typeof useAgentTasksStore.getState>['tasks']
  loading: boolean
  eventsMap: Record<string, ReturnType<typeof useAgentTasksStore.getState>['events'][string]>
  selectedId: string | null
  onSelect: (id: string) => void
}

function TaskList({ tasks, loading, eventsMap, selectedId, onSelect }: TaskListProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 p-8 text-center text-sm text-muted-foreground">
        正在加载任务...
      </div>
    )
  }
  if (tasks.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-border/60 p-8 text-center text-sm text-muted-foreground">
        当前 Tab 暂无任务
      </div>
    )
  }
  return (
    <div className="grid gap-3 md:grid-cols-2">
      {tasks.map((t) => (
        <TaskCard
          key={t.id}
          task={t}
          events={eventsMap[t.id]}
          selected={selectedId === t.id}
          onClick={() => onSelect(t.id)}
        />
      ))}
    </div>
  )
}

// ===== 新建任务弹窗 =====

interface CreateTaskDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function CreateTaskDialog({ open, onOpenChange }: CreateTaskDialogProps) {
  const createTask = useAgentTasksStore((s) => s.createTask)

  const [persona, setPersona] = useState(PERSONA_OPTIONS[0].value)
  const [title, setTitle] = useState('')
  const [userInput, setUserInput] = useState('')
  const [priority, setPriority] = useState('5')
  const [submitting, setSubmitting] = useState(false)

  const reset = () => {
    setPersona(PERSONA_OPTIONS[0].value)
    setTitle('')
    setUserInput('')
    setPriority('5')
  }

  const handleSubmit = async () => {
    if (!userInput.trim()) {
      toast.error('请填写任务指令')
      return
    }
    setSubmitting(true)
    try {
      await createTask({
        agent_persona: persona,
        priority: Number(priority) || 5,
        payload: {
          title: title.trim() || undefined,
          user_input: userInput.trim(),
        },
      })
      toast.success('任务已创建')
      reset()
      onOpenChange(false)
    } catch (e) {
      toast.error(`创建失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        onOpenChange(o)
        if (!o) reset()
      }}
    >
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus />
          新建任务
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>新建任务</DialogTitle>
          <DialogDescription>
            选择智能体角色并描述要做的事,任务将在后台异步执行。
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">智能体</label>
            <Select value={persona} onValueChange={setPersona}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PERSONA_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">标题(可选)</label>
            <Input
              placeholder="例如:审查 X 公司 NDA"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={80}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">任务指令 *</label>
            <Textarea
              rows={4}
              placeholder="详细描述需要智能体完成的事项..."
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground">优先级 (0-9)</label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Array.from({ length: 10 }, (_, i) => String(i)).map((v) => (
                  <SelectItem key={v} value={v}>
                    {v} {v === '5' ? '(默认)' : ''}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            取消
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? '创建中...' : '创建任务'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
