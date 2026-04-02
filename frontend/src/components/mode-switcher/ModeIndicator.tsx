/**
 * 模式指示器（紧凑版）
 *
 * 仅显示当前模式图标和简短标签，适用于移动端或侧边栏。
 */

import { useAppModeStore } from '@/lib/store'
import { isTauri } from '@/lib/tauri-bridge'
import { ShieldCheckIcon, CloudIcon, ArrowPathIcon } from '@heroicons/react/24/solid'

const MODE_ICONS = {
  'top-secret': { icon: ShieldCheckIcon, color: 'text-red-500', label: '绝密' },
  hybrid: { icon: ArrowPathIcon, color: 'text-amber-500', label: '混合' },
  cloud: { icon: CloudIcon, color: 'text-blue-500', label: '云端' },
} as const

export function ModeIndicator({ showLabel = true }: { showLabel?: boolean }) {
  const { mode } = useAppModeStore()

  if (!isTauri()) return null

  const config = MODE_ICONS[mode]
  const Icon = config.icon

  return (
    <div className="flex items-center gap-1" title={`当前模式: ${config.label}`}>
      <Icon className={`h-4 w-4 ${config.color}`} />
      {showLabel && (
        <span className={`text-xs font-medium ${config.color}`}>
          {config.label}
        </span>
      )}
    </div>
  )
}
