/**
 * CenterLayout — 统一的「中心」页面布局模板
 *
 * 用于 CaseCenter、ManagementCenter 等「顶部标题 + Tab 切换 + 全高内容」模式的页面。
 * 所有中心页面必须使用此组件，确保：
 * 1. 标题只出现一次（heading.section 级别）
 * 2. Tab 样式完全统一
 * 3. 内容区 flex-1 + overflow-hidden，子页面自行管理滚动
 *
 * 用法：
 *   <CenterLayout title="案件中心" tabs={tabs} activeTab={tab} onTabChange={setTab}>
 *     {tab === 'cases' && <Cases />}
 *     {tab === 'leads' && <Leads />}
 *   </CenterLayout>
 */

import { type ReactNode } from 'react'
import { heading, spacing } from '@/lib/design-tokens'
import { icons, type IconName } from '@/lib/icons'

export interface CenterTab {
  id: string
  label: string
  icon: IconName
}

interface CenterLayoutProps {
  /** 页面标题 */
  title: string
  /** Tab 定义 */
  tabs: CenterTab[]
  /** 当前激活的 Tab id */
  activeTab: string
  /** Tab 切换回调 */
  onTabChange: (tabId: string) => void
  /** 右侧操作区 */
  actions?: ReactNode
  /** 内容区（根据 activeTab 条件渲染） */
  children: ReactNode
}

export function CenterLayout({
  title,
  tabs,
  activeTab,
  onTabChange,
  actions,
  children,
}: CenterLayoutProps) {
  return (
    <div className="h-full flex flex-col">
      {/* Sticky Header */}
      <div className="shrink-0 border-b border-border bg-background/95 backdrop-blur-sm px-4 sm:px-5 lg:px-6 pt-4 pb-3">
        {/* 标题行 */}
        <div className="flex items-center justify-between mb-3">
          <h1 className={heading.page}>{title}</h1>
          {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
        </div>

        {/* Tab 切换 */}
        <div className="flex gap-1 bg-muted/50 rounded-xl p-1 w-fit">
          {tabs.map(tab => {
            const Icon = icons[tab.icon]
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary/20 ${
                  isActive
                    ? 'bg-background text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}
