/**
 * AppAuthorizationsPage.tsx — V3 应用授权（占位）
 */

import { KeyRound } from 'lucide-react'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function AppAuthorizationsPage() {
  return (
    <PlaceholderPage
      icon={KeyRound}
      title="应用授权"
      description="集中管理安心智能助手对第三方应用的访问授权"
      plannedFeatures={[
        '一键授权：钉钉 / 飞书 / 企业微信 / 邮箱 / 网盘等常用办公应用',
        '细粒度权限选择，明确告知每项授权读取或写入的数据范围',
        '授权状态总览：哪些应用已连接、最近一次同步时间、令牌有效期',
        '撤销与重新授权流程清晰，符合数据合规要求',
        '团队级 OAuth 应用管理，支持组织管理员统一审批',
      ]}
    />
  )
}
