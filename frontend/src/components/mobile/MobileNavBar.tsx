/**
 * MobileNavBar - 移动端底部导航栏
 *
 * 固定 5 个核心入口：AI 智能助手、案件、消息、智库、设置
 * 适配 iOS 安全区域
 */

import { useLocation, useNavigate } from 'react-router-dom'
import {
  ChatBubbleLeftRightIcon,
  BriefcaseIcon,
  ChatBubbleOvalLeftEllipsisIcon,
  BookOpenIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import {
  ChatBubbleLeftRightIcon as ChatSolid,
  BriefcaseIcon as BriefcaseSolid,
  ChatBubbleOvalLeftEllipsisIcon as MessageSolid,
  BookOpenIcon as BookSolid,
  Cog6ToothIcon as CogSolid,
} from '@heroicons/react/24/solid'

interface NavItem {
  path: string
  label: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  activeIcon: React.ComponentType<React.SVGProps<SVGSVGElement>>
  matchPaths?: string[]
}

const NAV_ITEMS: NavItem[] = [
  {
    path: '/chat',
    label: 'AI 智能助手',
    icon: ChatBubbleLeftRightIcon,
    activeIcon: ChatSolid,
  },
  {
    path: '/cases',
    label: '协作',
    icon: BriefcaseIcon,
    activeIcon: BriefcaseSolid,
    matchPaths: ['/cases', '/case-center', '/contracts', '/collaboration', '/agent-approvals', '/find-lawyer'],
  },
  {
    path: '/messages',
    label: '消息',
    icon: ChatBubbleOvalLeftEllipsisIcon,
    activeIcon: MessageSolid,
  },
  {
    path: '/knowledge-base',
    label: '智库',
    icon: BookOpenIcon,
    activeIcon: BookSolid,
    matchPaths: ['/knowledge-base', '/knowledge-graph', '/due-diligence'],
  },
  {
    path: '/settings',
    label: '我的',
    icon: Cog6ToothIcon,
    activeIcon: CogSolid,
    matchPaths: ['/settings', '/pricing', '/my-subscription'],
  },
]

export function MobileNavBar() {
  const location = useLocation()
  const navigate = useNavigate()

  const isActive = (item: NavItem) => {
    const paths = item.matchPaths || [item.path]
    return paths.some((p) => location.pathname.startsWith(p))
  }

  return (
    <nav
      className="flex items-center justify-around border-t border-border/50 bg-background/95 backdrop-blur-sm"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      {NAV_ITEMS.map((item) => {
        const active = isActive(item)
        const Icon = active ? item.activeIcon : item.icon

        return (
          <button
            key={item.path}
            onClick={() => navigate(item.path)}
            className={`flex flex-col items-center justify-center py-2 px-3 min-w-[64px] transition-colors ${
              active ? 'text-primary' : 'text-muted-foreground'
            }`}
          >
            <Icon className="w-6 h-6" />
            <span className={`text-[10px] mt-0.5 ${active ? 'font-semibold' : 'font-medium'}`}>
              {item.label}
            </span>
          </button>
        )
      })}
    </nav>
  )
}
