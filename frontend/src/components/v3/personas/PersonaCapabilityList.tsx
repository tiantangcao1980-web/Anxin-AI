/**
 * PersonaCapabilityList — persona 能力清单
 *
 * 列表展示 persona.capabilities，每条带"已实装/规划中"状态徽章。
 * 也可设置 onPick 让父组件知道用户选择了哪条能力（→ 触发 CapabilityRunner）。
 */

import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/components/ui/utils'

interface Props {
  capabilities: string[]
  isImplemented?: boolean
  selectedCapability?: string | null
  onPick?: (capability: string) => void
  className?: string
}

export function PersonaCapabilityList({
  capabilities,
  isImplemented = false,
  selectedCapability,
  onPick,
  className,
}: Props) {
  if (capabilities.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">该 persona 尚未声明能力清单。</p>
    )
  }

  return (
    <ul className={cn('flex flex-col gap-2', className)}>
      {capabilities.map((cap) => {
        const active = selectedCapability === cap
        return (
          <li key={cap}>
            <button
              type="button"
              onClick={() => onPick?.(cap)}
              disabled={!onPick}
              className={cn(
                'group flex w-full items-start gap-2 rounded-md border border-border/50 bg-card px-3 py-2 text-left text-sm transition-all',
                onPick && 'cursor-pointer hover:border-primary/40 hover:bg-muted/40',
                active && 'border-primary/60 bg-primary/5 ring-1 ring-primary/30',
                !onPick && 'cursor-default',
              )}
            >
              <icons.Sparkles
                className={cn(
                  'mt-0.5 size-3.5 shrink-0 text-muted-foreground',
                  active && 'text-primary',
                )}
              />
              <span className="flex-1 leading-snug text-foreground">{cap}</span>
              {isImplemented ? (
                <Badge
                  variant="outline"
                  className="shrink-0 border-emerald-300/60 bg-emerald-500/10 text-[10px] text-emerald-700 dark:border-emerald-700/50 dark:text-emerald-300"
                >
                  <icons.CheckCircle2 className="mr-1 size-3" />
                  已实装
                </Badge>
              ) : (
                <Badge
                  variant="outline"
                  className="shrink-0 border-amber-300/60 bg-amber-500/10 text-[10px] text-amber-700 dark:border-amber-700/50 dark:text-amber-300"
                >
                  <icons.Clock3 className="mr-1 size-3" />
                  规划中
                </Badge>
              )}
            </button>
          </li>
        )
      })}
    </ul>
  )
}
