/**
 * RiskTimeline - 风险时间轴
 *
 * 优先使用后端返回的 risk_events
 * 其次从 risk_points / recommendations 自动生成事件列表
 * 无数据时显示空状态
 */
import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, heading } from '@/lib/design-tokens'

interface RiskTimelineProps {
  data?: {
    overall_rating?: string
    risk_points?: string[]
    recommendations?: string[]
    operation_risk?: number
    litigation_risk?: number
    credit_risk?: number
    compliance_risk?: number
    relation_risk?: number
    risk_events?: Array<{
      date?: string
      level?: string
      title?: string
      description?: string
    }>
  }
}

interface TimelineEvent {
  id: number
  date: string
  level: 'high' | 'medium' | 'low'
  title: string
  description: string
}

/** 从风险数据派生时间轴事件 */
function deriveEvents(data?: RiskTimelineProps['data']): TimelineEvent[] {
  if (!data) return []

  if (data.risk_events && data.risk_events.length > 0) {
    return data.risk_events.map((e, i) => ({
      id: i + 1,
      date: e.date || '调查发现',
      level: (e.level || 'low') as TimelineEvent['level'],
      title: e.title || '风险事件',
      description: e.description || '',
    }))
  }

  const events: TimelineEvent[] = []
  let seq = 1

  const dims = [
    { key: 'operation_risk', label: '经营风险', score: data.operation_risk || 0 },
    { key: 'litigation_risk', label: '诉讼风险', score: data.litigation_risk || 0 },
    { key: 'credit_risk', label: '信用风险', score: data.credit_risk || 0 },
    { key: 'compliance_risk', label: '合规风险', score: data.compliance_risk || 0 },
    { key: 'relation_risk', label: '关联风险', score: data.relation_risk || 0 },
  ]

  dims
    .filter(d => d.score > 40)
    .sort((a, b) => b.score - a.score)
    .forEach(d => {
      events.push({
        id: seq++,
        date: '调查发现',
        level: d.score > 60 ? 'high' : 'medium',
        title: `${d.label}偏高`,
        description: `${d.label}评分 ${d.score}/100，${d.score > 60 ? '需重点关注' : '建议持续监控'}`,
      })
    })

  if (data.risk_points) {
    data.risk_points.forEach(p => {
      events.push({
        id: seq++,
        date: '风险排查',
        level: 'medium',
        title: p.length > 20 ? p.slice(0, 20) + '...' : p,
        description: p,
      })
    })
  }

  if (data.recommendations) {
    data.recommendations.slice(0, 3).forEach(r => {
      events.push({
        id: seq++,
        date: '建议措施',
        level: 'low',
        title: r.length > 20 ? r.slice(0, 20) + '...' : r,
        description: r,
      })
    })
  }

  return events
}

const levelConfig = {
  high: {
    icon: icons.AlertTriangle,
    bg: 'bg-red-50 dark:bg-red-950/30',
    border: 'border-red-200 dark:border-red-800',
    text: 'text-red-700 dark:text-red-300',
    dot: 'bg-red-500',
  },
  medium: {
    icon: icons.AlertCircle,
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    border: 'border-amber-200 dark:border-amber-800',
    text: 'text-amber-700 dark:text-amber-300',
    dot: 'bg-amber-500',
  },
  low: {
    icon: icons.Info,
    bg: 'bg-primary/5',
    border: 'border-primary/20',
    text: 'text-primary',
    dot: 'bg-primary',
  },
}

export function RiskTimeline({ data }: RiskTimelineProps) {
  const events = useMemo(() => deriveEvents(data), [data])

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: 0.1 }}
      className={cardStyle.base}
    >
      <div className="flex items-center gap-2 mb-6">
        <icons.Clock className="w-5 h-5 text-muted-foreground" />
        <div>
          <h3 className={heading.section}>风险时间轴</h3>
          <p className={heading.muted}>基于调查数据生成的风险事件</p>
        </div>
      </div>

      {events.length > 0 ? (
        <div className="relative">
          <div className="absolute left-2 top-0 bottom-0 w-0.5 bg-border" />

          <div className="space-y-4">
            {events.map((event, index) => {
              const config = levelConfig[event.level]
              const Icon = config.icon

              return (
                <motion.div
                  key={event.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.08 }}
                  className="relative pl-8"
                >
                  <div className={`absolute left-0 w-4 h-4 rounded-full ${config.dot} border-2 border-background`} />

                  <div className={`p-3 rounded-lg border ${config.bg} ${config.border}`}>
                    <div className="flex items-start gap-2 mb-1">
                      <Icon className={`w-4 h-4 ${config.text} flex-shrink-0 mt-0.5`} />
                      <div className="flex-1 min-w-0">
                        <h4 className={`font-medium text-sm ${config.text}`}>{event.title}</h4>
                        {event.description !== event.title && (
                          <p className="text-xs text-muted-foreground mt-0.5">{event.description}</p>
                        )}
                      </div>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{event.date}</p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <icons.Clock className="w-10 h-10 mb-3 opacity-20" />
          <p className="text-sm">暂无风险事件</p>
          <p className="text-xs opacity-60 mt-1">完成调查后将自动生成风险时间轴</p>
        </div>
      )}
    </motion.div>
  )
}
