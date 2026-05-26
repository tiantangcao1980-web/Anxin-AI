/**
 * StatusBar — 飞书风桌面底部状态栏（24px 高）
 *
 * 内容（左到右）：
 *   - 在线圆点（success/warning/muted）
 *   - 隐私模式（本地/混合/云端）+ 点击切换
 *   - 同步状态（已同步/同步中/离线/冲突）
 *   - 用户邮箱
 *   - ⌘K 命令面板提示（右下）
 *
 * 仅在桌面 lg+ 显示，移动端隐藏。
 * 关联：DESIGN.md §10.8 / docs/plans/2026-05-22-product-blueprint.md §3.1
 */

import { useNavigate } from 'react-router-dom'
import { useAppModeStore, useAuthStore } from '@/lib/store'

interface StatusBarProps {
  /** 触发 Cmd+K 命令面板（由父组件传入） */
  onOpenCommandPalette?: () => void
}

const MODE_LABELS: Record<string, { text: string; color: string }> = {
  local: { text: '本地', color: 'text-success' },
  hybrid: { text: '混合', color: 'text-info' },
  cloud: { text: '云端', color: 'text-im-primary' },
}

// SyncStatusType in store.ts = 'idle' | 'syncing' | 'error' | 'offline'
// 这里映射到 UI 显示文案；conflict 是路由感知的额外状态（暂未在 store 枚举中，留兼容）
const SYNC_LABELS: Record<string, { text: string; color: string }> = {
  idle: { text: '已同步', color: 'text-muted-foreground' },
  synced: { text: '已同步', color: 'text-muted-foreground' },
  syncing: { text: '同步中…', color: 'text-info' },
  conflict: { text: '有冲突', color: 'text-warning' },
  offline: { text: '离线', color: 'text-muted-foreground' },
  error: { text: '同步失败', color: 'text-destructive' },
}

export function DesktopStatusBar({ onOpenCommandPalette }: StatusBarProps = {}) {
  const navigate = useNavigate()
  const { mode, syncStatus, isOnline, lastSyncTime } = useAppModeStore()
  const user = useAuthStore((s) => s.user)

  const modeInfo = MODE_LABELS[mode ?? 'cloud'] ?? MODE_LABELS.cloud
  const syncInfo = SYNC_LABELS[syncStatus ?? 'idle'] ?? SYNC_LABELS.idle

  const lastSyncLabel = lastSyncTime
    ? new Date(lastSyncTime).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : null

  return (
    <div
      data-testid="desktop-status-bar"
      className="hidden lg:flex h-6 items-center px-3 text-[11px] border-t border-border bg-surface-1 text-muted-foreground select-none"
    >
      {/* 在线圆点 */}
      <span
        className={`inline-block w-2 h-2 rounded-full mr-2 ${
          isOnline ? 'bg-success' : 'bg-muted-foreground/40'
        }`}
        aria-label={isOnline ? '在线' : '离线'}
      />

      {/* 模式 */}
      <button
        type="button"
        onClick={() => navigate('/settings?tab=workstation')}
        className={`px-1.5 hover:bg-surface-2 rounded transition-colors ${modeInfo.color}`}
        title="切换隐私模式"
      >
        {modeInfo.text}模式
      </button>

      <span className="mx-2 text-border">·</span>

      {/* 同步状态 */}
      <button
        type="button"
        onClick={() => syncStatus === 'conflict' && navigate('/sync-conflicts')}
        className={`px-1.5 hover:bg-surface-2 rounded transition-colors ${syncInfo.color} ${
          syncStatus === 'conflict' ? 'cursor-pointer' : 'cursor-default'
        }`}
        disabled={syncStatus !== 'conflict'}
      >
        {syncInfo.text}
        {lastSyncLabel && syncStatus === 'synced' ? ` ${lastSyncLabel}` : ''}
      </button>

      {/* 中间填充 */}
      <span className="flex-1" />

      {/* 用户 */}
      {user?.email && (
        <>
          <span className="truncate max-w-[200px]" title={user.email}>
            {user.email}
          </span>
          <span className="mx-2 text-border">·</span>
        </>
      )}

      {/* ⌘K 命令面板提示 */}
      <button
        type="button"
        onClick={onOpenCommandPalette}
        className="flex items-center gap-1 px-2 py-0.5 rounded border border-border bg-surface-2 hover:bg-surface-3 transition-colors"
        title="打开命令面板"
      >
        <kbd className="font-mono text-[10px]">⌘K</kbd>
      </button>
    </div>
  )
}

export default DesktopStatusBar
