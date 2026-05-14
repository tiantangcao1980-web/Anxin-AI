/**
 * SkillCard — 单个 skill 卡片
 *
 * 顶部：emoji icon + 标题 + category 徽章
 * 中部：一句话描述
 * 底部：author + 绿色开关 + 详情按钮
 */

import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/components/ui/utils'

import type { Skill, SkillCategory } from '@/lib/api/skills'

import {
  CATEGORY_LABEL,
  TYPE_LABEL,
  CATEGORY_BADGE_CLASS,
} from './skillsTaxonomy'

interface SkillCardProps {
  skill: Skill
  onToggle: (next: boolean) => void
  onOpenDetail: () => void
  onExecute?: () => void
}

export function SkillCard({ skill, onToggle, onOpenDetail }: SkillCardProps) {
  const categoryLabel = CATEGORY_LABEL[skill.category as SkillCategory] ?? skill.category
  const typeLabel = TYPE_LABEL[skill.type] ?? skill.type
  const badgeClass =
    CATEGORY_BADGE_CLASS[skill.category as SkillCategory] ??
    'bg-muted text-muted-foreground'

  return (
    <Card
      className={cn(
        'group flex h-full flex-col gap-3 p-4 transition-all',
        'hover:border-primary/40 hover:shadow-sm',
        skill.enabled && 'border-emerald-300/60 dark:border-emerald-700/40',
      )}
    >
      {/* 顶部：icon + 标题 + 开关 */}
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-muted/60 text-xl ring-1 ring-border/50">
          <span aria-hidden>{skill.icon ?? '✨'}</span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={onOpenDetail}
              className="truncate text-left text-sm font-semibold text-foreground transition-colors hover:text-primary"
              title={skill.display_name}
            >
              {skill.display_name}
            </button>
            <Switch
              checked={skill.enabled}
              onCheckedChange={onToggle}
              aria-label={`${skill.enabled ? '禁用' : '启用'} ${skill.display_name}`}
              className="data-[state=checked]:bg-emerald-500"
            />
          </div>
          <p className="mt-0.5 truncate font-mono text-[10px] text-muted-foreground">
            {skill.name}
          </p>
        </div>
      </div>

      {/* 描述 */}
      <p className="line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {skill.description}
      </p>

      {/* 徽章 */}
      <div className="flex flex-wrap items-center gap-1">
        <Badge variant="outline" className={cn('text-[10px]', badgeClass)}>
          {categoryLabel}
        </Badge>
        <Badge variant="outline" className="text-[10px]">
          {typeLabel}
        </Badge>
        {skill.requires_apps.length > 0 && (
          <Badge variant="outline" className="text-[10px] text-amber-700 dark:text-amber-300">
            需 {skill.requires_apps.length} 项授权
          </Badge>
        )}
      </div>

      {/* 底部：author + 详情 */}
      <div className="mt-auto flex items-center justify-between gap-2 pt-1">
        <span className="truncate text-[11px] text-muted-foreground" title={skill.author}>
          by {skill.author}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={onOpenDetail}
        >
          <icons.Info className="size-3" />
          详情
        </Button>
      </div>
    </Card>
  )
}
