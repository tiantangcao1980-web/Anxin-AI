/**
 * EmptyState — 通用空状态(图标 + 文案)
 *
 * 用于"待审核为空" / "无已授权用户"等场景。
 */

import type { LucideIcon } from 'lucide-react'

import { cn } from '@/components/ui/utils'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  className?: string
}

export function EmptyState({ icon: Icon, title, description, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border border-dashed border-border/60 bg-muted/30 px-6 py-10 text-center',
        className,
      )}
    >
      <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Icon className="size-6" />
      </div>
      <h4 className="mt-3 text-sm font-medium text-foreground">{title}</h4>
      {description && (
        <p className="mt-1 max-w-md text-xs leading-relaxed text-muted-foreground">
          {description}
        </p>
      )}
    </div>
  )
}
