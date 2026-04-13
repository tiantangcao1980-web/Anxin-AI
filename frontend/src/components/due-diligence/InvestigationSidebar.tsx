/**
 * InvestigationSidebar - 智能调查仪表板左侧导航
 */
import { icons } from'@/lib/icons'
import { cn } from'@/lib/utils'

export type InvestigationSection =
 |'overview'
 |'risk'
 |'litigation'
 |'compliance'
 |'graph'
 |'sentiment'
 |'simulation'
 |'report'

interface NavItem {
 id: InvestigationSection
 label: string
 icon: any
 badge?: string | number
 badgeType?:'error' |'warning' |'info'
}

interface InvestigationSidebarProps {
 activeSection: InvestigationSection
 onSectionChange: (section: InvestigationSection) => void
 riskLevel?: string
 litigationCount?: number
 alertCount?: number
 hasReport?: boolean
 collapsed?: boolean
}

const NAV_ITEMS: NavItem[] = [
 { id:'overview', label:'调查概览', icon: icons.BarChart3 },
 { id:'risk', label:'风险评估', icon: icons.ShieldAlert },
 { id:'litigation', label:'诉讼分析', icon: icons.Scale },
 { id:'compliance', label:'信用合规', icon: icons.FileCheck },
 { id:'graph', label:'关系图谱', icon: icons.Network },
 { id:'sentiment', label:'舆情监控', icon: icons.Signal },
 { id:'simulation', label:'风险推演', icon: icons.Cpu },
 { id:'report', label:'调查报告', icon: icons.FileText },
]

export function InvestigationSidebar({
 activeSection,
 onSectionChange,
 riskLevel,
 litigationCount,
 alertCount,
 collapsed = false,
}: InvestigationSidebarProps) {
 const getBadge = (id: InvestigationSection): NavItem['badge'] | undefined => {
 switch (id) {
 case'risk':
 return riskLevel ==='high' ?'高' : riskLevel ==='medium' ?'中' : undefined
 case'litigation':
 return litigationCount && litigationCount > 0 ? litigationCount : undefined
 case'sentiment':
 return alertCount && alertCount > 0 ? alertCount : undefined
 default:
 return undefined
 }
 }

 const getBadgeType = (id: InvestigationSection): NavItem['badgeType'] => {
 switch (id) {
 case'risk':
 return riskLevel ==='high' ?'error' :'warning'
 case'litigation':
 return'warning'
 case'sentiment':
 return'error'
 default:
 return'info'
 }
 }

 const badgeColors = {
 error:'bg-destructive text-white',
 warning:'bg-warning text-white',
 info:'bg-primary text-white',
 }

 return (
 <nav className={cn(
'flex flex-col gap-1 py-2',
 collapsed ?'items-center' :''
 )}>
 {NAV_ITEMS.map((item) => {
 const Icon = item.icon
 const isActive = activeSection === item.id
 const badge = getBadge(item.id)
 const badgeType = getBadgeType(item.id)

 return (
 <button
 key={item.id}
 onClick={() => onSectionChange(item.id)}
 className={cn(
'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all relative group',
 isActive
 ?'bg-primary/10 text-primary'
 :'text-muted-foreground hover:bg-muted hover:text-foreground',
 collapsed ?'justify-center px-2' :''
 )}
 title={collapsed ? item.label : undefined}
 >
 <Icon className={cn(
'w-[18px] h-[18px] shrink-0',
 isActive ?'text-primary' :''
 )} />
 {!collapsed && (
 <>
 <span className="flex-1 text-left">{item.label}</span>
 {badge !== undefined && (
 <span className={cn(
'text-[10px] font-bold min-w-[18px] h-[18px] flex items-center justify-center rounded-full px-1',
 badgeColors[badgeType ||'info']
 )}>
 {badge}
 </span>
 )}
 </>
 )}
 {collapsed && badge !== undefined && (
 <span className={cn(
'absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full',
 badgeType ==='error' ?'bg-destructive' : badgeType ==='warning' ?'bg-warning' :'bg-primary'
 )} />
 )}
 </button>
 )
 })}
 </nav>
 )
}
