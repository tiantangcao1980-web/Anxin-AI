/**
 * AppCategoryTabs — 顶部分类 Tab
 *
 * 全部 + 8 大分类，每个 Tab 后带 provider 计数（小角标）。
 * 横向可滚动，避免窄屏溢出。
 */

import { cn } from '@/components/ui/utils'

import type { AppCategoryFilter } from '@/lib/store/appAuthorizationsStore'
import type { AppCategory, AppProvider } from '@/lib/api/appAuthorizations'

interface AppCategoryTabsProps {
  providers: AppProvider[]
  value: AppCategoryFilter
  onChange: (next: AppCategoryFilter) => void
  className?: string
}

interface TabDef {
  key: AppCategoryFilter
  label: string
}

const TABS: TabDef[] = [
  { key: 'all', label: '全部' },
  { key: 'office', label: '办公协作' },
  { key: 'office_storage', label: '文档存储' },
  { key: 'crm', label: 'CRM 销售' },
  { key: 'ecommerce', label: '跨境电商' },
  { key: 'info_source', label: '信息源' },
  { key: 'design', label: '设计创作' },
  { key: 'compliance', label: '法务合规' },
  { key: 'finance', label: '税务财务' },
]

export function AppCategoryTabs({
  providers,
  value,
  onChange,
  className,
}: AppCategoryTabsProps) {
  // 计数：全部 = providers.length；分类 = 该分类的 provider 数
  const countFor = (k: AppCategoryFilter): number => {
    if (k === 'all') return providers.length
    return providers.filter((p) => p.category === (k as AppCategory)).length
  }

  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1',
        className,
      )}
      role="tablist"
    >
      {TABS.map((t) => {
        const active = value === t.key
        const count = countFor(t.key)
        return (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange(t.key)}
            className={cn(
              'inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors',
              active
                ? 'border-primary/30 bg-primary/10 text-primary'
                : 'border-border/60 bg-background text-muted-foreground hover:border-border hover:text-foreground',
            )}
          >
            <span>{t.label}</span>
            <span
              className={cn(
                'inline-flex min-w-[1.25rem] justify-center rounded-full px-1.5 text-[10px] leading-4',
                active ? 'bg-primary/20 text-primary' : 'bg-muted text-muted-foreground',
              )}
            >
              {count}
            </span>
          </button>
        )
      })}
    </div>
  )
}
