/**
 * EmptyState — 全站统一空状态组件
 *
 * 用法：
 *   <EmptyState icon="FileText" title="暂无文档" description="点击上方按钮创建" />
 *   <EmptyState icon="Search" title="未找到结果" action={{ label: "重置筛选", onClick: reset }} />
 *
 * 设计规范 (DESIGN.md §4 / §7):
 * - 居中布局，icon + 标题 + 说明 + 可选操作按钮
 * - icon 使用 muted-foreground/30，标题 font-medium，说明 text-muted-foreground
 * - 按钮使用 buttonStyle.secondary
 */

import { icons } from '@/lib/icons'
import { buttonStyle, iconSize } from '@/lib/design-tokens'

interface EmptyStateProps {
  icon?: keyof typeof icons
  title: string
  description?: string
  action?: {
    label: string
    onClick: () => void
    icon?: keyof typeof icons
  }
  compact?: boolean
  className?: string
}

export function EmptyState({
  icon = 'FileText',
  title,
  description,
  action,
  compact = false,
  className = '',
}: EmptyStateProps) {
  const Icon = icons[icon]
  const ActionIcon = action?.icon ? icons[action.icon] : null

  return (
    <div className={`flex items-center justify-center ${compact ? 'py-8' : 'py-16'} ${className}`}>
      <div className="text-center max-w-sm px-4">
        <div className={`mx-auto mb-4 flex items-center justify-center rounded-2xl bg-muted ${compact ? 'w-12 h-12' : 'w-16 h-16'}`}>
          <Icon className={`${compact ? iconSize.lg : iconSize.xl} text-muted-foreground/30`} />
        </div>
        <p className={`font-medium text-foreground ${compact ? 'text-sm' : 'text-base'}`}>{title}</p>
        {description && (
          <p className={`mt-1.5 text-muted-foreground ${compact ? 'text-xs' : 'text-sm'}`}>{description}</p>
        )}
        {action && (
          <button onClick={action.onClick} className={`${buttonStyle.secondary} mt-4 inline-flex items-center gap-2`}>
            {ActionIcon && <ActionIcon className={iconSize.sm} />}
            {action.label}
          </button>
        )}
      </div>
    </div>
  )
}
