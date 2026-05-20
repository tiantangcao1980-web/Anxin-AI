/**
 * PersonaSkillsBadges — backed_by_skills 徽章列表
 *
 * 每个 skill 显示为一个小徽章；超过 max 时折叠 "+N"。
 */

import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/components/ui/utils'

interface Props {
  skills: string[]
  max?: number
  className?: string
}

export function PersonaSkillsBadges({ skills, max = 8, className }: Props) {
  if (skills.length === 0) {
    return null
  }
  const visible = skills.slice(0, max)
  const overflow = skills.length - visible.length

  return (
    <div className={cn('flex flex-wrap items-center gap-1', className)}>
      {visible.map((s) => (
        <Badge
          key={s}
          variant="outline"
          className="gap-1 px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground"
          title={s}
        >
          <icons.Wrench className="size-3 opacity-60" />
          {s}
        </Badge>
      ))}
      {overflow > 0 && (
        <Badge
          variant="outline"
          className="px-1.5 py-0.5 text-[10px] text-muted-foreground"
          title={skills.slice(max).join(', ')}
        >
          +{overflow}
        </Badge>
      )}
    </div>
  )
}
