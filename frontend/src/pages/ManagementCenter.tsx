/**
 * 管理中心 — 合并：合同管理 + 合规自检 + 风险预警
 * v3.0 导航重构
 */

import { useState } from 'react'
import { FileText, ShieldCheck, AlertTriangle } from 'lucide-react'
import Contracts from '@/pages/Contracts'
import ComplianceCheck from '@/pages/ComplianceCheck'
import { RiskAlertPanel } from '@/pages/RiskAlertPanel'

const tabs = [
  { id: 'contracts', label: '合同管理', icon: FileText },
  { id: 'compliance', label: '合规管理', icon: ShieldCheck },
  { id: 'risk-alert', label: '风险预警', icon: AlertTriangle },
] as const

export default function ManagementCenter() {
  const [activeTab, setActiveTab] = useState<string>('contracts')

  return (
    <div className="h-full flex flex-col">
      <div className="border-b bg-background/95 backdrop-blur px-6 pt-4 pb-0">
        <h1 className="text-xl font-medium mb-3">管理中心</h1>
        <div className="flex gap-1 bg-muted/50 rounded-lg p-1 w-fit">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'contracts' && <Contracts />}
        {activeTab === 'compliance' && <ComplianceCheck />}
        {activeTab === 'risk-alert' && <RiskAlertPanel />}
      </div>
    </div>
  )
}
