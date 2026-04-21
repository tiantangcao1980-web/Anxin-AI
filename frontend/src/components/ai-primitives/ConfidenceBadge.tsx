import { ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react'
import { cn } from '@/lib/utils'

export type ConfidenceLevel = 'high' | 'medium' | 'low'

interface ConfidenceBadgeProps {
  level: ConfidenceLevel
  label?: string
  showIcon?: boolean
  size?: 'sm' | 'md'
  className?: string
}

const CONFIG: Record<ConfidenceLevel, { text: string; cls: string; Icon: typeof ShieldCheck }> = {
  high: {
    text: '高置信',
    cls: 'bg-confidence-high/10 text-confidence-high ring-confidence-high/20',
    Icon: ShieldCheck,
  },
  medium: {
    text: '中置信',
    cls: 'bg-confidence-medium/10 text-confidence-medium ring-confidence-medium/20',
    Icon: ShieldAlert,
  },
  low: {
    text: '需复核',
    cls: 'bg-confidence-low/10 text-confidence-low ring-confidence-low/20',
    Icon: ShieldQuestion,
  },
}

export function ConfidenceBadge({
  level,
  label,
  showIcon = true,
  size = 'sm',
  className,
}: ConfidenceBadgeProps) {
  const { text, cls, Icon } = CONFIG[level]
  const displayText = label ?? text
  const sizeCls =
    size === 'sm'
      ? 'h-5 px-2 gap-1 text-[11px]'
      : 'h-6 px-2.5 gap-1.5 text-caption'

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-pill font-medium leading-none',
        'ring-1 ring-inset',
        sizeCls,
        cls,
        className,
      )}
      role="status"
      aria-label={`置信度：${displayText}`}
    >
      {showIcon && <Icon className={size === 'sm' ? 'size-3' : 'size-3.5'} />}
      {displayText}
    </span>
  )
}
