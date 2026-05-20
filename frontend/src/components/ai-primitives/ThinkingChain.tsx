import { useState, type ReactNode } from 'react'
import { icons } from '@/lib/icons'
import { cn } from '@/lib/utils'

export type ThinkingStepStatus = 'pending' | 'running' | 'done' | 'error'

export interface ThinkingStep {
  id: string
  title: string
  detail?: ReactNode
  status?: ThinkingStepStatus
  duration?: number
}

interface ThinkingChainProps {
  steps: ThinkingStep[]
  defaultOpen?: boolean
  streaming?: boolean
  className?: string
}

const STATUS_ICON: Record<ThinkingStepStatus, ReactNode> = {
  pending: <div className="size-2 rounded-pill bg-foreground-disabled" />,
  running: <icons.Loader2 className="size-3.5 text-ai-thinking animate-spin" />,
  done: <icons.Check className="size-3.5 text-ai-suggestion" />,
  error: <icons.AlertCircle className="size-3.5 text-destructive" />,
}

export function ThinkingChain({
  steps,
  defaultOpen = false,
  streaming = false,
  className,
}: ThinkingChainProps) {
  const [open, setOpen] = useState(defaultOpen || streaming)
  const totalMs = steps.reduce((acc, s) => acc + (s.duration ?? 0), 0)

  return (
    <div
      className={cn(
        'rounded-dd_lg border border-border-subtle bg-ai-thinking-surface/60',
        'transition-all duration-normal ease-standard',
        className,
      )}
    >
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className={cn(
          'flex w-full items-center gap-2 px-3 py-2',
          'text-caption text-muted-foreground',
          'hover:text-foreground focus-visible:outline-none focus-visible:shadow-focus-ring',
          'rounded-dd_lg',
        )}
        aria-expanded={open}
      >
        <icons.Brain
          className={cn(
            'size-3.5 text-ai-thinking',
            streaming && 'animate-ai-pulse',
          )}
        />
        <span className="font-medium">
          {streaming ? '正在推理…' : `思维链 · ${steps.length} 步`}
        </span>
        {totalMs > 0 && !streaming && (
          <span className="text-foreground-tertiary">· {(totalMs / 1000).toFixed(1)}s</span>
        )}
        <icons.ChevronDown
          className={cn(
            'ml-auto size-3.5 transition-transform duration-fast ease-standard',
            open && 'rotate-180',
          )}
        />
      </button>

      {open && (
        <ol className="relative ml-5 space-y-2 border-l border-border-subtle px-4 pb-3 pt-1">
          {steps.map((step) => {
            const status = step.status ?? 'done'
            return (
              <li key={step.id} className="relative">
                <span
                  className={cn(
                    'absolute -left-[22px] top-0.5 flex size-4 items-center justify-center',
                    'rounded-pill bg-background ring-1 ring-border-subtle',
                  )}
                >
                  {STATUS_ICON[status]}
                </span>
                <div className="text-caption text-foreground">{step.title}</div>
                {step.detail && (
                  <div className="mt-0.5 text-caption text-foreground-tertiary leading-relaxed">
                    {step.detail}
                  </div>
                )}
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}
