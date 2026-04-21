import type { ReactNode } from 'react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { cn } from '@/lib/utils'

export type RiskLevel = 'high' | 'medium' | 'low'

interface RiskHighlightProps {
  level: RiskLevel
  reason?: string
  category?: string
  children: ReactNode
  className?: string
  onClick?: () => void
  interactive?: boolean
}

const LEVEL_CLS: Record<RiskLevel, string> = {
  high: 'bg-risk-high-surface text-foreground decoration-risk-high/70 border-b-[1.5px] border-risk-high/50',
  medium: 'bg-risk-medium-surface text-foreground decoration-risk-medium/70 border-b-[1.5px] border-risk-medium/40',
  low: 'bg-risk-low-surface text-foreground decoration-risk-low/60 border-b border-risk-low/40 border-dashed',
}

const LEVEL_LABEL: Record<RiskLevel, string> = {
  high: '高风险',
  medium: '中风险',
  low: '提示',
}

export function RiskHighlight({
  level,
  reason,
  category,
  children,
  className,
  onClick,
  interactive = true,
}: RiskHighlightProps) {
  const base = (
    <span
      onClick={onClick}
      className={cn(
        'rounded-subtle px-0.5 py-0.5 transition-colors duration-fast ease-standard',
        LEVEL_CLS[level],
        interactive && 'cursor-pointer hover:brightness-95',
        'focus-visible:outline-none focus-visible:shadow-focus-ring',
        className,
      )}
      tabIndex={interactive ? 0 : undefined}
      role={interactive ? 'button' : undefined}
      aria-label={`${LEVEL_LABEL[level]}${category ? ` · ${category}` : ''}`}
    >
      {children}
    </span>
  )

  if (!interactive || !reason) return base

  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>{base}</Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            side="top"
            sideOffset={6}
            className={cn(
              'z-tooltip max-w-xs rounded-dd border border-border bg-popover px-3 py-2',
              'text-caption text-foreground shadow-elev-3',
              'data-[state=delayed-open]:animate-suggestion-in',
            )}
          >
            <div className="flex items-center gap-1.5 font-medium">
              <span
                className={cn(
                  'size-1.5 rounded-pill',
                  level === 'high' && 'bg-risk-high',
                  level === 'medium' && 'bg-risk-medium',
                  level === 'low' && 'bg-risk-low',
                )}
              />
              {LEVEL_LABEL[level]}
              {category && <span className="text-foreground-tertiary">· {category}</span>}
            </div>
            {reason && (
              <p className="mt-1 text-foreground-tertiary leading-relaxed">{reason}</p>
            )}
            <Tooltip.Arrow className="fill-popover" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  )
}
