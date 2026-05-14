/**
 * AgentBinder — 选择智能体下拉
 *
 * 10 个 V3 personas，从 docs/v3/AGENT_PERSONAS.md 提取并 hardcode 为常量。
 * 选择后立即调用 onChange（外部决定是否调用 store.bindAgent）。
 */

import { useState } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

export interface PersonaOption {
  value: string
  emoji: string
  label: string
  desc: string
}

export const V3_PERSONAS: PersonaOption[] = [
  { value: 'anxin_assistant', emoji: '🤖', label: '安心助理', desc: '通用入口 / 任务编排' },
  { value: 'legal_advisor', emoji: '⚖️', label: '法律顾问', desc: '法律咨询 + 检索' },
  { value: 'contract_steward', emoji: '📜', label: '合同管家', desc: '合同全生命周期' },
  { value: 'due_diligence', emoji: '🔍', label: '尽调专家', desc: '公司 / 项目 360° 尽调' },
  { value: 'tax_advisor', emoji: '💰', label: '财税顾问', desc: '税务 + 财务' },
  { value: 'workflow_steward', emoji: '📋', label: '流程管家', desc: 'OKR / 审批 / 会议 / 周报' },
  { value: 'market_researcher', emoji: '📊', label: '市场研究员', desc: '调研 / 竞品 / 趋势' },
  { value: 'sales_hunter', emoji: '🎯', label: '获客猎手', desc: '销售 / 推广 / Vibe Selling' },
  { value: 'content_director', emoji: '✍️', label: '内容总监', desc: '公众号 / 短视频 / 海报' },
  { value: 'cross_border', emoji: '🌍', label: '跨境电商助手', desc: '选品 / 独立站 / 出海全链路' },
]

export function getPersonaLabel(value: string | null | undefined): string {
  if (!value) return ''
  const p = V3_PERSONAS.find((x) => x.value === value)
  return p ? `${p.emoji} ${p.label}` : value
}

interface AgentBinderProps {
  value: string | null
  onChange: (persona: string) => Promise<void> | void
  /** 渠道未配置时禁用 */
  disabled?: boolean
}

export function AgentBinder({ value, onChange, disabled }: AgentBinderProps) {
  const [pending, setPending] = useState(false)

  const handleChange = async (next: string) => {
    if (next === value) return
    setPending(true)
    try {
      await onChange(next)
      toast.success(`已绑定 ${getPersonaLabel(next)}`)
    } catch (e) {
      toast.error(`绑定失败: ${e instanceof Error ? e.message : '未知错误'}`)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-xs font-medium text-foreground">智能体</label>
        {pending && <icons.Loader2 className="size-3 animate-spin text-muted-foreground" />}
      </div>
      <Select value={value ?? undefined} onValueChange={handleChange} disabled={disabled || pending}>
        <SelectTrigger className="h-9 w-full">
          <SelectValue placeholder="选择一个智能体来处理此渠道的消息" />
        </SelectTrigger>
        <SelectContent>
          {V3_PERSONAS.map((p) => (
            <SelectItem key={p.value} value={p.value}>
              <div className="flex flex-col items-start text-left">
                <span className="text-sm">
                  {p.emoji} {p.label}
                </span>
                <span className="text-[10px] text-muted-foreground">{p.desc}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
