/**
 * 案件中心 — 合并：案件管理 + 案源管理 + 任务与审批
 * v3.0 导航重构
 */

import { useState } from 'react'
import { Briefcase, Users, CheckSquare } from 'lucide-react'
import Cases from '@/pages/Cases'
import Leads from '@/pages/Leads'
import Tasks from '@/pages/Tasks'

const tabs = [
  { id: 'cases', label: '我的案件', icon: Briefcase },
  { id: 'leads', label: '案源线索', icon: Users },
  { id: 'tasks', label: '任务与审批', icon: CheckSquare },
] as const

export default function CaseCenter() {
  const [activeTab, setActiveTab] = useState<string>('cases')

  return (
    <div className="h-full flex flex-col">
      <div className="border-b bg-background/95 backdrop-blur px-6 pt-4 pb-0">
        <h1 className="text-xl font-medium mb-3">案件中心</h1>
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
        {activeTab === 'cases' && <Cases />}
        {activeTab === 'leads' && <Leads />}
        {activeTab === 'tasks' && <Tasks />}
      </div>
    </div>
  )
}
