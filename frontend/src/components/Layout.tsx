/**
 * Layout.tsx - 应用主布局组件
 *
 * ===== 顶部导航栏设计 =====
 * 受 Apple.com / Insta360.com 启发的顶部导航
 * - 固定顶栏 60px，Logo 左置，四大业务域下拉菜单居中，系统功能右置
 * - 移动端：底部 Tab 栏 + 顶部二级水平滚动导航
 * - 内容区域全宽，无侧边栏占用水平空间
 *
 * 导航分组（对应 PRD 四大业务域）：
 * - AI法务：直达智能对话（无下拉菜单，左侧为对话列表）
 * - 智能协作：案件管理、合同管理（含审查）、在线协作（含文档+工作台）、找律师（含律师精英）、合规自检、案源管理
 * - 信息中心：司法资讯、尽职调查
 * - 法律智库：智慧搜索、知识图谱、司法智库、司法学院
 */

import React, { useEffect, useState, useCallback } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { NotificationCenter } from './NotificationCenter'
import { UserProfile } from './UserProfile'
import { HardwareStatus } from './ui/HardwareStatus'
import { PrivacyToggle } from './ui/PrivacyToggle'
import { notificationsApi } from '../lib/api'
import { useAuthStore } from '@/lib/store'

import { toast } from 'sonner'
import { icons } from '@/lib/icons'
import { iconSize, buttonStyle, heading } from '@/lib/design-tokens'

// Heroicons 组件类型
type HeroIcon = React.ComponentType<React.SVGProps<SVGSVGElement>>

// 系统功能导航项
interface NavChild {
  id: string
  path: string
  label: string
  icon: HeroIcon
}

// 四大业务域 — 全部为直达链接，点击进入模块首页（各模块有自己的左侧导航栏）
const navGroups: { id: string; label: string; path: string }[] = [
  { id: 'ai-legal', label: 'AI法务', path: '/chat' },
  { id: 'collaboration', label: '智能协作', path: '/cases' },
  { id: 'info-center', label: '信息中心', path: '/news' },
  { id: 'knowledge', label: '法律智库', path: '/knowledge-graph' },
]

// 系统功能（右侧图标按钮）— 审批已整合进任务中心，系统设置已整合进后台管理
const systemItems: NavChild[] = [
  { id: 'tasks', path: '/tasks', label: '任务中心', icon: icons.Tasks },
]

// ===== 模块侧边栏配置 =====
interface SidebarItem {
  path: string
  label: string
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>
}

const moduleSidebarConfig: { id: string; title: string; icon: React.ComponentType<React.SVGProps<SVGSVGElement>>; paths: string[]; items: SidebarItem[] }[] = [
  {
    id: 'collaboration',
    title: '智能协作',
    icon: icons.CollaborationGroup,
    paths: ['/cases', '/contracts', '/collaboration', '/find-lawyer', '/compliance-check', '/leads', '/firm', '/lawyer-dashboard', '/acquisition'],
    items: [
      { path: '/cases', label: '案件管理', icon: icons.Cases },
      { path: '/contracts', label: '合同管理', icon: icons.Contracts },
      { path: '/collaboration', label: '在线协作', icon: icons.Collaboration },
      { path: '/find-lawyer', label: '找律师', icon: icons.Scale },
      { path: '/compliance-check', label: '合规自检', icon: icons.ShieldCheck },
      { path: '/leads', label: '案源管理', icon: icons.Leads },
    ],
  },
  {
    id: 'info-center',
    title: '信息中心',
    icon: icons.InfoCenter,
    paths: ['/news', '/due-diligence'],
    items: [
      { path: '/news', label: '司法资讯', icon: icons.News },
      { path: '/due-diligence', label: '尽职调查', icon: icons.DueDiligence },
    ],
  },
  {
    id: 'knowledge',
    title: '法律智库',
    icon: icons.KnowledgeGroup,
    paths: ['/knowledge-graph', '/knowledge-base'],
    items: [
      { path: '/knowledge-graph', label: '知识图谱', icon: icons.KnowledgeGraph },
      { path: '/knowledge-base', label: '司法智库', icon: icons.KnowledgeBase },
    ],
  },
]

