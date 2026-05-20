/**
 * PluginsPage.tsx — V3 插件（占位）
 */

import { icons } from '@/lib/icons'
import { PlaceholderPage } from '@/components/v3/PlaceholderPage'

export default function PluginsPage() {
  return (
    <PlaceholderPage
      icon={icons.Puzzle}
      title="插件"
      description="通过插件接入外部系统与数据源，构建你的法务工作台"
      plannedFeatures={[
        '官方插件库：北大法宝 / Westlaw / 企查查 / 国家企业信用信息系统等',
        'MCP 协议接入，兼容主流模型与 Agent 生态',
        '插件可在对话中按需调用，并展示数据来源与引用链路',
        '私有插件：通过 OpenAPI / Webhook 快速接入企业内部系统',
        '审批与上架机制，保障插件来源可控',
      ]}
    />
  )
}
