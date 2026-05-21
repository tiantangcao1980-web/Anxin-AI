/**
 * Tasks · 任务看板（Editorial Luxury 改造 · Phase 1）
 *
 * 旧版用 PageContainer + cardStyle.interactive + statusColor chip 色块 + priority bg-tint。
 * 新版：ListPageTemplate（list 视图）+ 自定义看板（board 视图 — Editorial hairline grid）。
 *
 * 保留全部功能：拖拽（drag-and-drop）/ 状态推进 / 优先级筛选 / 看板列表切换 / 乐观更新 + 回滚。
 */

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Calendar, Briefcase, Check, User } from 'lucide-react'

import { ListPageTemplate, ListPageStatus } from '@/components/ui/ListPageTemplate'
import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import { tasksApi, type TaskItem } from '@/lib/api'
import { cn } from '@/components/ui/utils'

type TaskStatus = 'todo' | 'in_progress' | 'done'
type TaskPriority = 'high' | 'medium' | 'low'
type ViewMode = 'board' | 'list'

interface Task {
  id: string
  title: string
  description: string
  status: TaskStatus
  priority: TaskPriority
  dueDate: string
  assignee: string
  caseTitle?: string
  tags: string[]
}

const PRIORITY_META: Record<TaskPriority, { label: string; labelEn: string; tone: 'normal' | 'warning' | 'error' }> = {
  high:   { label: '高', labelEn: 'High',   tone: 'error'   },
  medium: { label: '中', labelEn: 'Medium', tone: 'warning' },
  low:    { label: '低', labelEn: 'Low',    tone: 'normal'  },
}

const STATUS_META: Record<TaskStatus, { label: string; labelEn: string; tone: 'normal' | 'success' | 'warning' }> = {
  todo:        { label: '待办',   labelEn: 'Todo',     tone: 'normal'  },
  in_progress: { label: '进行中', labelEn: 'Doing',    tone: 'warning' },
  done:        { label: '已完成', labelEn: 'Done',     tone: 'success' },
}

const COLUMNS: TaskStatus[] = ['todo', 'in_progress', 'done']

function apiToTask(item: TaskItem): Task {
  return {
    id: item.id,
    title: item.title,
    description: item.description || '',
    status: (item.status as TaskStatus) || 'todo',
    priority: (item.priority as TaskPriority) || 'medium',
    dueDate: item.dueDate || '',
    assignee: item.assignee || '',
    caseTitle: item.caseTitle,
    tags: item.tags || [],
  }
}

