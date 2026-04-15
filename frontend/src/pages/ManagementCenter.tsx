/**
 * 管理中心 — 合并：合同管理 + 合规自检 + 风险预警
 * v4.0 使用 CenterLayout 统一布局
 */

import { useState } from 'react'
import { CenterLayout, type CenterTab } from '@/components/ui/CenterLayout'
import Contracts from '@/pages/Contracts'
import ComplianceCheck from '@/pages/ComplianceCheck'
import { RiskAlertPanel } from '@/pages/RiskAlertPanel'

const tabs: CenterTab[] = [
  { id: 'contracts', label: '合同管理', icon: 'FileText' },
  { id: 'compliance', label: '合规管理', icon: 'ShieldCheck' },
  { id: 'risk-alert', label: '风险预警', icon: 'AlertTriangle' },
]

export default function ManagementCenter() {
  const [activeTab, setActiveTab] = useState('contracts')

  return (
    <CenterLayout title="管理中心" tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'contracts' && <Contracts />}
      {activeTab === 'compliance' && <ComplianceCheck />}
      {activeTab === 'risk-alert' && <RiskAlertPanel />}
    </CenterLayout>
  )
}
