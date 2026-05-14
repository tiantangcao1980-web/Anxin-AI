import { useState, useEffect, useCallback, useRef } from'react'
import { icons } from'@/lib/icons'
import { EmptyState, LoadingState, ErrorState } from'@/components/common'
import { cardStyle, buttonStyle, heading, statusColor } from'@/lib/design-tokens'
import { tasksApi, type TaskItem } from'@/lib/api'
import { toast } from'sonner'
import { PageContainer } from'@/components/ui/PageContainer'

type TaskStatus ='todo' |'in_progress' |'done'
type TaskPriority ='high' |'medium' |'low'
type ViewMode ='board' |'list'

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
 high: { label:'高', color:'text-destructive bg-destructive/10' },
 medium: { label:'中', color:'text-warning bg-warning/10' },
 low: { label:'低', color:'text-muted-foreground bg-muted' },
}

const statusConfig = {
 todo: { label:'待办', color: statusColor.neutral },
 in_progress: { label:'进行中', color: statusColor.info },
 done: { label:'已完成', color: statusColor.success },
}

const columns: { key: TaskStatus; label: string }[] = [
 { key:'todo', label:'待办' },
 { key:'in_progress', label:'进行中' },
 { key:'done', label:'已完成' },
]

function apiToTask(item: TaskItem): Task {
 return {
 id: item.id,
 title: item.title,
 description: item.description ||'',
 status: (item.status as TaskStatus) ||'todo',
 priority: (item.priority as TaskPriority) ||'medium',
 dueDate: item.dueDate ||'',
 assignee: item.assignee ||'',
 caseTitle: item.caseTitle,
 tags: item.tags || [],
 }
}