function ToneTag({ tone, label, labelEn }: { tone: 'normal' | 'success' | 'warning' | 'error'; label: string; labelEn: string }) {
  const toneClass = {
    normal:  'text-muted-foreground',
    success: 'text-success',
    warning: 'text-warning',
    error:   'text-destructive',
  }[tone]
  return (
    <span className={cn('inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em]', toneClass)}>
      <span className="h-1 w-1 rounded-full bg-current" aria-hidden />
      <span>{labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal text-foreground/80">{label}</span>
    </span>
  )
}

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [viewMode, setViewMode] = useState<ViewMode>('board')
  const [filterPriority, setFilterPriority] = useState<TaskPriority | 'all'>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [draggedTaskId, setDraggedTaskId] = useState<string | null>(null)
  const [dropTarget, setDropTarget] = useState<TaskStatus | null>(null)

  const loadTasks = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await tasksApi.list({ page_size: 100 })
      setTasks((data.items || []).map(apiToTask))
    } catch (err) {
      setTasks([])
      setError(err instanceof Error ? err.message : '加载任务失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadTasks() }, [loadTasks])

  const filteredTasks = filterPriority === 'all' ? tasks : tasks.filter((t) => t.priority === filterPriority)

  // ===== 拖拽 =====
  const handleDragStart = (e: React.DragEvent, taskId: string) => {
    setDraggedTaskId(taskId)
    e.dataTransfer.effectAllowed = 'move'
    e.dataTransfer.setData('text/plain', taskId)
    if (e.currentTarget instanceof HTMLElement) e.currentTarget.style.opacity = '0.5'
  }
  const handleDragEnd = (e: React.DragEvent) => {
    setDraggedTaskId(null); setDropTarget(null)
    if (e.currentTarget instanceof HTMLElement) e.currentTarget.style.opacity = '1'
  }
  const handleDragOver = (e: React.DragEvent, status: TaskStatus) => {
    e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDropTarget(status)
  }
  const handleDrop = async (e: React.DragEvent, newStatus: TaskStatus) => {
    e.preventDefault()
    const taskId = e.dataTransfer.getData('text/plain') || draggedTaskId
    setDropTarget(null); setDraggedTaskId(null)
    if (!taskId) return
    const task = tasks.find((t) => t.id === taskId)
    if (!task || task.status === newStatus) return
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t)))
    toast.success(`任务已移至「${STATUS_META[newStatus].label}」`)
    try { await tasksApi.transition(taskId, newStatus) }
    catch (err: unknown) {
      setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: task.status } : t)))
      toast.error(err instanceof Error ? err.message : '状态更新失败')
    }
  }

  const moveTask = async (taskId: string, newStatus: TaskStatus) => {
    const task = tasks.find((t) => t.id === taskId)
    if (!task) return
    setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: newStatus } : t)))
    toast.success(`任务已移至「${STATUS_META[newStatus].label}」`)
    try { await tasksApi.transition(taskId, newStatus) }
    catch { setTasks((prev) => prev.map((t) => (t.id === taskId ? { ...t, status: task.status } : t))) }
  }

  const isOverdue = (date: string) => date && new Date(date) < new Date()

  // ===== 看板 TaskCard =====
  const TaskCard = ({ task }: { task: Task }) => {
    const overdue = isOverdue(task.dueDate) && task.status !== 'done'
    return (
      <div
        draggable
        onDragStart={(e) => handleDragStart(e, task.id)}
        onDragEnd={handleDragEnd}
        className={cn(
          'group bg-card border-b border-border/60 p-3 cursor-grab active:cursor-grabbing transition-colors hover:bg-surface-2/40',
          draggedTaskId === task.id && 'opacity-50',
        )}
      >
        <div className="flex items-start justify-between gap-2 mb-1.5">
          <h4 className="font-serif text-[15px] leading-tight text-foreground flex-1">{task.title}</h4>
          <ToneTag tone={PRIORITY_META[task.priority].tone} label={PRIORITY_META[task.priority].label} labelEn={PRIORITY_META[task.priority].labelEn} />
        </div>
        {task.description && (
          <p className="text-[12px] text-muted-foreground line-clamp-2 mb-2 leading-relaxed">{task.description}</p>
        )}
        {task.caseTitle && (
          <div className="flex items-center gap-1.5 mb-2 text-[12px] text-muted-foreground">
            <Briefcase className="w-3 h-3 stroke-[1.5]" />
            <span className="truncate">{task.caseTitle}</span>
          </div>
        )}
        <div className="flex items-center justify-between text-[12px]">
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <User className="w-3 h-3 stroke-[1.5]" />
            <span>{task.assignee || '—'}</span>
          </div>
          <div className={cn('flex items-center gap-1', overdue ? 'text-destructive' : 'text-muted-foreground')}>
            <Calendar className="w-3 h-3 stroke-[1.5]" />
            <span className="tabular-nums">{task.dueDate || '—'}</span>
          </div>
        </div>
        {task.status !== 'done' && (
          <div className="flex gap-3 mt-3 pt-2 border-t border-border/60">
            {task.status === 'todo' && (
              <button onClick={() => void moveTask(task.id, 'in_progress')} className="text-[11px] uppercase tracking-[0.12em] text-primary hover:text-primary-700 transition-colors">
                开始处理 →
              </button>
            )}
            {task.status === 'in_progress' && (
              <button onClick={() => void moveTask(task.id, 'done')} className="inline-flex items-center gap-1.5 text-[11px] uppercase tracking-[0.12em] text-success hover:opacity-80 transition-opacity">
                <Check className="w-3 h-3 stroke-[1.5]" />
                <span>标记完成</span>
              </button>
            )}
          </div>
        )}
      </div>
    )
  }

  const toolbar = (
    <>
      <select
        value={filterPriority}
        onChange={(e) => setFilterPriority(e.target.value as TaskPriority | 'all')}
        className="bg-transparent border border-border hover:border-foreground focus:border-foreground transition-colors text-[13px] px-3 py-1.5 outline-none"
      >
        <option value="all">全部优先级</option>
        <option value="high">高优先级</option>
        <option value="medium">中优先级</option>
        <option value="low">低优先级</option>
      </select>
      <div className="inline-flex items-center text-[13px] border border-border" role="tablist">
        <button
          onClick={() => setViewMode('board')}
          role="tab"
          aria-selected={viewMode === 'board'}
          className={cn('px-3 py-1.5 transition-colors', viewMode === 'board' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground')}
        >
          看板
        </button>
        <button
          onClick={() => setViewMode('list')}
          role="tab"
          aria-selected={viewMode === 'list'}
          className={cn('px-3 py-1.5 transition-colors border-l border-border', viewMode === 'list' ? 'bg-foreground text-background' : 'text-muted-foreground hover:text-foreground')}
        >
          列表
        </button>
      </div>
    </>
  )

  // ===== 看板视图（自定义，因为内含 drag-drop） =====
  if (viewMode === 'board') {
    return (
      <div className="mx-auto max-w-[1600px] px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-12">
        <EditorialPageHeader
          tracker={['Workflow', '任务看板']}
          title="任务"
          description={`${filteredTasks.length} 项任务 · 拖拽可推进状态`}
          actions={toolbar}
        />
        {loading ? (
          <ListPageStatus tracker="Loading" title="正在加载任务" />
        ) : error ? (
          <ListPageStatus tracker="Error" title="任务数据加载失败" description={error} tone="error" action={
            <button onClick={() => void loadTasks()} className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px]">重试</button>
          } />
        ) : filteredTasks.length === 0 ? (
          <ListPageStatus tracker="Empty" title="暂无任务" description="运行种子数据后即可看到任务看板。" />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-px bg-border border border-border min-w-[768px] overflow-x-auto">
            {COLUMNS.map((status) => {
              const colTasks = filteredTasks.filter((t) => t.status === status)
              const isOver = dropTarget === status
              const meta = STATUS_META[status]
              return (
                <div
                  key={status}
                  className={cn('bg-card flex flex-col min-w-[240px] transition-colors', isOver && 'bg-primary-50')}
                  onDragOver={(e) => handleDragOver(e, status)}
                  onDragLeave={() => setDropTarget(null)}
                  onDrop={(e) => void handleDrop(e, status)}
                >
                  <header className="px-4 py-3 border-b border-border flex items-center justify-between">
                    <ToneTag tone={meta.tone} label={meta.label} labelEn={meta.labelEn} />
                    <span className="text-[11px] text-muted-foreground tabular-nums">{colTasks.length}</span>
                  </header>
                  <div className="flex-1 min-h-[200px]">
                    {colTasks.map((t) => (<TaskCard key={t.id} task={t} />))}
                    {colTasks.length === 0 && (
                      <p className={cn('text-[12px] text-center py-12', isOver ? 'text-primary' : 'text-muted-foreground/50')}>
                        {isOver ? '放下以移至此列' : '暂无任务'}
                      </p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  // ===== 列表视图（ListPageTemplate） =====
  return (
    <ListPageTemplate
      tracker={['Workflow', '任务列表']}
      title="任务"
      description={`${filteredTasks.length} 项任务`}
      toolbarRight={toolbar}
      loading={loading}
      error={error}
      empty={!loading && !error && filteredTasks.length === 0}
      emptyState={
        <ListPageStatus tracker="Empty" title="暂无任务" description="运行种子数据后即可看到任务。" action={
          <button onClick={() => void loadTasks()} className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px]">重新加载</button>
        } />
      }
    >
      {filteredTasks.map((task, i) => {
        const overdue = isOverdue(task.dueDate) && task.status !== 'done'
        return (
          <li key={task.id}>
            <div className="group flex items-start gap-6 py-5 px-3 -mx-3 border-b border-border/60 transition-colors hover:bg-surface-2/40">
              <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
                {String(i + 1).padStart(3, '0')}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-4 flex-wrap mb-1.5">
                  <h3 className="font-serif text-[18px] leading-tight text-foreground truncate">{task.title}</h3>
                  <ToneTag tone={STATUS_META[task.status].tone} label={STATUS_META[task.status].label} labelEn={STATUS_META[task.status].labelEn} />
                  <ToneTag tone={PRIORITY_META[task.priority].tone} label={PRIORITY_META[task.priority].label} labelEn={PRIORITY_META[task.priority].labelEn} />
                </div>
                <div className="text-[12px] text-muted-foreground flex items-center gap-4 flex-wrap mt-2">
                  {task.caseTitle && (<span className="inline-flex items-center gap-1.5"><Briefcase className="w-3 h-3 stroke-[1.5]" />{task.caseTitle}</span>)}
                  <span className="inline-flex items-center gap-1.5"><User className="w-3 h-3 stroke-[1.5]" />{task.assignee || '—'}</span>
                  <span className={cn('inline-flex items-center gap-1.5', overdue && 'text-destructive')}>
                    <Calendar className="w-3 h-3 stroke-[1.5]" />
                    <span className="tabular-nums">{task.dueDate || '—'}</span>
                  </span>
                </div>
              </div>
            </div>
          </li>
        )
      })}
    </ListPageTemplate>
  )
}
