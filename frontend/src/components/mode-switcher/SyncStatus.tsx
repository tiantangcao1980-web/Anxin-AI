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
 label:'同步中...',
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

 return (
 <>
 <button
 onClick={handleSync}
 disabled={isSyncing || syncStatus ==='offline'}
 className="flex items-center gap-1.5 px-2 py-1 rounded-md text-xs hover:bg-accent transition-colors disabled:opacity-50"
 title={`${config.label} | 上次同步：${formatTime(lastSyncTime)}`}
 >
 <Icon
 className={`h-3.5 w-3.5 ${config.color} ${
 config.animate || isSyncing ?'animate-spin' :''
 }`}
 />
 <span className="text-muted-foreground hidden lg:inline">
 {isSyncing ?'同步中...' : formatTime(lastSyncTime)}
 </span>
 </button>
 {conflicts.length > 0 && (
 <button
 type="button"
 onClick={() => navigate('/sync-conflicts')}
 className="ml-1 rounded-md bg-destructive/10 px-2 py-1 text-xs text-destructive hover:bg-destructive/15"
 title="查看同步冲突"
 >
 {conflicts.length} 个冲突
 </button>
 )}
 <Dialog open={conflictOpen} onOpenChange={setConflictOpen}>
 <DialogContent className="max-w-2xl">
 <DialogHeader>
 <DialogTitle>同步冲突</DialogTitle>
 </DialogHeader>
 <div className="max-h-[55vh] space-y-3 overflow-y-auto">
 {conflicts.length === 0 ? (
 <p className="text-sm text-muted-foreground">当前没有待处理的同步冲突。</p>
 ) : conflicts.map((conflict) => (
 <div key={conflict.log_id} className="rounded-md border border-border p-3">
 <div className="mb-2 flex items-center justify-between gap-3">
 <div className="min-w-0">
 <p className="truncate text-sm font-medium">{conflict.entity_type} / {conflict.entity_id}</p>
 <p className="text-xs text-muted-foreground">请选择保留本地版本或云端版本。</p>
 </div>
 </div>
 <div className="grid gap-2 md:grid-cols-2">
 <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">{JSON.stringify(conflict.local_data, null, 2)}</pre>
 <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">{JSON.stringify(conflict.remote_data, null, 2)}</pre>
 </div>
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
 ))}
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
