/**
 * PairingAuthorizationsPage.tsx — V3 配对授权（占位）
 */

import { Users } from 'lucide-react'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function PairingAuthorizationsPage() {
  return (
    <PlaceholderPage
      icon={Users}
      title="配对授权"
      description="授权他人或设备代你执行特定智能体任务，安全可追溯"
      plannedFeatures={[
        '生成配对码 / 二维码，绑定移动端、桌面端或团队成员',
        '细粒度授权范围：可使用的智能体、可访问的会话、可操作的工具',
        '有效期与单次使用限制，到期自动失效',
        '完整的授权审计日志：谁、何时、做了什么',
        '一键吊销与冻结，支持紧急停用',
      ]}
    />
  )
}
