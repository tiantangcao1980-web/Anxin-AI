/**
 * MessageChannelsPage.tsx — V3 消息渠道（占位）
 */

import { MessageCircle } from 'lucide-react'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function MessageChannelsPage() {
  return (
    <PlaceholderPage
      icon={MessageCircle}
      title="消息渠道"
      description="统一管理通知触达渠道，让重要事项不再错过"
      plannedFeatures={[
        '多渠道接入：站内消息、企业微信、钉钉、飞书、邮件、短信',
        '按事件类型订阅：任务到期、合同审签、舆情预警、案件进展',
        '勿扰时段与频率控制，避免推送疲劳',
        '渠道送达回执与失败重投，关键消息不丢失',
        '团队广播：管理员可向指定群组下发公告或合规提醒',
      ]}
    />
  )
}
