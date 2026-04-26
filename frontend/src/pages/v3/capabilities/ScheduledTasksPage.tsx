/**
 * ScheduledTasksPage.tsx — V3 定时任务（占位）
 */

import { Clock } from 'lucide-react'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function ScheduledTasksPage() {
  return (
    <PlaceholderPage
      icon={Clock}
      title="定时任务"
      description="按周期或时间点自动触发智能体任务，把重复工作交给安心"
      plannedFeatures={[
        '可视化 Cron 编排：每日 / 每周 / 每月 / 自定义时间触发',
        '常用模板：合同到期提醒、案件状态日报、舆情周报、月度合规巡检',
        '任务执行历史与结果归档，可一键复用上次输出',
        '失败重试与企业微信 / 短信 / 邮件多渠道告警',
        '与「任务中心」打通，自动派发后续待办',
      ]}
    />
  )
}
