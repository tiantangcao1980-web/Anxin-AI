/**
 * AgentsPage.tsx — V3 智能体中心（占位）
 */

import { Bot } from 'lucide-react'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function AgentsPage() {
  return (
    <PlaceholderPage
      icon={Bot}
      title="智能体"
      description="按场景调用专属智能体，让安心更懂你的业务"
      plannedFeatures={[
        '内置法务智能体集合：合同审查、合规自检、案件分析、尽调助手等',
        '一键调用与对话上下文继承，避免重复粘贴背景信息',
        '自定义智能体：上传 Prompt / 指令集 / 知识包，快速搭建专属角色',
        '团队共享：将常用智能体推送给同事或律所成员',
        '使用洞察：调用次数、成功率、平均处理时长等运营指标',
      ]}
    />
  )
}
