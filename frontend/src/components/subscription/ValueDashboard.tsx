/**
 * ValueDashboard — 订阅价值感可视化组件 (V2 架构)
 *
 * 展示用户本月通过 AI 法务节省的时间和费用，提升续费率。
 * 嵌入到首页或设置页中。
 */

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { Card, CardContent } from '@/components/ui/card'
import { useAuthStore } from '@/lib/store'

interface ValueMetric {
  label: string
  value: string
  subtitle: string
  icon: keyof typeof icons
  color: string
}

export function ValueDashboard() {
  const { user } = useAuthStore()
  const [metrics, setMetrics] = useState<ValueMetric[]>([])

  useEffect(() => {
    // 模拟数据（实际从 API 获取）
    // TODO: 接入真实统计 API
    setMetrics([
      {
        label: '本月 AI 对话',
        value: '47 次',
        subtitle: '相当于 23.5 小时律师咨询',
        icon: 'MessageCircle',
        color: 'text-primary',
      },
      {
        label: '文书生成',
        value: '12 份',
        subtitle: '预估节省 ¥18,000 律师费',
        icon: 'FileText',
        color: 'text-success',
      },
      {
        label: '合同审查',
        value: '8 份',
        subtitle: '发现 23 处风险条款',
        icon: 'Shield',
        color: 'text-warning',
      },
      {
        label: '累计节省',
        value: '¥32,400',
        subtitle: '订阅费仅 ¥99/月，投资回报率 327 倍',
        icon: 'TrendingUp',
        color: 'text-success',
      },
    ])
  }, [user?.id])

  if (metrics.length === 0) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <icons.BarChart3 className="w-5 h-5 text-primary" />
        <h3 className="text-base font-semibold text-foreground">本月使用价值</h3>
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {metrics.map((metric, i) => {
          const IconComp = icons[metric.icon] || icons.Star
          return (
            <motion.div
              key={metric.label}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <Card className="h-full">
                <CardContent className="p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <IconComp className={`w-4 h-4 ${metric.color}`} />
                    <span className="text-xs text-muted-foreground">{metric.label}</span>
                  </div>
                  <div className={`text-xl font-bold ${metric.color}`}>{metric.value}</div>
                  <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">
                    {metric.subtitle}
                  </p>
                </CardContent>
              </Card>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