export default function Tasks() {
 const [tasks, setTasks] = useState<Task[]>([])
 const [viewMode, setViewMode] = useState<ViewMode>('board')
 const [filterPriority, setFilterPriority] = useState<TaskPriority |'all'>('all')
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)

 // 拖拽状态
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
 setError(err instanceof Error ? err.message :'加载任务失败')
 } finally {
 setLoading(false)
 }
 }, [])

 useEffect(() => { loadTasks() }, [loadTasks])

 const filteredTasks = filterPriority ==='all' ? tasks : tasks.filter(t => t.priority === filterPriority)

 // ===== 拖拽处理 =====

 const handleDragStart = (e: React.DragEvent, taskId: string) => {
 setDraggedTaskId(taskId)
 e.dataTransfer.effectAllowed ='move'
 e.dataTransfer.setData('text/plain', taskId)
 // 半透明拖拽效果
 if (e.currentTarget instanceof HTMLElement) {
 e.currentTarget.style.opacity ='0.5'
 }
 }

 const handleDragEnd = (e: React.DragEvent) => {
 setDraggedTaskId(null)
 setDropTarget(null)
 if (e.currentTarget instanceof HTMLElement) {
 e.currentTarget.style.opacity ='1'
 }
 }

 const handleDragOver = (e: React.DragEvent, status: TaskStatus) => {
 e.preventDefault()
 e.dataTransfer.dropEffect ='move'
 setDropTarget(status)
 }

 const handleDragLeave = () => {
 setDropTarget(null)
 }

 const handleDrop = async (e: React.DragEvent, newStatus: TaskStatus) => {
 e.preventDefault()
 const taskId = e.dataTransfer.getData('text/plain') || draggedTaskId
 setDropTarget(null)
 setDraggedTaskId(null)

 if (!taskId) return

 const task = tasks.find(t => t.id === taskId)
 if (!task || task.status === newStatus) return

 // 乐观更新
 setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: newStatus } : t))
 toast.success(`任务已移至「${statusConfig[newStatus].label}」`)

 // 调用后端
 try {
 await tasksApi.transition(taskId, newStatus)
 } catch (err: any) {
 // 回滚
 setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: task.status } : t))
 toast.error(err?.message ||'状态更新失败')
 }
 }

 // 按钮点击快捷移动
 const moveTask = async (taskId: string, newStatus: TaskStatus) => {
 const task = tasks.find(t => t.id === taskId)
 if (!task) return
 setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: newStatus } : t))
 toast.success(`任务已移至「${statusConfig[newStatus].label}」`)
 try {
 await tasksApi.transition(taskId, newStatus)
 } catch {
 setTasks(prev => prev.map(t => t.id === taskId ? { ...t, status: task.status } : t))
 }
 }

 const isOverdue = (date: string) => date && new Date(date) < new Date()

 const TaskCard = ({ task }: { task: Task }) => (
 <div
 draggable
 onDragStart={e => handleDragStart(e, task.id)}
 onDragEnd={handleDragEnd}
 className={`${cardStyle.interactive} mb-3 cursor-grab active:cursor-grabbing ${
 draggedTaskId === task.id ?'ring-2 ring-primary/40 opacity-50' :''
 }`}
 >
 <div className="flex items-start justify-between mb-2">
 <h4 className={heading.card +' flex-1'}>{task.title}</h4>
 <span className={`text-xs px-1.5 py-0.5 rounded ${priorityConfig[task.priority]?.color ||''}`}>
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
 <div className={`flex items-center gap-1 text-xs ${isOverdue(task.dueDate) && task.status !=='done' ?'text-destructive' :'text-muted-foreground'}`}>
 <icons.Calendar className="w-3 h-3" />
 <span>{task.dueDate}</span>
 </div>
 </div>
 {task.status !=='done' && (
 <div className="flex gap-1 mt-3 pt-2 border-t border-border">
 {task.status ==='todo' && (
 <button onClick={() => moveTask(task.id,'in_progress')} className="text-xs text-primary hover:underline">开始处理</button>
 )}
 {task.status ==='in_progress' && (
 <button onClick={() => moveTask(task.id,'done')} className="text-xs text-success hover:underline">标记完成</button>
 )}
 </div>
 )}
 </div>
 )

 return (
 <PageContainer showHeader={false} scrollable={false} className="!p-0 !space-y-0">
 <div className="border-b border-border px-4 sm:px-5 lg:px-6 py-3 flex items-center justify-between">
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
 className={`px-3 py-1.5 text-xs ${viewMode ==='board' ?'bg-primary text-primary-foreground' :'bg-background text-muted-foreground hover:bg-muted'}`}>
 看板
 </button>
 <button onClick={() => setViewMode('list')}
 className={`px-3 py-1.5 text-xs ${viewMode ==='list' ?'bg-primary text-primary-foreground' :'bg-background text-muted-foreground hover:bg-muted'}`}>
 列表
 </button>
 </div>
 </div>
 </div>

 <div className="flex-1 overflow-auto px-4 sm:px-5 lg:px-6 py-4">
 {loading ? (
 <LoadingState text="加载任务..." />
 ) : error ? (
 <ErrorState title="任务数据加载失败" message={error} onRetry={() => void loadTasks()} />
 ) : filteredTasks.length === 0 ? (
 <EmptyState icon="Tasks" title="暂无任务数据" description="运行种子数据后即可验证任务看板。" />
 ) : viewMode ==='board' ? (
 /* ===== 看板视图（支持拖拽） ===== */
 <div className="flex gap-4 h-full min-w-[768px]">
 {columns.map(col => {
 const colTasks = filteredTasks.filter(t => t.status === col.key)
 const isOver = dropTarget === col.key
 return (
 <div
 key={col.key}
 className={`flex-1 flex flex-col min-w-[240px] rounded-xl transition-colors ${
 isOver ?'bg-primary/5 ring-2 ring-primary/20 ring-dashed' :''
 }`}
 onDragOver={e => handleDragOver(e, col.key)}
 onDragLeave={handleDragLeave}
 onDrop={e => handleDrop(e, col.key)}
 >
 <div className="flex items-center justify-between mb-3 px-1">
 <div className="flex items-center gap-2">
 <span className={`text-xs px-2 py-0.5 rounded-full ${statusConfig[col.key].color}`}>
 {col.label}
 </span>
 <span className="text-xs text-muted-foreground">{colTasks.length}</span>
 </div>
 </div>
 <div className={`flex-1 overflow-y-auto px-1 min-h-[100px] ${
 isOver && colTasks.length === 0 ?'flex items-center justify-center' :''
 }`}>
 {colTasks.map(task => <TaskCard key={task.id} task={task} />)}
 {colTasks.length === 0 && (
 <p className={`text-xs text-muted-foreground text-center py-8 ${
 isOver ?'text-primary opacity-80' :'opacity-50'
 }`}>
 {isOver ?'放下以移至此列' :'暂无任务'}
 </p>
 )}
 </div>
 </div>
 )
 })}
 </div>
 ) : (
 /* ===== 列表视图 ===== */
 <div className="space-y-2">
 {filteredTasks.map(task => (
 <div key={task.id} className={cardStyle.interactive +' flex items-center gap-4'}>
 <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${statusConfig[task.status]?.color ||''}`}>
 {statusConfig[task.status]?.label || task.status}
 </span>
 <span className={`text-xs px-1.5 py-0.5 rounded flex-shrink-0 ${priorityConfig[task.priority]?.color ||''}`}>
 {priorityConfig[task.priority]?.label || task.priority}
 </span>
 <div className="flex-1 min-w-0">
 <p className={heading.card +' truncate'}>{task.title}</p>
 {task.caseTitle && <p className="text-xs text-muted-foreground truncate">{task.caseTitle}</p>}
 </div>
 <span className="text-xs text-muted-foreground flex-shrink-0">{task.assignee}</span>
 <span className={`text-xs flex-shrink-0 ${isOverdue(task.dueDate) && task.status !=='done' ?'text-destructive' :'text-muted-foreground'}`}>
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
