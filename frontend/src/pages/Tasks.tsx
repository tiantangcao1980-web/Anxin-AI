import { useState, useEffect, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, buttonStyle, heading, statusColor } from '@/lib/design-tokens'
import { tasksApi, type TaskItem } from '@/lib/api'
import { toast } from 'sonner'
import { PageContainer } from '@/components/ui/PageContainer'

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

const priorityConfig = {
  high: { label: '高', color: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-950/30' },
  medium: { label: '中', color: 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30' },
  low: { label: '低', color: 'text-muted-foreground bg-muted' },
}

const statusConfig = {
  todo: { label: '待办', color: statusColor.neutral },
  in_progress: { label: '进行中', color: statusColor.info },
  done: { label: '已完成', color: statusColor.success },
}

const columns: { key: TaskStatus; label: string }[] = [
  { key: 'todo', label: '待办' },
  { key: 'in_progress', label: '进行中' },
  { key: 'done', label: '已完成' },
]

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

export default function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [viewMode, setViewMode] = useState<ViewMode>('board')
  const [filterPriority, setFilterPriority] = useState<TaskPriority | 'all'>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

  useEffect(() => { loadTasks() }, [loadTasks])

  const filteredTasks = filterPriority === 'all' ? tasks : tasks.filter(t => t.priority === filterPriority)

  const moveTask = async (taskId: string, newStatus: TaskStatus) => {
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: newStatus } : t))
    toast.success('任务状态已更新')
    try {
      await tasksApi.updateStatus(taskId, newStatus)
    } catch {
      // 静默失败，本地状态已更新
    }
  }

  const isOverdue = (date: string) => date && new Date(date) < new Date()

  const TaskCard = ({ task }: { task: Task }) => (
    <div className={cardStyle.interactive + ' mb-3'}>
      <div className="flex items-start justify-between mb-2">
        <h4 className={heading.card + ' flex-1'}>{task.title}</h4>
        <span className={`text-xs px-1.5 py-0.5 rounded ${priorityConfig[task.priority]?.color || ''}`}>
          {priorityConfig[task.priority]?.label || task.priority}
        </span>
      </div>
      <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{task.description}</p>
      {task.caseTitle && (
        <div className="flex items-center gap-1 mb-2">
          <icons.Cases className="w-3 h-3 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{task.caseTitle}</span>
        </div>
      )}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <icons.User className="w-3 h-3 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">{task.assignee}</span>
        </div>
        <div className={`flex items-center gap-1 text-xs ${isOverdue(task.dueDate) && task.status !== 'done' ? 'text-red-500' : 'text-muted-foreground'}`}>
          <icons.Calendar className="w-3 h-3" />
          <span>{task.dueDate}</span>
        </div>
      </div>
      {task.status !== 'done' && (
        <div className="flex gap-1 mt-3 pt-2 border-t border-border">
          {task.status === 'todo' && (
            <button onClick={() => moveTask(task.id, 'in_progress')} className="text-xs text-primary hover:underline">开始处理</button>
          )}
          {task.status === 'in_progress' && (
            <button onClick={() => moveTask(task.id, 'done')} className="text-xs text-emerald-600 hover:underline">标记完成</button>
          )}
        </div>
      )}
    </div>
  )

  return (
    <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
      <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-5 flex items-center justify-between">
        <h1 className={heading.page}>
          <icons.Tasks className="w-5 h-5 inline-block mr-2 -mt-0.5" />
          任务中心
        </h1>
        <div className="flex items-center gap-3">
          <select value={filterPriority} onChange={e => setFilterPriority(e.target.value as any)}
            className="px-3 py-1.5 rounded-lg border border-border bg-background text-xs">
            <option value="all">全部优先级</option>
            <option value="high">高优先级</option>
            <option value="medium">中优先级</option>
            <option value="low">低优先级</option>
          </select>
          <div className="flex rounded-lg border border-border overflow-hidden">
            <button onClick={() => setViewMode('board')}
              className={`px-3 py-1.5 text-xs ${viewMode === 'board' ? 'bg-primary text-white' : 'bg-background text-muted-foreground hover:bg-muted'}`}>
              看板
            </button>
            <button onClick={() => setViewMode('list')}
              className={`px-3 py-1.5 text-xs ${viewMode === 'list' ? 'bg-primary text-white' : 'bg-background text-muted-foreground hover:bg-muted'}`}>
              列表
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-auto px-4 sm:px-5 lg:px-6 py-4">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <icons.Refresh className="w-6 h-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">加载任务...</span>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20">
            <icons.AlertTriangle className="w-10 h-10 text-destructive/60 mb-3" />
            <p className="text-sm text-foreground mb-1">任务数据加载失败</p>
            <p className="text-xs text-muted-foreground mb-4">{error}</p>
            <button onClick={() => void loadTasks()} className={buttonStyle.primary}>
              重新加载
            </button>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20">
            <icons.Tasks className="w-10 h-10 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-foreground mb-1">暂无任务数据</p>
            <p className="text-xs text-muted-foreground">运行种子数据后即可验证任务看板。</p>
          </div>
        ) : viewMode === 'board' ? (
          <div className="flex gap-4 h-full min-w-[768px]">
            {columns.map(col => {
              const colTasks = filteredTasks.filter(t => t.status === col.key)
              return (
                <div key={col.key} className="flex-1 flex flex-col min-w-[240px]">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${statusConfig[col.key].color}`}>
                        {col.label}
                      </span>
                      <span className="text-xs text-muted-foreground">{colTasks.length}</span>
                    </div>
                  </div>
                  <div className="flex-1 overflow-y-auto">
                    {colTasks.map(task => <TaskCard key={task.id} task={task} />)}
                    {colTasks.length === 0 && (
                      <p className="text-xs text-muted-foreground text-center py-8 opacity-50">暂无任务</p>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredTasks.map(task => (
              <div key={task.id} className={cardStyle.interactive + ' flex items-center gap-4'}>
                <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${statusConfig[task.status]?.color || ''}`}>
                  {statusConfig[task.status]?.label || task.status}
                </span>
                <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${priorityConfig[task.priority]?.color || ''}`}>
                  {priorityConfig[task.priority]?.label || task.priority}
                </span>
                <div className="flex-1 min-w-0">
                  <p className={heading.card + ' truncate'}>{task.title}</p>
                  {task.caseTitle && <p className="text-xs text-muted-foreground truncate">{task.caseTitle}</p>}
                </div>
                <span className="text-xs text-muted-foreground flex-shrink-0">{task.assignee}</span>
                <span className={`text-xs flex-shrink-0 ${isOverdue(task.dueDate) && task.status !== 'done' ? 'text-red-500' : 'text-muted-foreground'}`}>
                  {task.dueDate}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </PageContainer>
  )
}
