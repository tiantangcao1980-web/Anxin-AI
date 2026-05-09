import { PageContainer } from '@/components/ui/PageContainer'
import { Badge } from '@/components/ui/badge'
import { LlmSettingsPanel } from '@/pages/Settings'

export default function AdminAIConfig() {
  return (
    <PageContainer title="模型治理" description="组织级模型供应商、默认配置、密钥遮罩与联调状态">
      <div className="mb-4 flex items-center justify-end">
        <Badge variant="outline" className="text-xs">组织级 · 已遮罩</Badge>
      </div>
      <LlmSettingsPanel />
    </PageContainer>
  )
}
