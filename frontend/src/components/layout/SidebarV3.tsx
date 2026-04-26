/**
 * SidebarV3.tsx — V3 全局侧边栏（Accio Work / Claude Code 桌面风格）
 *
 * 通过环境变量 VITE_V3_NAV=true 启用，默认关闭，旧 Layout/侧边栏不动。
 *
 * IA 结构：
 *   [Logo: 安心智能助手]
 *   + 新对话           → /chat
 *   ◆ 智能体           → /agents
 *   🛠 能力 (折叠)
 *     ⏰ 定时任务       → /capabilities/scheduled-tasks
 *     🔌 应用授权       → /capabilities/app-authorizations
 *     ✨ 技能           → /capabilities/skills
 *     📦 插件           → /capabilities/plugins
 *     💬 消息渠道       → /capabilities/message-channels
 *     👥 配对授权       → /capabilities/pairing-authorizations
 *   🚀 任务中心 [Beta] → /v3/tasks
 *   📚 知识库          → /knowledge-base
 *   ────────
 *   会话（列表占位）
 *   ────────
 *   + 团队 [Beta]
 *   [user 头像 + 升级]
 */

import { useState, useMemo, type ComponentType } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  Plus,
  Bot,
  Wrench,
  Clock,
  KeyRound,
  Sparkles,
  Puzzle,
  MessageCircle,
  Users,
  Rocket,
  BookOpen,
  ChevronDown,
  ChevronRight,
  Scale,
  UserPlus,
  ArrowUpRight,
  type LucideIcon,
} from 'lucide-react'
import { sidebarNav } from '@/lib/design-tokens'

interface NavItem {
  label: string
  path: string
  icon: LucideIcon
  beta?: boolean
}

const TOP_ITEMS: NavItem[] = [
  { label: '新对话', path: '/chat', icon: Plus },
  { label: '智能体', path: '/agents', icon: Bot },
]

const CAPABILITY_ITEMS: NavItem[] = [
  { label: '定时任务', path: '/capabilities/scheduled-tasks', icon: Clock },
  { label: '应用授权', path: '/capabilities/app-authorizations', icon: KeyRound },
  { label: '技能', path: '/capabilities/skills', icon: Sparkles },
  { label: '插件', path: '/capabilities/plugins', icon: Puzzle },
  { label: '消息渠道', path: '/capabilities/message-channels', icon: MessageCircle },
  { label: '配对授权', path: '/capabilities/pairing-authorizations', icon: Users },
]

const BOTTOM_ITEMS: NavItem[] = [
  { label: '任务中心', path: '/v3/tasks', icon: Rocket, beta: true },
  { label: '知识库', path: '/knowledge-base', icon: BookOpen },
]

function isActive(currentPath: string, target: string): boolean {
  return currentPath === target || currentPath.startsWith(target + '/')
}

