/**
 * SkillSearchBar — 顶部搜索 + persona 过滤
 *
 * 左侧 search input；右侧 persona Select（"全部角色" + 已知 personas + 任意当前数据中出现的额外 personas）
 */

import { icons } from '@/lib/icons'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/components/ui/utils'

import { KNOWN_PERSONAS } from './skillsTaxonomy'

interface SkillSearchBarProps {
  search: string
  onSearchChange: (q: string) => void

  persona: string // 'all' or persona name
  onPersonaChange: (p: string) => void

  /** 来自数据的真实 persona 集（用于补全 KNOWN_PERSONAS 之外的） */
  personaCounts: Record<string, number>

  className?: string
}

export function SkillSearchBar({
  search,
  onSearchChange,
  persona,
  onPersonaChange,
  personaCounts,
  className,
}: SkillSearchBarProps) {
  // 合并 known + 数据中实际出现的，去重
  const allPersonas = Array.from(
    new Set<string>([...KNOWN_PERSONAS, ...Object.keys(personaCounts)]),
  ).filter((p) => p !== '全部')

  return (
    <div className={cn('flex flex-wrap items-center gap-2', className)}>
      <div className="relative min-w-0 flex-1">
        <icons.Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="搜索技能名称、触发词、关键字..."
          className="pl-9 pr-9"
        />
        {search && (
          <button
            type="button"
            onClick={() => onSearchChange('')}
            className="absolute right-2 top-1/2 inline-flex size-6 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            aria-label="清空搜索"
          >
            <icons.X className="size-3.5" />
          </button>
        )}
      </div>

      <Select value={persona} onValueChange={onPersonaChange}>
        <SelectTrigger className="w-[180px] shrink-0">
          <SelectValue placeholder="按角色过滤" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">全部角色</SelectItem>
          {allPersonas.map((p) => (
            <SelectItem key={p} value={p}>
              {p}
              {personaCounts[p] ? (
                <span className="ml-2 text-[10px] text-muted-foreground">
                  ({personaCounts[p]})
                </span>
              ) : null}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
