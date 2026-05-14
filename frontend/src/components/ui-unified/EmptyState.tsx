/**
 * EmptyState — 全站统一空状态组件 (v2)
 *
 * v2 新增：
 * - `variant` 预设业务语境（default / search / error / ai / success）
 * - `illustration` 槽位（可传自定义 SVG/Lottie/组件）
 * - 入场动画（淡入 + 上移 + icon pop）
 * - 响应式内边距
 *
 * 保留 v1 的所有 props，向后 100% 兼容。
 */

import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { buttonStyle, iconSize } from '@/lib/design-tokens'
import { cn } from '@/lib/utils'

type Variant = 'default' | 'search' | 'error' | 'ai' | 'success'

interface EmptyStateProps {
  icon?: keyof typeof icons
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
    icon?: keyof typeof icons
  }
  /** 次要操作（链接态） */
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  compact?: boolean
  /** 业务语境变体：决定默认图标、图标底色、文案语气 */
  variant?: Variant
  /** 自定义插图（覆盖默认图标圈） */
  illustration?: ReactNode
  className?: string
}

const VARIANT_ICON: Record<Variant, keyof typeof icons> = {
  default: 'FileText',
  search: 'Search',
  error: 'AlertCircle',
  ai: 'Sparkles',
  success: 'CheckCircle',
}

const VARIANT_ICON_CLS: Record<Variant, string> = {
  default: 'bg-surface-2 text-foreground-tertiary',
  search: 'bg-surface-2 text-foreground-tertiary',
  error: 'bg-destructive/10 text-destructive',
  ai: 'bg-ai-surface text-ai',
  success: 'bg-success/10 text-success',
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  secondaryAction,
  compact = false,
  variant = 'default',
  illustration,
  className = '',
}: EmptyStateProps) {
  const iconKey = icon ?? VARIANT_ICON[variant]
  const Icon = icons[iconKey]
  const ActionIcon = action?.icon ? icons[action.icon] : null
  const iconBoxCls = VARIANT_ICON_CLS[variant]

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.2, 0, 0, 1] }}
      className={cn(
        'flex items-center justify-center',
        compact ? 'py-8' : 'py-14 sm:py-16',
        className,
      )}
    >
      <div className="text-center max-w-sm px-4">
        {illustration ? (
          <div className="mx-auto mb-4 flex items-center justify-center">{illustration}</div>
        ) : (
          <motion.div
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{
              type: 'spring',
              stiffness: 260,
              damping: 18,
              delay: 0.1,
            }}
            className={cn(
              'mx-auto mb-4 flex items-center justify-center rounded-dd_xl',
              iconBoxCls,
              compact ? 'w-12 h-12' : 'w-16 h-16',
              variant === 'ai' && 'animate-ai-pulse',
            )}
          >
            <Icon className={compact ? iconSize.lg : iconSize.xl} />
          </motion.div>
        )}

        <p
          className={cn(
            'font-medium text-foreground',
            compact ? 'text-body' : 'text-body-lg',
          )}
        >
          {title}
        </p>
        {description && (
          <p
            className={cn(
              'mt-1.5 text-foreground-tertiary leading-relaxed',
              compact ? 'text-caption' : 'text-body-sm',
            )}
          >
            {description}
          </p>
        )}

        {(action || secondaryAction) && (
          <div className="mt-5 flex items-center justify-center gap-3">
            {action && (
              <button
                onClick={action.onClick}
                className={cn(buttonStyle.primary, 'inline-flex items-center gap-2')}
              >
                {ActionIcon && <ActionIcon className={iconSize.sm} />}
                {action.label}
              </button>
            )}
            {secondaryAction && (
              <button
                onClick={secondaryAction.onClick}
                className={cn(buttonStyle.ghost, 'inline-flex items-center')}
              >
                {secondaryAction.label}
              </button>
            )}
          </div>
        )}
      </div>
    </motion.div>
  )
}
