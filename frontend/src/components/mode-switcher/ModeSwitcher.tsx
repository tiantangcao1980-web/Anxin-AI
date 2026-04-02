/**
 * 运行模式切换器
 *
 * 在顶部导航栏显示当前模式，并提供切换功能。
 * 三种模式：绝密🔒 / 混合🔄 / 云端☁️
 */

import { useState, useCallback } from 'react'
import { useAppModeStore } from '@/lib/store'
import { switchMode, isTauri, type AppMode } from '@/lib/tauri-bridge'
import { ShieldCheckIcon, CloudIcon, ArrowPathIcon } from '@heroicons/react/24/outline'

const MODE_CONFIG = {
  'top-secret': {
    label: '绝密模式',
    icon: ShieldCheckIcon,
    color: 'text-red-600 dark:text-red-400',
    bg: 'bg-red-50 dark:bg-red-950/30',
    border: 'border-red-200 dark:border-red-800',
    description: '完全本地处理，数据不离设备',
  },
  hybrid: {
    label: '混合模式',
    icon: ArrowPathIcon,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    border: 'border-amber-200 dark:border-amber-800',
    description: '本地优先，选择性云同步',
  },
  cloud: {
    label: '云端模式',
    icon: CloudIcon,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-50 dark:bg-blue-950/30',
    border: 'border-blue-200 dark:border-blue-800',
    description: '全部云端处理，功能完整',
  },
} as const

export function ModeSwitcher() {
  const { mode, setMode } = useAppModeStore()
  const [isOpen, setIsOpen] = useState(false)
  const [isSwitching, setIsSwitching] = useState(false)

  // Web 模式下不显示
  if (!isTauri()) return null

  const currentConfig = MODE_CONFIG[mode]
  const Icon = currentConfig.icon

  const handleSwitch = useCallback(async (newMode: AppMode) => {
    if (newMode === mode || isSwitching) return

    setIsSwitching(true)
    try {
      const result = await switchMode(newMode)
      if (result?.success) {
        setMode(newMode)
      }
    } catch (error) {
      console.error('模式切换失败:', error)
    } finally {
      setIsSwitching(false)
      setIsOpen(false)
    }
  }, [mode, isSwitching, setMode])

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border text-sm font-medium transition-all ${currentConfig.bg} ${currentConfig.border} ${currentConfig.color} hover:opacity-80`}
        title={currentConfig.description}
      >
        <Icon className="h-4 w-4" />
        <span className="hidden sm:inline">{currentConfig.label}</span>
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full mt-1 z-50 w-64 rounded-xl border border-border bg-popover shadow-lg p-1.5">
            {(Object.entries(MODE_CONFIG) as [AppMode, typeof MODE_CONFIG[AppMode]][]).map(
              ([key, config]) => {
                const ModeIcon = config.icon
                const isActive = key === mode

                return (
                  <button
                    key={key}
                    onClick={() => handleSwitch(key)}
                    disabled={isSwitching}
                    className={`w-full flex items-start gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                      isActive
                        ? `${config.bg} ${config.border} border`
                        : 'hover:bg-accent border border-transparent'
                    } ${isSwitching ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    <ModeIcon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${config.color}`} />
                    <div>
                      <div className={`text-sm font-medium ${isActive ? config.color : 'text-foreground'}`}>
                        {config.label}
                        {isActive && <span className="ml-1.5 text-xs opacity-60">● 当前</span>}
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {config.description}
                      </div>
                    </div>
                  </button>
                )
              }
            )}
          </div>
        </>
      )}
    </div>
  )
}
