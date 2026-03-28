/**
 * Layout.tsx - 应用主布局组件
 *
 * ===== 顶部导航栏设计 =====
 * 受 Apple.com / Insta360.com 启发的顶部导航
 * - 固定顶栏 60px，Logo 左置，四大业务域下拉菜单居中，系统功能右置
 * - 移动端：汉堡菜单 -> 全屏下拉菜单
 * - 内容区域全宽，无侧边栏占用水平空间
 *
 * 导航分组（对应 PRD 四大业务域）：
 * - AI法务：直达智能对话（无下拉菜单，左侧为对话列表）
 * - 智能协作：案件管理、合同管理（含审查）、在线协作（含文档+工作台）、找律师（含律师精英）、合规自检、案源管理
 * - 信息中心：司法资讯、尽职调查
 * - 法律智库：智慧搜索、知识图谱、司法智库、司法学院
 */

import { useEffect, useState, useCallback, useRef, type ComponentType, type SVGProps } from 'react'
import { createPortal } from 'react-dom'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { NotificationCenter } from './NotificationCenter'
import { UserProfile } from './UserProfile'
import { HardwareStatus } from './ui/HardwareStatus'
import { PrivacyToggle } from './ui/PrivacyToggle'
import { notificationsApi } from '../lib/api'
import { useAuthStore } from '@/lib/store'

import { icons } from '@/lib/icons'
import { iconSize, buttonStyle, heading } from '@/lib/design-tokens'

// Heroicons 组件类型
type HeroIcon = ComponentType<SVGProps<SVGSVGElement>>

// ===== 四大业务域导航数据结构 =====

interface NavChild {
  id: string
  path: string
  label: string
  icon: HeroIcon
}

interface NavGroup {
  id: string
  label: string
  icon: HeroIcon
  path?: string // 直达链接（无下拉菜单时使用）
  children: NavChild[]
}

const navGroups: NavGroup[] = [
  {
    id: 'ai-legal',
    label: 'AI法务',
    icon: icons.AILegal,
    path: '/chat', // 直达智能对话，无下拉菜单
    children: [],
  },
  {
    id: 'collaboration',
    label: '智能协作',
    icon: icons.CollaborationGroup,
    children: [
      { id: 'cases', path: '/cases', label: '案件管理', icon: icons.Cases },
      { id: 'contracts', path: '/contracts', label: '合同管理', icon: icons.Contracts },
      { id: 'collaboration', path: '/collaboration', label: '在线协作', icon: icons.Collaboration },
      { id: 'find-lawyer', path: '/find-lawyer', label: '找律师', icon: icons.Scale },
      { id: 'compliance-check', path: '/compliance-check', label: '合规自检', icon: icons.ShieldCheck },
      { id: 'leads', path: '/leads', label: '案源管理', icon: icons.Leads },
      { id: 'acquisition', path: '/acquisition', label: '获客看板', icon: icons.BarChart3 },
      { id: 'firm', path: '/firm', label: '律所管理', icon: icons.Building },
      { id: 'pricing', path: '/pricing', label: '套餐定价', icon: icons.DollarSign },
      { id: 'lawyer-dashboard', path: '/lawyer-dashboard', label: '律师工作台', icon: icons.Dashboard },
    ],
  },
  {
    id: 'info-center',
    label: '信息中心',
    icon: icons.InfoCenter,
    children: [
      { id: 'news', path: '/news', label: '司法资讯', icon: icons.News },
      { id: 'due-diligence', path: '/due-diligence', label: '尽职调查', icon: icons.DueDiligence },
    ],
  },
  {
    id: 'knowledge',
    label: '法律智库',
    icon: icons.KnowledgeGroup,
    children: [
      { id: 'search', path: '/search', label: '智慧搜索', icon: icons.Search },
      { id: 'knowledge-graph', path: '/knowledge-graph', label: '知识图谱', icon: icons.KnowledgeGraph },
      { id: 'knowledge-base', path: '/knowledge-base', label: '司法智库', icon: icons.KnowledgeBase },
      { id: 'academy', path: '/academy', label: '司法学院', icon: icons.Academy },
    ],
  },
]

// 系统功能（右侧图标按钮）— 审批已整合进任务中心，系统设置已整合进后台管理
const systemItems: NavChild[] = [
  { id: 'messages', path: '/messages', label: '消息', icon: icons.Chat },
  { id: 'tasks', path: '/tasks', label: '任务中心', icon: icons.Tasks },
]

