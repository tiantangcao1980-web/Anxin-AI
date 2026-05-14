/**
 * PersonaWorkspaceLayout — persona 详情工作台通用布局
 *
 * 三栏：
 *   - 顶部：persona 头像 + 名称 + 描述 + 切换 persona 下拉 + 状态徽章
 *   - 左：聊天面板（slot: chat）
 *   - 右：能力 / 工具面板（slot: tools）
 *
 * 移动端折叠为单列堆叠。
 */

import { icons } from '@/lib/icons'
import { useNavigate } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/components/ui/utils'

import type { Persona } from '@/lib/api/personas'

interface Props {
  persona: Persona | undefined
  allPersonas: Persona[]
  chat: React.ReactNode
  tools: React.ReactNode
  onSwitchPersona: (personaId: string) => void
}

export function PersonaWorkspaceLayout({
  persona,
  allPersonas,
  chat,
  tools,
  onSwitchPersona,
}: Props) {
  const navigate = useNavigate()

  if (!persona) {
    return (
      <div className="mx-auto max-w-3xl p-10 text-center text-sm text-muted-foreground">
        正在加载 persona……
      </div>
    )
  }

  const implemented = !!persona.is_implemented

  return (
    <div className="flex h-full flex-col">
      {/* 顶部 */}
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-border/40 bg-card/40 px-6 py-4">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="-ml-2 h-8 gap-1 text-muted-foreground"
            onClick={() => navigate('/agents')}
          >
            <icons.ArrowLeft className="size-4" />
            智能体
          </Button>
          <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-muted/60 text-2xl ring-1 ring-border/50">
            <span aria-hidden>{persona.emoji}</span>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1 className="truncate text-lg font-semibold tracking-tight text-foreground">
                {persona.display_name}
              </h1>
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
            <p className="mt-0.5 line-clamp-1 max-w-2xl text-sm text-muted-foreground">
              {persona.description}
            </p>
          </div>
        </div>

        {/* 切换 persona */}
        {allPersonas.length > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="gap-1">
                切换
                <icons.ChevronDown className="size-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-64">
              <DropdownMenuLabel>切换到其它 persona</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {allPersonas.map((p) => (
                <DropdownMenuItem
                  key={p.persona_id}
                  onClick={() => onSwitchPersona(p.persona_id)}
                  className={cn(
                    'gap-2',
                    p.persona_id === persona.persona_id && 'bg-muted',
                  )}
                >
                  <span className="text-base" aria-hidden>
                    {p.emoji}
                  </span>
                  <span className="flex-1 truncate">{p.display_name}</span>
                  {p.is_implemented ? (
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400">
                      实装
                    </span>
                  ) : (
                    <span className="text-[10px] text-amber-600 dark:text-amber-400">
                      规划
                    </span>
                  )}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </header>

      {/* 主体：左聊天 / 右工具 */}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-0 lg:grid-cols-[minmax(0,1fr)_380px]">
        <section className="min-w-0 border-r border-border/40">{chat}</section>
        <aside className="min-w-0 overflow-y-auto bg-muted/20">{tools}</aside>
      </div>
    </div>
  )
}
