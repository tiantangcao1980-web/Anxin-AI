/**
 * 案件中心 — 合并：案件管理 + 案源管理 + 任务与审批
 * v4.0 使用 CenterLayout 统一布局
 */

import { CenterLayout, type CenterTab } from '@/components/ui/CenterLayout'
import { useTabUrlSync } from '@/hooks/useTabUrlSync'
// I2 (2026-05-14, ADR 003): tab 内容子组件迁出 pages/, 集中到 components/center-tabs/
import { CaseManagement as Cases } from '@/components/case-management/CaseManagement'
import { Leads, Tasks } from '@/components/center-tabs'

const tabs: CenterTab[] = [
  { id: 'cases', label: '我的案件', icon: 'Briefcase' },
  { id: 'leads', label: '案源线索', icon: 'Users' },
  { id: 'tasks', label: '任务与审批', icon: 'CheckCheck' },
]

const VALID_TAB_IDS = tabs.map(t => t.id)

export default function CaseCenter() {
  const { activeTab, handleTabChange } = useTabUrlSync(VALID_TAB_IDS, 'cases')

  return (
    <CenterLayout title="案件中心" tabs={tabs} activeTab={activeTab} onTabChange={handleTabChange}>
      {activeTab === 'cases' && <Cases />}
      {activeTab === 'leads' && <Leads />}
      {activeTab === 'tasks' && <Tasks />}
    </CenterLayout>
  )
}
