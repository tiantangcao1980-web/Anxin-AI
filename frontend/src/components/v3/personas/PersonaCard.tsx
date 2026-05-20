/**
 * PersonaCard — 单个 persona 卡片
 *
 * 顶部：emoji + display_name + 实装状态徽章
 * 中部：description（一句话定位）
 * 中下：能力清单前 3 条 + 总数
 * 底部：skills/apps 徽章计数 + "进入工作台" CTA
 */

import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { cn } from '@/components/ui/utils'

import type { Persona } from '@/lib/api/personas'

interface Props {
  persona: Persona
  onEnter: () => void
}

const DOMAIN_BADGE_CLASS: Record<string, string> = {
  综合协调: 'border-sky-300/60 bg-sky-500/10 text-sky-700 dark:text-sky-300',
  合规经营: 'border-violet-300/60 bg-violet-500/10 text-violet-700 dark:text-violet-300',
  增长获客: 'border-orange-300/60 bg-orange-500/10 text-orange-700 dark:text-orange-300',
  出海跨境: 'border-emerald-300/60 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300',
}

export function PersonaCard({ persona, onEnter }: Props) {
  const implemented = !!persona.is_implemented
  const domainClass = persona.domain ? DOMAIN_BADGE_CLASS[persona.domain] : ''

  return (
    <Card
      className={cn(
        'group relative flex h-full flex-col gap-3 p-5 transition-all',
        'hover:border-primary/40 hover:shadow-md',
        implemented && 'border-emerald-300/60 dark:border-emerald-700/40',
      )}
    >
      {/* 顶部：emoji + 名称 + 状态 */}
      <div className="flex items-start gap-3">
        <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-muted/60 text-2xl ring-1 ring-border/50">
          <span aria-hidden>{persona.emoji}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3
              className="truncate text-base font-semibold tracking-tight text-foreground"
              title={persona.display_name}
            >
              {persona.display_name}
            </h3>
            {implemented ? (
              <Badge
                variant="outline"
                className="border-emerald-300/60 bg-emerald-500/10 text-[10px] text-emerald-700 dark:border-emerald-700/50 dark:text-emerald-300"
              >
                <icons.CheckCircle2 className="mr-1 size-3" />
                已实装
              </Badge>
            ) : (
              <Badge
                variant="outline"
                className="border-amber-300/60 bg-amber-500/10 text-[10px] text-amber-700 dark:border-amber-700/50 dark:text-amber-300"
              >
                <icons.Clock3 className="mr-1 size-3" />
                规划中
              </Badge>
            )}
          </div>
          <p className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground">
            {persona.persona_id}
          </p>
        </div>
      </div>

      {/* 一句话描述 */}
      <p className="line-clamp-2 text-sm leading-relaxed text-muted-foreground">
        {persona.description}
      </p>

      {/* 能力前 3 条预览 */}
      {persona.capabilities.length > 0 && (
        <ul className="space-y-1">
          {persona.capabilities.slice(0, 3).map((c) => (
            <li
              key={c}
              className="flex items-start gap-1.5 text-xs leading-snug text-foreground/80"
            >
              <span className="mt-1 size-1 shrink-0 rounded-full bg-primary/60" />
              <span className="line-clamp-1">{c}</span>
            </li>
          ))}
          {persona.capabilities.length > 3 && (
            <li className="pl-3 text-[11px] text-muted-foreground">
              + 还有 {persona.capabilities.length - 3} 项能力
            </li>
          )}
        </ul>
      )}

      {/* 域 + skills/apps 计数 */}
      <div className="flex flex-wrap items-center gap-1.5 pt-1">
        {persona.domain && (
          <Badge variant="outline" className={cn('text-[10px]', domainClass)}>
            {persona.domain}
          </Badge>
        )}
        <Badge
          variant="outline"
          className="gap-1 text-[10px] text-muted-foreground"
          title={persona.backed_by_skills.join(', ')}
        >
          <icons.Hammer className="size-3 opacity-60" />
          {persona.backed_by_skills.length} 技能
        </Badge>
        <Badge
          variant="outline"
          className="gap-1 text-[10px] text-muted-foreground"
          title={persona.supported_apps.join(', ')}
        >
          <icons.Plug className="size-3 opacity-60" />
          {persona.supported_apps.length} 应用
        </Badge>
      </div>

      {/* CTA */}
      <div className="mt-auto flex items-center justify-end pt-2">
        <Button size="sm" variant="default" onClick={onEnter} className="gap-1">
          进入工作台
          <icons.ArrowRight className="size-3.5" />
        </Button>
      </div>
    </Card>
  )
}
