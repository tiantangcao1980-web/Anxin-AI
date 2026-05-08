/**
 * 同步状态指示器
 *
 * 显示当前同步状态（空闲/同步中/错误/离线），
 * 点击可触发手动同步。
 */

import { useCallback, useEffect, useState } from'react'
import { useNavigate } from'react-router-dom'
import { useAppModeStore } from'@/lib/store'
import { getSyncConflicts, isTauri, resolveSyncConflict, triggerSync } from'@/lib/tauri-bridge'
import {
 countChangedConflictFields,
 formatConflictData,
 formatConflictEntityType,
 summarizeConflictData,
} from'@/lib/sync-conflict-utils'
import {
 SYNC_CONFLICT_BUTTON_CLASS,
 SYNC_CONFLICT_COUNT_CLASS,
 SYNC_CONFLICT_ICON_CLASS,
 SYNC_CONFLICT_LABEL_CLASS,
 SYNC_STATUS_BUTTON_CLASS,
 SYNC_STATUS_ICON_CLASS,
 SYNC_STATUS_LABEL_CLASS,
 SYNC_STATUS_TIME_CLASS,
 syncToolbarStatusLabel,
} from'@/components/mode-switcher/sync-status-ui'
import { Button } from'@/components/ui/button'
import {
 Dialog,
 DialogContent,
 DialogFooter,
 DialogHeader,
 DialogTitle,
} from'@/components/ui/dialog'
import {
 ArrowPathIcon,
 CheckCircleIcon,
 ExclamationCircleIcon,
 SignalSlashIcon,
} from'@heroicons/react/24/outline'

interface SyncConflictItem {
 log_id: number
 entity_type: string
 entity_id: string
 local_data: Record<string, unknown>
 remote_data: Record<string, unknown>
}

const STATUS_CONFIG = {
 idle: {
 icon: CheckCircleIcon,
 label:'已同步',
 color:'text-success',
 animate: false,
 },
 syncing: {
 icon: ArrowPathIcon,
 label:'同步中',
 color:'text-info',
 animate: true,
 },
 error: {
 icon: ExclamationCircleIcon,
 label:'同步失败',
 color:'text-destructive',
 animate: false,
 },
 offline: {
 icon: SignalSlashIcon,
 label:'离线',
 color:'text-gray-400',
 animate: false,
 },
} as const

