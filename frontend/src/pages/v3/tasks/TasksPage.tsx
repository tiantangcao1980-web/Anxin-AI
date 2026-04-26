/**
 * TasksPage.tsx — V3 任务中心（占位）
 *
 * 注：与现有 /tasks 重定向冲突，将挂载在 /v3/tasks 路径下，避免破坏旧路由。
 */

import { Rocket } from 'lucide-react'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function TasksPage() {
  return (
    <PlaceholderPage
      icon={Rocket}
      title="任务中心"
      description="集中追踪智能体执行的长任务、定时任务与人机协同工单"
      plannedFeatures={[
        '统一任务列表：进行中 / 已完成 / 失败 / 已取消，状态实时刷新',
        '长任务可后台执行，结果通过消息渠道回推',
        '人工接管：对低置信度结果转交相关同事或律师审核',
        '任务模板与一键复跑，沉淀最佳实践',
        '团队视图：负责人、SLA、超期预警、绩效统计',
      ]}
      beta
    />
  )
}