function ModuleSidebar({ currentPath, onNavigate }: { currentPath: string; onNavigate: (path: string) => void }) {
  const [collapsed, setCollapsed] = useState(false)

  // 根据当前路由找到对应的模块
  const currentModule = moduleSidebarConfig.find(m =>
    m.paths.some(p => currentPath === p || currentPath.startsWith(p + '/'))
  )

  if (!currentModule) return null

  const TitleIcon = currentModule.icon

  return (
    <div
      className="hidden lg:flex flex-col border-r border-border bg-card shrink-0 transition-all duration-200"
      style={{ width: collapsed ? 56 : 220 }}
    >
      {/* 模块标题 */}
      <div className="flex items-center gap-2.5 px-3 h-12 border-b border-border shrink-0">
        <TitleIcon className="w-5 h-5 text-primary shrink-0" />
        {!collapsed && (
          <span className="text-sm font-bold text-foreground whitespace-nowrap">
            {currentModule.title}
          </span>
        )}
      </div>

      {/* 导航列表 */}
      <nav className="flex-1 py-2 space-y-0.5 overflow-y-auto">
        {currentModule.items.map((item) => {
          const isActive = currentPath === item.path || currentPath.startsWith(item.path + '/')
          const Icon = item.icon
          return (
            <button
              key={item.path}
              onClick={() => onNavigate(item.path)}
              className={`w-full flex items-center gap-2.5 mx-1.5 px-2.5 py-2 rounded-lg text-[13px] transition-colors ${
                isActive
                  ? 'bg-primary/10 text-primary font-medium'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
              title={collapsed ? item.label : undefined}
              style={{ width: `calc(100% - ${collapsed ? '8px' : '12px'})` }}
            >
              <Icon className="w-4.5 h-4.5 shrink-0" />
              {!collapsed && <span className="whitespace-nowrap">{item.label}</span>}
            </button>
          )
        })}
      </nav>

      {/* 折叠按钮 */}
      <div className="p-2 border-t border-border">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-center gap-2 py-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors text-xs"
        >
          {collapsed ? (
            <icons.ChevronRight className="w-4 h-4" />
          ) : (
            <>
              <icons.ChevronLeft className="w-4 h-4" />
              <span>收起</span>
            </>
          )}
        </button>
      </div>
    </div>
  )
}

// 路由活跃检测 — 检查当前路径是否属于某个模块
const modulePathMap: Record<string, string[]> = {
  'ai-legal': ['/chat'],
  'collaboration': ['/cases', '/contracts', '/collaboration', '/find-lawyer', '/compliance-check', '/leads', '/acquisition', '/firm', '/lawyer-dashboard'],
  'info-center': ['/news', '/due-diligence'],
  'knowledge': ['/search', '/knowledge-graph', '/knowledge-base', '/academy'],
}

function isModuleActive(moduleId: string, pathname: string): boolean {
  const paths = modulePathMap[moduleId] || []
  return paths.some(p => pathname === p || pathname.startsWith(p + '/'))
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
  const [showMoreMenu, setShowMoreMenu] = useState(false)

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

  // 路由变化时关闭更多菜单
  useEffect(() => {
    setShowMoreMenu(false)
  }, [location.pathname])

  const handleNavClick = useCallback(
    (path: string) => {
      navigate(path)
      setShowMoreMenu(false)
    },
    [navigate]
  )

  const currentPath = location.pathname

  // 获取当前模块配置（用于移动端二级导航）
  const currentModule = moduleSidebarConfig.find(m =>
    m.paths.some(p => currentPath === p || currentPath.startsWith(p + '/'))
  )

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

          {/* 中间：四大业务域直达链接（点击进入模块首页，模块内有左侧导航栏） */}
          <nav className="hidden lg:flex items-center gap-1 flex-1">
            {navGroups.map((group) => (
              <button
                key={group.id}
                onClick={() => handleNavClick(group.path)}
                className={`px-3.5 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isModuleActive(group.id, currentPath)
                    ? 'text-primary'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                }`}
              >
                {group.label}
              </button>
            ))}
          </nav>

          {/* 右侧：系统功能 + 用户区 */}
          <div className="flex items-center gap-1.5 ml-auto">
            {/* 桌面端系统功能（图标+文字按钮） */}
            <div className="hidden lg:flex items-center gap-1">
              {systemItems.map((item) => {
                const Icon = item.icon
                const isActive = isPathActive(item.path, currentPath)
                return (
                  <button
                    key={item.id}
                    onClick={() => handleNavClick(item.path)}
                    className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isActive
                        ? 'text-primary bg-primary/10'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.label}</span>
                  </button>
                )
              })}
            </div>

            {/* 分隔线 */}
            <div className="hidden lg:block h-5 w-px bg-border/60 mx-1" />

            {/* AI 私有助手 & 隐私开关 */}
            <div className="hidden lg:flex items-center gap-1">
              <HardwareStatus />
              <PrivacyToggle />
            </div>
            {/* 移动/Web端 AI 助手占位（灰色图标，提示仅桌面端可用） */}
            <button
              className="lg:hidden p-2 text-muted-foreground/40 hover:text-muted-foreground/60 transition-colors"
              onClick={() => toast.info('AI 私有助手目前仅支持桌面端使用，您可以通过消息与桌面端远程协作', { duration: 4000 })}
              title="AI 私有助手（仅桌面端）"
            >
              <icons.Cpu className={iconSize.md} />
            </button>

            <div className="hidden lg:block h-5 w-px bg-border/60 mx-1" />

            {/* 消息入口（整合通知） */}
            <button
              onClick={() => navigate('/messages')}
              className={`relative ${buttonStyle.icon} ${currentPath === '/messages' ? 'text-primary' : ''}`}
            >
              <icons.Chat className={`${iconSize.md} ${currentPath === '/messages' ? 'text-primary' : 'text-muted-foreground'}`} />
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

          </div>
        </div>

        {/* ===== 移动端二级导航栏（顶栏下方水平滚动） ===== */}
        {currentModule && (
          <div className="lg:hidden border-t border-border/30 overflow-x-auto scrollbar-hide">
            <div className="flex items-center gap-1 px-3 py-1.5 min-w-max">
              {currentModule.items.map((item) => {
                const ItemIcon = item.icon
                const itemActive = isPathActive(item.path, currentPath)
                return (
                  <button
                    key={item.path}
                    onClick={() => navigate(item.path)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                      itemActive
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-muted/60'
                    }`}
                  >
                    <ItemIcon className="w-3.5 h-3.5" />
                    <span>{item.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        )}
      </header>

      {/* ===== 页面内容区（顶部留出导航栏高度，移动端底部留出 Tab 栏高度） ===== */}
      <div className={`flex-1 overflow-hidden flex pb-14 lg:pb-0 ${currentModule ? 'pt-[100px] lg:pt-[60px]' : 'pt-[60px]'}`}>
        {/* 模块侧边栏（Chat 页面有自己的内部侧边栏，不显示；移动端已通过 ModuleSidebar 内部 hidden lg:flex 隐藏） */}
        {!currentPath.startsWith('/chat') && !currentPath.startsWith('/messages') && !currentPath.startsWith('/tasks') && !currentPath.startsWith('/settings') && (
          <ModuleSidebar currentPath={currentPath} onNavigate={handleNavClick} />
        )}
        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>

      {/* ===== 移动端底部 Tab 栏 ===== */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-background border-t border-border/50" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        <div className="flex items-center justify-around h-14">
          {navGroups.map((group) => {
            const isActive = isModuleActive(group.id, currentPath)
            const groupIcons: Record<string, typeof icons.Chat> = {
              'ai-legal': icons.Chat,
              'collaboration': icons.Cases,
              'info-center': icons.News,
              'knowledge': icons.KnowledgeGraph,
            }
            const GroupIcon = groupIcons[group.id] || icons.Chat
            return (
              <button
                key={group.id}
                onClick={() => handleNavClick(group.path)}
                className={`flex flex-col items-center gap-0.5 px-3 py-1 min-w-[60px] ${
                  isActive ? 'text-primary' : 'text-muted-foreground'
                }`}
              >
                <GroupIcon className="w-5 h-5" />
                <span className="text-[10px] font-medium">{group.label}</span>
              </button>
            )
          })}
          {/* 更多按钮 */}
          <button
            onClick={() => setShowMoreMenu(!showMoreMenu)}
            className={`flex flex-col items-center gap-0.5 px-3 py-1 min-w-[60px] ${
              showMoreMenu ? 'text-primary' : 'text-muted-foreground'
            }`}
          >
            <icons.MoreHorizontal className="w-5 h-5" />
            <span className="text-[10px] font-medium">更多</span>
          </button>
        </div>
      </nav>

      {/* ===== 移动端"更多"弹出面板 ===== */}
      {showMoreMenu && (
        <>
          <div
            className="lg:hidden fixed inset-0 z-40"
            onClick={() => setShowMoreMenu(false)}
          />
          <div className="lg:hidden fixed bottom-14 left-0 right-0 z-50 bg-background border-t border-border/50 shadow-lg rounded-t-2xl animate-in slide-in-from-bottom-2 duration-200" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
            <div className="px-4 py-3 space-y-1">
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
              {isAdmin && (
                <button
                  onClick={() => handleNavClick('/admin')}
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