function NavRow({
  item,
  current,
  onClick,
  indent = false,
}: {
  item: NavItem
  current: string
  onClick: (path: string) => void
  indent?: boolean
}) {
  const Icon: ComponentType<{ className?: string }> = item.icon
  const active = isActive(current, item.path)
  return (
    <button
      type="button"
      onClick={() => onClick(item.path)}
      className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 ${sidebarNav.itemText} transition-colors ${
        active ? sidebarNav.itemActive : sidebarNav.itemDefault
      } ${indent ? 'pl-8' : ''}`}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="flex-1 truncate text-left">{item.label}</span>
      {item.beta && (
        <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary">
          Beta
        </span>
      )}
    </button>
  )
}

export interface SidebarV3Props {
  /** 可选：会话列表（V3 后续接入 useChatStore） */
  conversations?: Array<{ id: string; title: string }>
  /** 顶部 Logo 文案 */
  brand?: string
}

export function SidebarV3({ conversations = [], brand = '安心智能助手' }: SidebarV3Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const currentPath = location.pathname

  // 「能力」分组默认展开；如当前路径在 capabilities 内强制展开
  const inCapabilities = currentPath.startsWith('/capabilities/')
  const [capExpanded, setCapExpanded] = useState<boolean>(true)
  const showCapabilities = capExpanded || inCapabilities

  const handleNav = (path: string) => navigate(path)

  const sessionList = useMemo(() => conversations.slice(0, 30), [conversations])

  return (
    <aside className="hidden h-full w-[260px] shrink-0 flex-col border-r border-border/60 bg-surface-1 lg:flex">
      {/* Brand */}
      <div className="flex h-14 items-center gap-2.5 border-b border-border/40 px-4">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
          <Scale className="h-4 w-4" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-foreground">{brand}</span>
      </div>

      {/* 主导航 */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        {/* 顶部入口 */}
        <div className="space-y-0.5">
          {TOP_ITEMS.map((item) => (
            <NavRow key={item.path} item={item} current={currentPath} onClick={handleNav} />
          ))}
        </div>

        {/* 能力分组 */}
        <div className="mt-3">
          <button
            type="button"
            onClick={() => setCapExpanded((v) => !v)}
            className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 ${sidebarNav.itemText} ${sidebarNav.itemDefault}`}
            aria-expanded={showCapabilities}
          >
            <Wrench className="h-4 w-4 shrink-0" />
            <span className="flex-1 text-left">能力</span>
            {showCapabilities ? (
              <ChevronDown className="h-3.5 w-3.5 opacity-70" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 opacity-70" />
            )}
          </button>
          {showCapabilities && (
            <div className="mt-0.5 space-y-0.5">
              {CAPABILITY_ITEMS.map((item) => (
                <NavRow key={item.path} item={item} current={currentPath} onClick={handleNav} indent />
              ))}
            </div>
          )}
        </div>

        {/* 任务中心 / 知识库 */}
        <div className="mt-3 space-y-0.5">
          {BOTTOM_ITEMS.map((item) => (
            <NavRow key={item.path} item={item} current={currentPath} onClick={handleNav} />
          ))}
        </div>

        {/* 分隔线 */}
        <div className="my-3 border-t border-border/40" />

        {/* 会话列表占位 */}
        <div>
          <div className="mb-1 px-2.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground/80">
            会话
          </div>
          {sessionList.length === 0 ? (
            <div className="rounded-lg px-2.5 py-3 text-xs text-muted-foreground/70">
              暂无历史会话，点击「新对话」开始。
            </div>
          ) : (
            <ul className="space-y-0.5">
              {sessionList.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    onClick={() => navigate(`/chat?session=${c.id}`)}
                    className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-xs ${sidebarNav.itemDefault}`}
                  >
                    <span className="truncate">{c.title || '未命名会话'}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* 分隔线 */}
        <div className="my-3 border-t border-border/40" />

        {/* 团队（Beta） */}
        <button
          type="button"
          onClick={() => navigate('/agents')}
          className={`flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 ${sidebarNav.itemText} ${sidebarNav.itemDefault}`}
        >
          <UserPlus className="h-4 w-4 shrink-0" />
          <span className="flex-1 text-left">团队</span>
          <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-primary">
            Beta
          </span>
        </button>
      </nav>

      {/* 底部用户区 + 升级 */}
      <div className="border-t border-border/40 p-2">
        <div className="flex items-center gap-2 rounded-xl px-2 py-2 hover:bg-muted/50 transition-colors">
          <button
            type="button"
            onClick={() => navigate('/settings')}
            className="flex flex-1 items-center gap-2 text-left"
            aria-label="账户设置"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/90 text-primary-foreground">
              <Users className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium text-foreground">我的账户</div>
              <div className="truncate text-[11px] text-muted-foreground">点击进入设置</div>
            </div>
          </button>
          <button
            type="button"
            onClick={() => navigate('/pricing')}
            className="flex shrink-0 items-center gap-1 rounded-lg bg-primary/10 px-2 py-1.5 text-[11px] font-medium text-primary hover:bg-primary/15"
            aria-label="升级订阅"
          >
            升级
            <ArrowUpRight className="h-3 w-3" />
          </button>
        </div>
      </div>
    </aside>
  )
}

export default SidebarV3