export function SyncStatus() {
 const { syncStatus, lastSyncTime, mode, setLastSyncTime, setSyncStatus } = useAppModeStore()
 const [isSyncing, setIsSyncing] = useState(false)
 const [conflicts, setConflicts] = useState<SyncConflictItem[]>([])
 const [conflictOpen, setConflictOpen] = useState(false)
 const [resolvingId, setResolvingId] = useState<number | null>(null)
 const isDesktopClient = isTauri()
 const navigate = useNavigate()

 const config = STATUS_CONFIG[syncStatus]
 const Icon = config.icon

 const refreshConflicts = useCallback(async () => {
 if (!isDesktopClient || mode ==='top-secret') return
 const rows = await getSyncConflicts()
 setConflicts(rows as SyncConflictItem[])
 }, [isDesktopClient, mode])

 const handleSync = useCallback(async () => {
 if (isSyncing || syncStatus ==='offline') return
 setIsSyncing(true)
 setSyncStatus('syncing')
 try {
 const result = await triggerSync()
 setSyncStatus(result?.success ? 'idle' : 'error')
 if (result?.sync_time) {
 setLastSyncTime(result.sync_time)
 }
 await refreshConflicts()
 if ((result?.conflicts ?? 0) > 0) {
 setConflictOpen(true)
 }
 } finally {
 setIsSyncing(false)
 }
 }, [isSyncing, refreshConflicts, setLastSyncTime, setSyncStatus, syncStatus])

 const handleResolveConflict = useCallback(async (
 conflict: SyncConflictItem,
 resolution: 'keep_local' | 'keep_remote',
 ) => {
 setResolvingId(conflict.log_id)
 try {
 const result = await resolveSyncConflict(conflict.log_id, resolution)
 if (result.success) {
 await refreshConflicts()
 }
 } finally {
 setResolvingId(null)
 }
 }, [refreshConflicts])

 useEffect(() => {
 void refreshConflicts()
 }, [refreshConflicts])

 if (!isDesktopClient) return null
 if (mode ==='top-secret') return null // 绝密模式不显示同步状态

 const formatTime = (time: string | null) => {
 if (!time) return'从未同步'
 const d = new Date(time)
 const now = new Date()
 const diff = Math.floor((now.getTime() - d.getTime()) / 1000)
 if (diff < 60) return'刚刚'
 if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
 if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
 return d.toLocaleDateString('zh-CN')
 }

 const lastSyncLabel = formatTime(lastSyncTime)
 const toolbarLabel = syncToolbarStatusLabel(isSyncing, config.label)

 return (
 <>
 <button
 onClick={handleSync}
 disabled={isSyncing || syncStatus ==='offline'}
 className={SYNC_STATUS_BUTTON_CLASS}
 title={`${toolbarLabel} | 上次同步：${lastSyncLabel}`}
 aria-label={`${toolbarLabel}，上次同步：${lastSyncLabel}`}
 >
 <Icon
 className={`${SYNC_STATUS_ICON_CLASS} ${config.color} ${
 config.animate || isSyncing ?'animate-spin' :''
 }`}
 />
 <span className={SYNC_STATUS_LABEL_CLASS}>
 {toolbarLabel}
 </span>
 <span className={SYNC_STATUS_TIME_CLASS}>
 · {lastSyncLabel}
 </span>
 </button>
 {conflicts.length > 0 && (
 <button
 type="button"
 onClick={() => navigate('/sync-conflicts')}
 className={SYNC_CONFLICT_BUTTON_CLASS}
 title={`${conflicts.length} 个同步冲突待处理`}
 aria-label={`${conflicts.length} 个同步冲突待处理，打开冲突管理`}
 >
 <ExclamationCircleIcon className={SYNC_CONFLICT_ICON_CLASS} aria-hidden="true" />
 <span className={SYNC_CONFLICT_LABEL_CLASS}>冲突</span>
 <span className={SYNC_CONFLICT_COUNT_CLASS}>{conflicts.length}</span>
 </button>
 )}
 <Dialog open={conflictOpen} onOpenChange={setConflictOpen}>
 <DialogContent className="max-w-3xl">
 <DialogHeader>
 <DialogTitle>同步冲突</DialogTitle>
 </DialogHeader>
 <div className="max-h-[55vh] space-y-3 overflow-y-auto">
 {conflicts.length === 0 ? (
 <p className="text-sm text-muted-foreground">当前没有待处理的同步冲突。</p>
 ) : conflicts.map((conflict) => {
 const changedFields = summarizeConflictData(conflict.local_data, conflict.remote_data)
 const changedCount = countChangedConflictFields(conflict.local_data, conflict.remote_data)
 return (
 <div key={conflict.log_id} className="rounded-md border border-border p-3">
 <div className="mb-2 flex items-center justify-between gap-3">
 <div className="min-w-0">
 <p className="truncate text-sm font-medium">
 {formatConflictEntityType(conflict.entity_type)} / {conflict.entity_id}
 </p>
 <p className="text-xs text-muted-foreground">
 {changedCount} 个字段存在差异，请选择保留本地版本或云端版本。
 </p>
 </div>
 </div>
 <div className="space-y-2 rounded-md border border-border bg-muted/30 p-2">
 {changedFields.length === 0 ? (
 <p className="text-xs text-muted-foreground">系统未识别到字段级差异，请打开冲突管理查看详情。</p>
 ) : changedFields.map((field) => (
 <div key={field.key} className="grid gap-2 rounded bg-background p-2 md:grid-cols-[120px_minmax(0,1fr)_minmax(0,1fr)]">
 <div className="text-xs font-medium text-foreground">{field.label}</div>
 <div className="min-w-0 text-xs">
 <p className="mb-1 text-muted-foreground">本地版本</p>
 <p className="break-words text-foreground">{field.localPreview}</p>
 </div>
 <div className="min-w-0 text-xs">
 <p className="mb-1 text-muted-foreground">云端版本</p>
 <p className="break-words text-foreground">{field.remotePreview}</p>
 </div>
 </div>
 ))}
 </div>
 <details className="mt-2 rounded-md border border-border bg-background px-3 py-2">
 <summary className="cursor-pointer text-xs font-medium text-muted-foreground">查看原始数据</summary>
 <div className="mt-2 grid gap-2 md:grid-cols-2">
 <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">{formatConflictData(conflict.local_data)}</pre>
 <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">{formatConflictData(conflict.remote_data)}</pre>
 </div>
 </details>
 <div className="mt-3 flex justify-end gap-2">
 <Button
 variant="outline"
 size="sm"
 disabled={resolvingId === conflict.log_id}
 onClick={() => handleResolveConflict(conflict, 'keep_remote')}
 >
 保留云端
 </Button>
 <Button
 size="sm"
 disabled={resolvingId === conflict.log_id}
 onClick={() => handleResolveConflict(conflict, 'keep_local')}
 >
 保留本地
 </Button>
 </div>
 </div>
 )
 })}
 </div>
 <DialogFooter>
 <Button variant="outline" onClick={() => navigate('/sync-conflicts')}>打开冲突管理</Button>
 <Button variant="outline" onClick={() => setConflictOpen(false)}>关闭</Button>
 </DialogFooter>
 </DialogContent>
 </Dialog>
 </>
 )
}