// ===== 工具函数 =====
function isGroupActive(group: NavGroup, pathname: string): boolean {
  if (group.path) {
    return pathname === group.path || pathname.startsWith(group.path + '/')
  }
  return group.children.some(
    (child) => pathname === child.path || pathname.startsWith(child.path + '/')
  )
}

function isPathActive(path: string, pathname: string): boolean {
  return pathname === path || pathname.startsWith(path + '/')
}

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()
  const isAdmin = user?.role === 'admin'
  const [showNotifications, setShowNotifications] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  // 桌面端下拉菜单状态
  const [openDropdown, setOpenDropdown] = useState<string | null>(null)
  const dropdownTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const navRef = useRef<HTMLDivElement>(null)
  const dropdownPanelRef = useRef<HTMLDivElement>(null)

  // 移动端菜单状态
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [mobileExpandedGroup, setMobileExpandedGroup] = useState<string | null>(null)

  // 通知轮询
  useEffect(() => {
    const fetchUnreadCount = async () => {
      try {
        const response = await notificationsApi.list({ unread_only: true })
        setUnreadCount(response.total || 0)
      } catch {
        // 静默处理
      }
    }
    fetchUnreadCount()
    const interval = setInterval(fetchUnreadCount, 120000)
    return () => clearInterval(interval)
  }, [])

  // 路由变化时关闭菜单
  useEffect(() => {
    setMobileMenuOpen(false)
    setMobileExpandedGroup(null)
    setOpenDropdown(null)
  }, [location.pathname])

  // 点击外部关闭下拉菜单（排除 Portal 渲染的面板）
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node
      // 不关闭：点击在导航栏内 或 下拉面板内
      if (navRef.current?.contains(target)) return
      if (dropdownPanelRef.current?.contains(target)) return
      setOpenDropdown(null)
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleNavClick = useCallback(
    (path: string) => {
      navigate(path)
      setMobileMenuOpen(false)
      setMobileExpandedGroup(null)
      setOpenDropdown(null)
    },
    [navigate]
  )

  // 桌面端下拉菜单：纯点击模式（Portal 与 nav 不在同一 DOM 树，hover 交互不可靠）
  const handleDropdownEnter = useCallback((_groupId: string) => {
    if (dropdownTimeoutRef.current) {
      clearTimeout(dropdownTimeoutRef.current)
      dropdownTimeoutRef.current = null
    }
  }, [])

  const handleDropdownLeave = useCallback(() => {
    // 不自动关闭，通过点击遮罩层或菜单项来关闭
  }, [])

  const toggleMobileGroup = useCallback((groupId: string) => {
    setMobileExpandedGroup((prev) => (prev === groupId ? null : groupId))
  }, [])

  const currentPath = location.pathname

  return (
    <div className="h-screen bg-muted/30 flex flex-col overflow-hidden">
      {/* ===== 固定顶部导航栏 ===== */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border/50">
        <div className="h-[60px] px-4 lg:px-6 flex items-center">
          {/* 左侧：Logo */}
          <button
            onClick={() => handleNavClick('/chat')}
            className="flex items-center gap-2.5 shrink-0 mr-6 lg:mr-10"
          >
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shadow-sm">
              <icons.Legal className="w-[18px] h-[18px] text-white" />
            </div>
            <span className={`${heading.section} tracking-tight hidden sm:block`}>
              安心法务
            </span>
          </button>

          {/* 中间：桌面端导航组（Apple/影石风格全屏下拉） */}
          <nav ref={navRef} className="hidden lg:flex items-center gap-1 flex-1">
            {navGroups.map((group) => {
              const groupActive = isGroupActive(group, currentPath)
              const hasChildren = group.children.length > 0
              const isOpen = openDropdown === group.id

              // 无子菜单的组 → 直达链接
              if (!hasChildren && group.path) {
                return (
                  <button
                    key={group.id}
                    onClick={() => handleNavClick(group.path!)}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                      groupActive
                        ? 'text-primary'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                    }`}
                  >
                    <span>{group.label}</span>
                  </button>
                )
              }

              // 有子菜单的组 → 下拉面板
              return (
                <div key={group.id}>
                  <button
                    onClick={() => setOpenDropdown(isOpen ? null : group.id)}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                      groupActive
                        ? 'text-primary'
                        : isOpen
                          ? 'text-foreground bg-muted/60'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                    }`}
                  >
                    <span>{group.label}</span>
                    <icons.ChevronDown
                      className={`w-3.5 h-3.5 transition-transform duration-200 ${
                        isOpen ? 'rotate-180' : ''
                      }`}
                    />
                  </button>
                </div>
              )
            })}
          </nav>

          {/* 右侧：系统功能 + 用户区 */}
          <div className="flex items-center gap-1 ml-auto">
            {/* 桌面端系统功能图标按钮 */}
            <div className="hidden lg:flex items-center gap-0.5">
              {systemItems.map((item) => {
                const Icon = item.icon
                const isActive = isPathActive(item.path, currentPath)
                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.path)}
                    title={item.label}
                    className={`${buttonStyle.icon} ${
                      isActive
                        ? 'text-primary bg-primary/10'
                        : ''
                    }`}
                  >
                    <Icon className={iconSize.md} />
                  </button>
                )
              })}

              {/* 后台管理入口已迁移到用户面板中 */}
            </div>

            {/* 分隔线 */}
            <div className="hidden lg:block h-5 w-px bg-border/60 mx-1.5" />

            {/* 硬件状态 & 隐私开关（仅桌面端） */}
            <div className="hidden lg:flex items-center gap-1">
              <HardwareStatus />
              <PrivacyToggle />
            </div>

            <div className="hidden lg:block h-5 w-px bg-border/60 mx-1.5" />

            {/* 通知按钮 */}
            <button
              onClick={() => setShowNotifications(!showNotifications)}
              className={`relative ${buttonStyle.icon}`}
            >
              <icons.Notification className={`${iconSize.md} text-muted-foreground`} />
              {unreadCount > 0 && (
                <span className="absolute top-1 right-1 min-w-[16px] h-[16px] bg-primary text-white text-[10px] font-bold flex items-center justify-center rounded-full px-1 border-2 border-background">
                  {unreadCount}
                </span>
              )}
            </button>

            {/* 用户头像 */}
            <button
              onClick={() => setShowProfile(!showProfile)}
              className={buttonStyle.icon}
            >
              <div className={`${iconSize.xl} bg-primary/90 rounded-full flex items-center justify-center`}>
                <icons.User className={`${iconSize.sm} text-white`} />
              </div>
            </button>

            {/* 移动端汉堡菜单按钮 */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className={`lg:hidden ${buttonStyle.icon} ml-1`}
            >
              {mobileMenuOpen ? (
                <icons.Close className={`${iconSize.md} text-foreground`} />
              ) : (
                <icons.Menu className={`${iconSize.md} text-muted-foreground`} />
              )}
            </button>
          </div>
        </div>

        {/* ===== 移动端下拉全屏菜单 ===== */}
        {mobileMenuOpen && (
          <>
            {/* 遮罩 */}
            <div
              className="lg:hidden fixed inset-0 top-[60px] bg-black/30 z-40"
              onClick={() => {
                setMobileMenuOpen(false)
                setMobileExpandedGroup(null)
              }}
            />
            {/* 菜单面板 */}
            <div className="lg:hidden absolute top-[60px] left-0 right-0 bg-background border-b border-border shadow-xl z-50 max-h-[calc(100vh-60px)] overflow-y-auto animate-in slide-in-from-top-2 duration-200">
              <div className="px-4 py-3 space-y-1">
                {/* 四大导航组 */}
                {navGroups.map((group) => {
                  const GroupIcon = group.icon
                  const groupActive = isGroupActive(group, currentPath)
                  const hasChildren = group.children.length > 0
                  const isExpanded = mobileExpandedGroup === group.id

                  // 无子菜单 → 直达链接
                  if (!hasChildren && group.path) {
                    return (
                      <button
                        key={group.id}
                        onClick={() => handleNavClick(group.path!)}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-[15px] font-medium transition-colors ${
                          groupActive
                            ? 'text-primary bg-primary/5'
                            : 'text-foreground hover:bg-muted/60'
                        }`}
                      >
                        <GroupIcon className="w-5 h-5 shrink-0" />
                        <span className="flex-1 text-left">{group.label}</span>
                      </button>
                    )
                  }

                  return (
                    <div key={group.id}>
                      <button
                        onClick={() => toggleMobileGroup(group.id)}
                        className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-[15px] font-medium transition-colors ${
                          groupActive
                            ? 'text-primary bg-primary/5'
                            : 'text-foreground hover:bg-muted/60'
                        }`}
                      >
                        <GroupIcon className="w-5 h-5 shrink-0" />
                        <span className="flex-1 text-left">{group.label}</span>
                        <icons.ChevronDown
                          className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${
                            isExpanded ? 'rotate-180' : ''
                          }`}
                        />
                      </button>

                      {/* 子菜单展开 */}
                      {isExpanded && (
                        <div className="ml-4 pl-4 border-l-2 border-border/40 space-y-0.5 py-1 animate-in slide-in-from-top-1 duration-150">
                          {group.children.map((child) => {
                            const ChildIcon = child.icon
                            const isActive = isPathActive(child.path, currentPath)
                            return (
                              <button
                                key={child.id}
                                onClick={() => handleNavClick(child.path)}
                                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                                  isActive
                                    ? 'text-primary bg-primary/8 font-medium'
                                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                                }`}
                              >
                                <ChildIcon className="w-4 h-4 shrink-0" />
                                <span>{child.label}</span>
                                {isActive && (
                                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />
                                )}
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  )
                })}

                {/* 分隔线 */}
                <div className="h-px bg-border/50 my-2" />

                {/* 系统功能 */}
                {systemItems.map((item) => {
                  const Icon = item.icon
                  const isActive = isPathActive(item.path, currentPath)
                  return (
                    <button
                      key={item.id}
                      onClick={() => handleNavClick(item.path)}
                      className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-[15px] transition-colors ${
                        isActive
                          ? 'text-primary bg-primary/5 font-medium'
                          : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                      }`}
                    >
                      <Icon className="w-5 h-5 shrink-0" />
                      <span>{item.label}</span>
                    </button>
                  )
                })}

                {/* 管理员入口 */}
                {isAdmin && (
                  <button
                    onClick={() => {
                      navigate('/admin')
                      setMobileMenuOpen(false)
                    }}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-[15px] transition-colors ${
                      currentPath.startsWith('/admin')
                        ? 'text-amber-600 bg-amber-500/10 font-medium'
                        : 'text-amber-500/80 hover:text-amber-600 hover:bg-amber-500/10'
                    }`}
                  >
                    <icons.Shield className="w-5 h-5 shrink-0" />
                    <span>后台管理</span>
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </header>

      {/* ===== 全屏下拉面板（Portal 渲染到 body，避免 header 层叠上下文问题） ===== */}
      {openDropdown && createPortal(
        <div ref={dropdownPanelRef}>
          {/* 背景遮罩 — 仅点击关闭，不响应 mouseEnter */}
          <div
            className="fixed inset-0 top-[60px] bg-black/20 backdrop-blur-sm z-[60]"
            onClick={() => setOpenDropdown(null)}
          />
          {/* 下拉面板 */}
          <div
            className="fixed top-[60px] left-0 right-0 z-[70] bg-background/95 backdrop-blur-xl border-b border-border/60 shadow-xl animate-in fade-in slide-in-from-top-1 duration-200"
          >
            <div className="max-w-7xl mx-auto px-6 lg:px-10 py-6">
              <div className="grid grid-cols-2 xl:grid-cols-3 gap-1">
                {navGroups
                  .find((g) => g.id === openDropdown)
                  ?.children.map((child) => {
                    const ChildIcon = child.icon
                    const isActive = isPathActive(child.path, currentPath)
                    return (
                      <button
                        key={child.id}
                        onClick={() => handleNavClick(child.path)}
                        className={`flex items-center gap-3 px-4 py-3.5 rounded-xl text-sm transition-all group ${
                          isActive
                            ? 'text-primary bg-primary/8 font-medium'
                            : 'text-foreground/80 hover:bg-muted/70 hover:text-foreground'
                        }`}
                      >
                        <div
                          className={`p-2 rounded-lg transition-colors ${
                            isActive
                              ? 'bg-primary/15 text-primary'
                              : 'bg-muted/80 text-muted-foreground group-hover:bg-primary/10 group-hover:text-primary'
                          }`}
                        >
                          <ChildIcon className="w-4.5 h-4.5" />
                        </div>
                        <span>{child.label}</span>
                        {isActive && (
                          <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary" />
                        )}
                      </button>
                    )
                  })}
              </div>
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* ===== 页面内容区（顶部留出导航栏高度） ===== */}
      <main className="flex-1 pt-[60px] overflow-hidden">
        <Outlet />
      </main>

      {/* 通知中心 */}
      {showNotifications && (
        <NotificationCenter
          onClose={() => setShowNotifications(false)}
          onClearAll={() => setUnreadCount(0)}
        />
      )}

      {/* 用户中心 */}
      {showProfile && <UserProfile onClose={() => setShowProfile(false)} />}
    </div>
  )
}
