/**
 * SkillDetailDrawer — 右侧技能详情抽屉
 *
 * 展示完整 body markdown + triggers + dependencies + requires_apps + 试运行入口
 *
 * Markdown 渲染策略：动态 import react-markdown 以避免初次包体膨胀；
 * 模块加载失败时降级到 <pre>。
 */

import { lazy, Suspense, useState } from 'react'
import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/components/ui/utils'

import type { Skill, SkillCategory } from '@/lib/api/skills'

import {
  CATEGORY_BADGE_CLASS,
  CATEGORY_LABEL,
  TYPE_LABEL,
} from './skillsTaxonomy'

const ReactMarkdown = lazy(() => import('react-markdown'))

interface SkillDetailDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  skill: Skill | null
  loading: boolean
  onToggle: (next: boolean) => void
  onExecute: () => void
}

function Section({
  title,
  children,
  hidden,
}: {
  title: string
  children: React.ReactNode
  hidden?: boolean
}) {
  if (hidden) return null
  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </h3>
      <div>{children}</div>
    </div>
  )
}

export function SkillDetailDrawer({
  open,
  onOpenChange,
  skill,
  loading,
  onToggle,
  onExecute,
}: SkillDetailDrawerProps) {
  const [mdError, setMdError] = useState(false)
  const categoryLabel =
    (skill && CATEGORY_LABEL[skill.category as SkillCategory]) ?? skill?.category
  const badgeClass = skill
    ? CATEGORY_BADGE_CLASS[skill.category as SkillCategory] ??
      'bg-muted text-muted-foreground'
    : ''

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col gap-0 overflow-hidden p-0 sm:max-w-xl"
      >
        {loading || !skill ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            <icons.Loader2 className="mr-2 size-4 animate-spin" />
            加载中...
          </div>
        ) : (
          <>
            <SheetHeader className="space-y-2 border-b border-border/60 p-5">
              <div className="flex items-start gap-3">
                <div className="flex size-12 shrink-0 items-center justify-center rounded-2xl bg-muted text-2xl ring-1 ring-border/50">
                  <span aria-hidden>{skill.icon ?? '✨'}</span>
                </div>
                <div className="min-w-0 flex-1">
                  <SheetTitle className="truncate text-base">
                    {skill.display_name}
                  </SheetTitle>
                  <SheetDescription className="mt-0.5 font-mono text-[11px]">
                    {skill.name} · v{skill.version}
                  </SheetDescription>
                  <div className="mt-2 flex flex-wrap items-center gap-1">
                    <Badge variant="outline" className={cn('text-[10px]', badgeClass)}>
                      {categoryLabel}
                    </Badge>
                    <Badge variant="outline" className="text-[10px]">
                      {TYPE_LABEL[skill.type] ?? skill.type}
                    </Badge>
                    <Badge variant="outline" className="text-[10px]">
                      by {skill.author}
                    </Badge>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <Switch
                    checked={skill.enabled}
                    onCheckedChange={onToggle}
                    aria-label={skill.enabled ? '禁用技能' : '启用技能'}
                    className="data-[state=checked]:bg-emerald-500"
                  />
                  <span className="text-[10px] text-muted-foreground">
                    {skill.enabled ? '已启用' : '未启用'}
                  </span>
                </div>
              </div>
              <p className="text-sm text-foreground/80">{skill.description}</p>
            </SheetHeader>

            <div className="flex-1 space-y-5 overflow-y-auto p-5">
              <Section title="触发词" hidden={skill.triggers.length === 0}>
                <ul className="flex flex-wrap gap-1.5">
                  {skill.triggers.map((t) => (
                    <li
                      key={t}
                      className="rounded-md bg-muted px-2 py-0.5 font-mono text-[11px] text-foreground/80"
                    >
                      {t}
                    </li>
                  ))}
                </ul>
              </Section>

              <Section title="适配角色" hidden={skill.personas.length === 0}>
                <div className="flex flex-wrap gap-1.5">
                  {skill.personas.map((p) => (
                    <Badge key={p} variant="secondary" className="text-[10px]">
                      {p}
                    </Badge>
                  ))}
                </div>
              </Section>

              <Section title="所需授权" hidden={skill.requires_apps.length === 0}>
                <div className="flex flex-wrap gap-1.5">
                  {skill.requires_apps.map((a) => (
                    <Badge
                      key={a}
                      variant="outline"
                      className="border-amber-300 bg-amber-50 text-[10px] text-amber-700 dark:bg-amber-500/10 dark:text-amber-300"
                    >
                      {a}
                    </Badge>
                  ))}
                </div>
              </Section>

              <Section title="技能依赖" hidden={skill.dependencies.length === 0}>
                <ul className="flex flex-col gap-1">
                  {skill.dependencies.map((d) => (
                    <li
                      key={d}
                      className="rounded-md bg-muted/40 px-2 py-1 font-mono text-[11px] text-foreground/70"
                    >
                      {d}
                    </li>
                  ))}
                </ul>
              </Section>

              <Section title="关键词" hidden={skill.keywords.length === 0}>
                <div className="flex flex-wrap gap-1.5">
                  {skill.keywords.map((k) => (
                    <Badge key={k} variant="outline" className="text-[10px]">
                      {k}
                    </Badge>
                  ))}
                </div>
              </Section>

              <Section title="详细说明">
                {skill.body ? (
                  mdError ? (
                    <pre className="max-h-96 overflow-auto rounded-md bg-muted/40 p-3 font-mono text-[11px] leading-relaxed">
                      {skill.body}
                    </pre>
                  ) : (
                    <div className="prose prose-sm prose-zinc max-w-none dark:prose-invert">
                      <Suspense
                        fallback={
                          <div className="text-xs text-muted-foreground">
                            正在加载渲染器...
                          </div>
                        }
                      >
                        <MarkdownBody
                          body={skill.body}
                          onError={() => setMdError(true)}
                        />
                      </Suspense>
                    </div>
                  )
                ) : skill.body_excerpt ? (
                  <p className="text-sm text-muted-foreground">{skill.body_excerpt}</p>
                ) : (
                  <p className="text-sm text-muted-foreground">（无说明）</p>
                )}
              </Section>
            </div>

            <div className="flex items-center justify-between gap-2 border-t border-border/60 bg-muted/30 p-4">
              <div className="text-xs text-muted-foreground">
                {skill.enabled ? '已启用 · 可在对话中触发' : '未启用 · 触发将被忽略'}
              </div>
              <Button onClick={onExecute} size="sm" variant="default">
                <icons.PlayCircle className="size-4" />
                试运行
              </Button>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

function MarkdownBody({ body, onError }: { body: string; onError: () => void }) {
  try {
    return <ReactMarkdown>{body}</ReactMarkdown>
  } catch {
    onError()
    return null
  }
}
