/**
 * 管理中心 — 合并：合同管理 + 合规自检 + 风险预警
 * v4.0 使用 CenterLayout 统一布局
 */

import { CenterLayout, type CenterTab } from '@/components/ui/CenterLayout'
import { useTabUrlSync } from '@/hooks/useTabUrlSync'
// I2 (2026-05-14, ADR 003): tab 内容子组件迁出 pages/, 集中到 components/center-tabs/
import { Contracts, ComplianceCheck, RiskAlertPanel } from '@/components/center-tabs'

const tabs: CenterTab[] = [
  { id: 'contracts', label: '合同管理', icon: 'FileText' },
  { id: 'compliance', label: '合规管理', icon: 'ShieldCheck' },
  { id: 'risk-alert', label: '风险预警', icon: 'AlertTriangle' },
]

const VALID_TAB_IDS = tabs.map(t => t.id)

export default function ManagementCenter() {
  const { activeTab, handleTabChange } = useTabUrlSync(VALID_TAB_IDS, 'contracts')

  return (
    <CenterLayout title="管理中心" tabs={tabs} activeTab={activeTab} onTabChange={handleTabChange}>
      {activeTab === 'contracts' && <Contracts />}
      {activeTab === 'compliance' && <ComplianceCheck />}
      {activeTab === 'risk-alert' && <RiskAlertPanel />}
    </CenterLayout>
  )
}
