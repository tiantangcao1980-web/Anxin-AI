/**
 * PlaceholderPage.tsx — V3 占位页通用模板
 *
 * 用途：为 V3 IA 中尚未实现的页面（智能体/能力/任务等）提供统一的占位 UI。
 * 设计原则：复用现有 Card / Button / design-tokens，不引入新设计语言。
 */

import { useNavigate } from 'react-router-dom'
import { ArrowRight, Sparkles, type LucideIcon } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { spacing, heading } from '@/lib/design-tokens'

export interface PlaceholderPageProps {
  /** 页面标题 */
  title: string
  /** 副标题 / 一句话说明 */
  description: string
  /** 即将推出的功能 bullet 列表（建议 3-5 条） */
  plannedFeatures: string[]
  /** 可选的页面图标（来自 lucide-react） */
  icon?: LucideIcon
  /** 是否标记为 Beta */
  beta?: boolean
}

export function PlaceholderPage({
  title,
  description,
  plannedFeatures,
  icon: Icon = Sparkles,
  beta = false,
}: PlaceholderPageProps) {
  const navigate = useNavigate()

  return (
    <div className={`mx-auto w-full max-w-3xl ${spacing.page}`}>
      {/* ===== 页面头 ===== */}
      <div className="mb-8 flex items-start gap-4">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Icon className="h-6 w-6" />
        </div>
        <div className="flex-1">
          <div className="mb-1 flex items-center gap-2">
            <h1 className={heading.page}>{title}</h1>
            {beta && (
              <Badge variant="secondary" className="rounded-full px-2 py-0 text-[10px] font-medium uppercase tracking-wide">
                Beta
              </Badge>
            )}
          </div>
          <p className="text-base text-muted-foreground">{description}</p>
        </div>
      </div>

      {/* ===== 即将推出 ===== */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-lg">即将推出</CardTitle>
          <CardDescription>该模块正在开发中，规划的核心能力如下</CardDescription>
        </CardHeader>
        <CardContent>
          <ul className="space-y-3">
            {plannedFeatures.map((feature) => (
              <li key={feature} className="flex items-start gap-3">
                <span
                  aria-hidden
                  className="mt-2 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                />
                <span className="text-sm leading-relaxed text-foreground/90">{feature}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* ===== 回到聊天 CTA ===== */}
      <div className="flex items-center justify-between rounded-2xl border border-border/40 bg-surface-1 p-5 shadow-card">
        <div>
          <p className="text-sm font-medium text-foreground">想先体验现有能力？</p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            回到智能对话，了解安心智能助手当前已支持的功能。
          </p>
        </div>
        <Button onClick={() => navigate('/chat')} iconRight={<ArrowRight className="h-4 w-4" />}>
          回到聊天
        </Button>
      </div>
    </div>
  )
}

export default PlaceholderPage
