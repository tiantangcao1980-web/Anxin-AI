/**
 * AgentsPage — V3 智能体中心 (P8-C 真业务化)
 *
 * 替换 P0 占位版：展示 10 个 user-facing persona 网格。
 *   - 顶部：标题 + 副标题 + 搜索 + filter（已实装 / 全部 / 规划中）
 *   - 网格：响应式 1/2/3/4 列
 *   - 点 persona → 跳 /v3/personas/{persona_id}
 *
 * 数据来源：personasStore（VITE_PERSONAS_MOCK=true 切换 mock）
 */

import { useEffect, useMemo } from 'react'
import { icons } from '@/lib/icons'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn } from '@/components/ui/utils'

import { PersonaCard } from '@/components/v3/personas/PersonaCard'

import {
  usePersonasStore,
  type PersonaImplementedFilter,
} from '@/lib/store/personasStore'

export default function AgentsPage() {
  const navigate = useNavigate()

  const personas = usePersonasStore((s) => s.personas)
  const loading = usePersonasStore((s) => s.loading)
  const loadError = usePersonasStore((s) => s.loadError)
  const searchQuery = usePersonasStore((s) => s.searchQuery)
  const implementedFilter = usePersonasStore((s) => s.implementedFilter)

  const loadPersonas = usePersonasStore((s) => s.loadPersonas)
  const setSearch = usePersonasStore((s) => s.setSearch)
  const setImplementedFilter = usePersonasStore((s) => s.setImplementedFilter)
  const getFilteredPersonas = usePersonasStore((s) => s.getFilteredPersonas)

  useEffect(() => {
    if (personas.length === 0) {
      loadPersonas()
    }
  }, [loadPersonas, personas.length])

  const filtered = useMemo(
    () => getFilteredPersonas(),
    [personas, searchQuery, implementedFilter, getFilteredPersonas],
  )

  const implementedCount = personas.filter((p) => p.is_implemented).length
  const plannedCount = personas.length - implementedCount

  const enter = (personaId: string) => {
    navigate(`/v3/personas/${personaId}`)
  }

  return (
    <div className="mx-auto flex h-full max-w-7xl flex-col gap-5 p-6">
      {/* 顶栏 */}
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <icons.Bot className="size-6" />
          </div>
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">
              智能体
            </h1>
            <p className="mt-0.5 max-w-2xl text-sm text-muted-foreground">
              10 个人格化智能体 — 对外人格化、对内能力化。每个 persona 在后台编排
              specialized agents + skills + 集成应用。
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => loadPersonas()}
            disabled={loading}
          >
            <icons.RefreshCcw className={loading ? 'animate-spin' : ''} />
            刷新
          </Button>
        </div>
      </header>

      {/* 计数条 */}
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <Badge
          variant="outline"
          className="rounded-full bg-muted px-2 py-0.5 font-medium text-foreground"
        >
          {personas.length} 个 persona
        </Badge>
        <span>· 已实装 {implementedCount} 个</span>
        <span>· 规划中 {plannedCount} 个</span>
        <span>· 当前过滤后 {filtered.length} 个</span>
      </div>

      {/* 搜索 + filter */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[260px] flex-1">
          <icons.Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索 persona 名称 / 描述 / 能力 / 业务域……"
            className="pl-9"
          />
        </div>
        <Tabs
          value={implementedFilter}
          onValueChange={(v) => setImplementedFilter(v as PersonaImplementedFilter)}
        >
          <TabsList>
            <TabsTrigger value="all">全部</TabsTrigger>
            <TabsTrigger value="implemented">已实装</TabsTrigger>
            <TabsTrigger value="planned">规划中</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* 错误 */}
      {loadError && (
        <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-500/10 dark:text-red-300">
          加载失败：{loadError}
        </div>
      )}

      {/* 网格 */}
      <main className="min-w-0 flex-1">
        {loading && personas.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
            正在加载 persona 列表……
          </div>
        ) : filtered.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border/60 p-10 text-center text-sm text-muted-foreground">
            没有匹配的 persona — 试试清空搜索词或切换过滤
          </div>
        ) : (
          <div
            className={cn(
              'grid gap-4',
              'grid-cols-1 md:grid-cols-2 xl:grid-cols-3',
            )}
          >
            {filtered.map((p) => (
              <PersonaCard
                key={p.persona_id}
                persona={p}
                onEnter={() => enter(p.persona_id)}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
