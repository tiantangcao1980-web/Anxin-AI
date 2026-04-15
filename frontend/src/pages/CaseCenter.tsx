/**
 * 案件中心 — 合并：案件管理 + 案源管理 + 任务与审批
 * v4.0 使用 CenterLayout 统一布局
 */

import { useState } from 'react'
import { CenterLayout, type CenterTab } from '@/components/ui/CenterLayout'
import Cases from '@/pages/Cases'
import Leads from '@/pages/Leads'
import Tasks from '@/pages/Tasks'

const tabs: CenterTab[] = [
  { id: 'cases', label: '我的案件', icon: 'Briefcase' },
  { id: 'leads', label: '案源线索', icon: 'Users' },
  { id: 'tasks', label: '任务与审批', icon: 'CheckCheck' },
]

export default function CaseCenter() {
  const [activeTab, setActiveTab] = useState('cases')

  return (
    <CenterLayout title="案件中心" tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === 'cases' && <Cases />}
      {activeTab === 'leads' && <Leads />}
      {activeTab === 'tasks' && <Tasks />}
    </CenterLayout>
  )
}
