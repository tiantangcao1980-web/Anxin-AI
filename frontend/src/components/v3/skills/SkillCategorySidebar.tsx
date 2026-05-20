/**
 * SkillCategorySidebar — 左侧分组侧栏
 *
 * "全部" + 13 域，每项带 emoji + 中文名 + 计数。
 * sticky 布局；移动端自动 fallback 到顶部水平 chip 列表（响应式）。
 */

import { icons } from '@/lib/icons'
import { cn } from '@/components/ui/utils'

import type { SkillCategory } from '@/lib/api/skills'

import {
  CATEGORY_ICON,
  CATEGORY_LABEL,
  CATEGORY_ORDER,
} from './skillsTaxonomy'

interface SkillCategorySidebarProps {
  value: 'all' | SkillCategory
  onChange: (next: 'all' | SkillCategory) => void
  /** 各 category 的 skill 数量 */
  counts: Record<string, number>
  totalCount: number
  className?: string
}

export function SkillCategorySidebar({
  value,
  onChange,
  counts,
  totalCount,
  className,
}: SkillCategorySidebarProps) {
  const items: Array<{
    key: 'all' | SkillCategory
    label: string
    icon: string
    count: number
  }> = [
    { key: 'all', label: '全部', icon: '✨', count: totalCount },
    ...CATEGORY_ORDER.map((c) => ({
      key: c,
      label: CATEGORY_LABEL[c],
      icon: CATEGORY_ICON[c],
      count: counts[c] ?? 0,
    })),
  ]

  return (
    <aside
      className={cn(
        'lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:w-56 lg:shrink-0 lg:overflow-y-auto',
        className,
      )}
    >
      {/* 桌面端：纵向列表 */}
      <div className="hidden rounded-xl border border-border/60 bg-card p-2 lg:block">
        <div className="flex items-center gap-2 px-2 pb-2 text-xs font-medium text-muted-foreground">
          <icons.Layers className="size-3.5" />
          技能分组
        </div>
        <nav className="flex flex-col gap-0.5">
          {items.map((it) => {
            const active = value === it.key
            return (
              <button
                key={it.key}
                type="button"
                onClick={() => onChange(it.key)}
                className={cn(
                  'flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors',
                  active
                    ? 'bg-primary/10 font-medium text-primary'
                    : 'text-foreground/80 hover:bg-muted/60 hover:text-foreground',
                )}
              >
                <span className="text-base leading-none" aria-hidden>
                  {it.icon}
                </span>
                <span className="flex-1 truncate">{it.label}</span>
                <span
                  className={cn(
                    'shrink-0 rounded-full px-1.5 py-0.5 text-[10px] tabular-nums',
                    active
                      ? 'bg-primary/15 text-primary'
                      : 'bg-muted text-muted-foreground',
                  )}
                >
                  {it.count}
                </span>
              </button>
            )
          })}
        </nav>
      </div>

      {/* 移动端：横向滚动 chip */}
      <div className="-mx-1 flex gap-1.5 overflow-x-auto px-1 pb-2 lg:hidden">
        {items.map((it) => {
          const active = value === it.key
          return (
            <button
              key={it.key}
              type="button"
              onClick={() => onChange(it.key)}
              className={cn(
                'flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1 text-xs transition-colors',
                active
                  ? 'border-primary/40 bg-primary/10 text-primary'
                  : 'border-border bg-card text-foreground/70 hover:bg-muted/60',
              )}
            >
              <span aria-hidden>{it.icon}</span>
              <span>{it.label}</span>
              <span className="rounded-full bg-muted px-1 text-[10px] tabular-nums text-muted-foreground">
                {it.count}
              </span>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
