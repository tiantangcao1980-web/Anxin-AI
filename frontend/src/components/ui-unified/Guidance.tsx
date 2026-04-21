import { useEffect, useState, type ReactNode } from 'react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, X } from 'lucide-react'
import { cn } from '@/lib/utils'

interface AttentionPulseProps {
  children: ReactNode
  /** 是否启用（默认 true）；完成引导后关闭 */
  active?: boolean
  /** 色调，默认 primary */
  tone?: 'primary' | 'ai' | 'warning'
  className?: string
}

/**
 * AttentionPulse — 注意力光环脉冲
 *
 * 套在任何元素外层，绘制柔和呼吸光环，引导用户视线。
 *
 * 建议使用场景：
 * - 首次引导：新功能按钮外圈
 * - 待办提示：未读红点 / 新消息
 * - AI 触发：AI 助手浮窗入口
 *
 * 注意：active=false 时无任何渲染开销，可安全常挂在元素上。
 */
export function AttentionPulse({
  children,
  active = true,
  tone = 'primary',
  className,
}: AttentionPulseProps) {
  const toneCls = {
    primary: 'ring-primary/35 after:bg-primary/15',
    ai: 'ring-ai/40 after:bg-ai/15',
    warning: 'ring-warning/40 after:bg-warning/20',
  }[tone]

  return (
    <span className={cn('relative inline-flex', className)}>
      {active && (
        <span
          aria-hidden
          className={cn(
            'pointer-events-none absolute inset-0 z-base rounded-pill',
            'after:absolute after:inset-0 after:rounded-pill after:animate-ai-pulse',
            'ring-2 ring-inset',
            toneCls,
          )}
        />
      )}
      {children}
    </span>
  )
}

interface NewBadgeProps {
  /** 显示文本，默认「新」 */
  label?: string
  /** 显示小圆点而非文字 */
  dot?: boolean
  className?: string
}

/**
 * NewBadge — 右上角"新"角标
 *
 * 带 pop-in 入场动画，用于新功能/新消息醒目提示。
 */
export function NewBadge({ label = '新', dot = false, className }: NewBadgeProps) {
  return (
    <motion.span
      initial={{ scale: 0, rotate: -30 }}
      animate={{ scale: 1, rotate: 0 }}
      transition={{ type: 'spring', stiffness: 600, damping: 16 }}
      className={cn(
        'inline-flex items-center justify-center font-medium',
        'bg-primary text-primary-foreground shadow-elev-1',
        dot ? 'size-2 rounded-pill' : 'min-w-4 h-4 rounded-pill px-1 text-[10px] leading-none',
        className,
      )}
    >
      {dot ? null : label}
    </motion.span>
  )
}

interface InteractiveHintProps {
  children: ReactNode
  /** 引导文案（必填） */
  hint: ReactNode
  /** 方向 */
  side?: 'top' | 'right' | 'bottom' | 'left'
  /** 默认展开（用于 onboarding），用户关闭后记住 dismiss */
  defaultOpen?: boolean
  /** localStorage key，开启后关闭态会记忆 */
  storageKey?: string
  /** 标题 */
  title?: string
  className?: string
}

/**
 * InteractiveHint — 首用/新特性气泡引导
 *
 * 业务场景：
 * - 新功能上线，第一次出现时自动展开引导
 * - 用户点 X 后，localStorage 记忆，再不出现
 *
 * 与 Tooltip 区别：InteractiveHint 是"教学性质"（默认显示 + 可关闭），
 * Tooltip 是"辅助性质"（hover 才出现）。
 */
export function InteractiveHint({
  children,
  hint,
  side = 'bottom',
  defaultOpen = true,
  storageKey,
  title,
  className,
}: InteractiveHintProps) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (storageKey) {
      const dismissed = typeof window !== 'undefined' && localStorage.getItem(storageKey) === '1'
      if (!dismissed && defaultOpen) setOpen(true)
    } else if (defaultOpen) {
      setOpen(true)
    }
  }, [storageKey, defaultOpen])

  const handleDismiss = () => {
    setOpen(false)
    if (storageKey) localStorage.setItem(storageKey, '1')
  }

  return (
    <Tooltip.Provider>
      <Tooltip.Root open={open}>
        <Tooltip.Trigger asChild>
          <span className={cn('inline-flex', className)}>{children}</span>
        </Tooltip.Trigger>
        <AnimatePresence>
          {open && (
            <Tooltip.Portal forceMount>
              <Tooltip.Content
                side={side}
                sideOffset={10}
                className={cn(
                  'z-tooltip max-w-xs rounded-dd_lg border border-primary/20 bg-card p-3 shadow-elev-4',
                  'text-body-sm text-foreground',
                )}
                asChild
              >
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: side === 'top' ? 6 : -6 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}
                >
                  <div className="flex items-start gap-2">
                    <Sparkles className="mt-0.5 size-4 shrink-0 text-primary animate-ai-pulse" />
                    <div className="min-w-0 flex-1">
                      {title && (
                        <div className="text-body font-medium text-foreground">{title}</div>
                      )}
                      <div className="text-caption leading-relaxed text-foreground-tertiary">
                        {hint}
                      </div>
                    </div>
                    <button
                      onClick={handleDismiss}
                      className={cn(
                        'inline-flex size-5 shrink-0 items-center justify-center rounded-subtle',
                        'text-foreground-tertiary hover:bg-surface-2 hover:text-foreground',
                        'transition-colors duration-fast ease-standard',
                      )}
                      aria-label="关闭引导"
                    >
                      <X className="size-3" />
                    </button>
                  </div>
                  <Tooltip.Arrow className="fill-card" />
                </motion.div>
              </Tooltip.Content>
            </Tooltip.Portal>
          )}
        </AnimatePresence>
      </Tooltip.Root>
    </Tooltip.Provider>
  )
}
