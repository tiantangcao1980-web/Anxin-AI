/**
 * 同步状态指示器
 *
 * 显示当前同步状态（空闲/同步中/错误/离线），
 * 点击可触发手动同步。
 */

import { useCallback, useState } from'react'
import { useAppModeStore } from'@/lib/store'
import { triggerSync, isTauri } from'@/lib/tauri-bridge'
import {
 ArrowPathIcon,
 CheckCircleIcon,
 ExclamationCircleIcon,
 SignalSlashIcon,
} from'@heroicons/react/24/outline'

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
 const { syncStatus, lastSyncTime, mode } = useAppModeStore()
 const [isSyncing, setIsSyncing] = useState(false)
 const isDesktopClient = isTauri()

 const config = STATUS_CONFIG[syncStatus]
 const Icon = config.icon

 const handleSync = useCallback(async () => {
 if (isSyncing || syncStatus ==='offline') return
 setIsSyncing(true)
 try {
 await triggerSync()
 } finally {
 setIsSyncing(false)
 }
 }, [isSyncing, syncStatus])

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
 )
}
