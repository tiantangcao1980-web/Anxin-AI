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
 * - 智能调查：尽职调查（司法资讯 v2.0 启用）
 * - 法律智库：智慧搜索、知识图谱、司法智库、司法学院
 */

import React, { useEffect, useState, useCallback } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { NotificationCenter } from './NotificationCenter'
import { UserProfile } from './UserProfile'
import { notificationsApi } from '../lib/api'
import { useIMStore, useNotificationStore } from '@/lib/store'
import { usePermission } from '@/hooks/usePermission'

import { icons } from '@/lib/icons'
import { iconSize, buttonStyle, heading, sidebarNav } from '@/lib/design-tokens'
import { ModeSwitcher } from '@/components/mode-switcher/ModeSwitcher'
import { SyncStatus } from '@/components/mode-switcher/SyncStatus'

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
  { id: 'info-center', label: '智能调查', path: '/due-diligence' },
  { id: 'knowledge', label: '法律智库', path: '/knowledge-base' },
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
  feature?: string
}

const moduleSidebarConfig: { id: string; title: string; icon: React.ComponentType<React.SVGProps<SVGSVGElement>>; paths: string[]; items: SidebarItem[] }[] = [
  {
    id: 'collaboration',
    title: '智能协作',
    icon: icons.CollaborationGroup,
    paths: ['/cases', '/contracts', '/documents', '/collaboration', '/find-lawyer', '/compliance-check', '/leads', '/firm', '/lawyer-dashboard', '/acquisition'],
    items: [
      { path: '/cases', label: '案件管理', icon: icons.Cases, feature: 'case_management' },
      { path: '/contracts', label: '合同管理', icon: icons.Contracts, feature: 'contract_management' },
      { path: '/documents', label: '文档工作台', icon: icons.FileText, feature: 'document_management' },
      { path: '/collaboration', label: '协作模板', icon: icons.Collaboration, feature: 'collaboration' },
      { path: '/find-lawyer', label: '找律师', icon: icons.Scale, feature: 'lawyer_matching' },
      { path: '/compliance-check', label: '合规自检', icon: icons.ShieldCheck, feature: 'compliance_check' },
      { path: '/leads', label: '案源管理', icon: icons.Leads, feature: 'leads' },
    ],
  },
  {
    id: 'info-center',
    title: '智能调查',
    icon: icons.DueDiligence,
    paths: ['/due-diligence', '/due-diligence/risk', '/due-diligence/litigation', '/due-diligence/compliance', '/due-diligence/graph', '/due-diligence/sentiment', '/due-diligence/simulation', '/due-diligence/report'],
    items: [
      { path: '/due-diligence', label: '调查概览', icon: icons.BarChart3 },
      { path: '/due-diligence/risk', label: '风险评估', icon: icons.ShieldAlert },
      { path: '/due-diligence/litigation', label: '诉讼分析', icon: icons.Scale },
      { path: '/due-diligence/compliance', label: '信用合规', icon: icons.FileCheck },
      { path: '/due-diligence/graph', label: '关系图谱', icon: icons.Network },
      { path: '/due-diligence/sentiment', label: '舆情监控', icon: icons.Signal },
      { path: '/due-diligence/simulation', label: '风险推演', icon: icons.Cpu },
      { path: '/due-diligence/report', label: '调查报告', icon: icons.FileText },
      // { path: '/news', label: '司法资讯', icon: icons.News },  // v2.0 版本启用
    ],
  },
  {
    id: 'knowledge',
    title: '法律智库',
    icon: icons.KnowledgeGroup,
    paths: ['/knowledge-base', '/knowledge-graph'],
    items: [
      { path: '/knowledge-base', label: '知识库', icon: icons.Database },
      { path: '/knowledge-graph', label: '知识图谱', icon: icons.KnowledgeGraph },
    ],
  },
]

function ModuleSidebar({ currentPath, onNavigate }: { currentPath: string; onNavigate: (path: string) => void }) {
  const [collapsed, setCollapsed] = useState(false)
  const { canAccess } = usePermission()

  // 根据当前路由找到对应的模块
  const currentModule = moduleSidebarConfig.find(m =>
    m.paths.some(p => currentPath === p || currentPath.startsWith(p + '/'))
  )

  if (!currentModule) return null

  const visibleItems = currentModule.items.filter((item) =>
    item.feature ? canAccess(item.feature) : true
  )

  if (visibleItems.length === 0) return null

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
          <span className={`${sidebarNav.title} whitespace-nowrap`}>
            {currentModule.title}
          </span>
        )}
      </div>

      {/* 导航列表 */}
      <nav className="flex-1 py-2 space-y-0.5 overflow-y-auto">
        {visibleItems.map((item) => {
          // 精确匹配：避免 /due-diligence 匹配所有 /due-diligence/* 子路径
          const hasSubItems = visibleItems.some(other => other.path !== item.path && other.path.startsWith(item.path + '/'))
          const isActive = hasSubItems ? currentPath === item.path : (currentPath === item.path || currentPath.startsWith(item.path + '/'))
          const Icon = item.icon
          return (
            <button
              key={item.path}
              onClick={() => onNavigate(item.path)}
              className={`w-full flex items-center gap-2.5 mx-1.5 px-2.5 py-2 rounded-lg ${sidebarNav.itemText} transition-colors ${
                isActive
                  ? sidebarNav.itemActive
                  : sidebarNav.itemDefault
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
  'info-center': ['/due-diligence'],  // 子路径 /due-diligence/* 自动匹配
  'knowledge': ['/search', '/knowledge-graph', '/knowledge-base', '/academy'],
}

function isModuleActive(moduleId: string, pathname: string): boolean {
  const paths = modulePathMap[moduleId] || []
  return paths.some(p => pathname === p || pathname.startsWith(p + '/'))
}

function isPathActive(path: string, pathname: string): boolean {
  return pathname === path || pathname.startsWith(path + '/')
}

const HEADER_ACTION_LABELS_KEY = 'anxin-header-action-labels'

function readHeaderActionLabels(): boolean {
  try {
    const v = localStorage.getItem(HEADER_ACTION_LABELS_KEY)
    if (v === null) return true
    return v === '1'
  } catch {
    return true
  }
}

export default function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { canAccess } = usePermission()
  const [showNotifications, setShowNotifications] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [headerActionLabels, setHeaderActionLabels] = useState(readHeaderActionLabels)

  const toggleHeaderActionLabels = useCallback(() => {
    setHeaderActionLabels((prev) => {
      const next = !prev
      try {
        localStorage.setItem(HEADER_ACTION_LABELS_KEY, next ? '1' : '0')
      } catch {
        /* 隐私模式等场景下忽略 */
      }
      return next
    })
  }, [])

  // IM 未读数来自 store
  const imUnreadTotal = useIMStore((s) => s.unreadTotal)
  const notifUnreadCount = useNotificationStore((s) => s.unreadCount)
  const setNotifStore = useNotificationStore((s) => s.setNotifications)

  // 启动时从 API 同步通知未读数到 Store（后续由 WebSocket 实时更新）
  useEffect(() => {
    (async () => {
      try {
        const response = await notificationsApi.list({ unread_only: true })
        const items = response.data || []
        setNotifStore(items)
      } catch {
        // 静默处理
      }
    })()
  }, [setNotifStore])

  // 合并 IM + 通知未读数
  const combinedUnread = imUnreadTotal + notifUnreadCount

  const handleNavClick = useCallback(
    (path: string) => {
      navigate(path)
    },
    [navigate]
  )

  const currentPath = location.pathname

  // 获取当前模块配置（用于移动端二级导航）
  const currentModule = moduleSidebarConfig
    .map((module) => ({
      ...module,
      items: module.items.filter((item) => (item.feature ? canAccess(item.feature) : true)),
    }))
    .find((module) =>
      module.paths.some(p => currentPath === p || currentPath.startsWith(p + '/'))
    )

  return (
    <div className="flex h-[100dvh] min-h-[100dvh] flex-col overflow-hidden bg-surface-2">
      {/* ===== 固定顶部导航栏 ===== */}
      <header className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-surface-1/90 backdrop-blur-xl">
        <div className="h-[60px] px-4 lg:px-6 flex items-center">
          {/* 左侧：Logo */}
          <button
            type="button"
            onClick={() => handleNavClick('/chat')}
            className="flex w-auto shrink-0 items-center justify-start gap-2.5 mr-3 sm:mr-6 lg:mr-10 lg:w-[196px]"
          >
            <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shadow-sm">
              <icons.Legal className="w-[18px] h-[18px] text-white" />
            </div>
            <span className="text-xl font-semibold text-foreground tracking-tight hidden sm:block">
              安心法务
            </span>
          </button>

          {/* 中间：四大业务域直达链接（点击进入模块首页，模块内有左侧导航栏） */}
          <nav className="hidden lg:flex items-center gap-1 flex-1">
            {navGroups.map((group) => (
              <button
                key={group.id}
                onClick={() => handleNavClick(group.path)}
                className={`px-3.5 py-2 rounded-lg text-base font-medium transition-colors ${
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
          <div className="ml-auto flex items-center gap-1 sm:gap-1.5 md:gap-2">
            <div className="flex items-center gap-1 rounded-xl border border-border/60 bg-background/85 p-1 shadow-sm backdrop-blur-sm">
              <button
                onClick={() => navigate('/messages')}
                aria-label="消息"
                title="消息"
                className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-medium transition-colors md:h-10 md:w-auto md:text-sm ${
                  headerActionLabels ? 'md:gap-1.5 md:px-3' : 'md:px-2'
                } ${
                  currentPath === '/messages'
                    ? 'text-primary bg-primary/10'
                    : (combinedUnread > 0)
                      ? 'text-foreground bg-background shadow-sm hover:bg-muted/50'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                }`}
              >
                <icons.Chat className="h-4 w-4 shrink-0" />
                {headerActionLabels && <span className="hidden whitespace-nowrap md:inline">消息</span>}
                {(combinedUnread > 0) && (
                  <>
                    <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] bg-destructive text-white text-[10px] font-bold flex items-center justify-center rounded-full px-1 border-2 border-background animate-bounce-subtle">
                      {(combinedUnread) > 99 ? '99+' : (combinedUnread)}
                    </span>
                    <span className="absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] bg-destructive rounded-full animate-ping opacity-40" />
                  </>
                )}
              </button>

              {systemItems.map((item) => {
                const Icon = item.icon
                const isActive = isPathActive(item.path, currentPath)
                return (
                  <button
                    key={item.id}
                    type="button"
                    aria-label={item.label}
                    title={item.label}
                    onClick={() => handleNavClick(item.path)}
                    className={`relative flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-medium transition-colors md:h-10 md:w-auto md:text-sm ${
                      headerActionLabels ? 'md:gap-1.5 md:px-3' : 'md:px-2'
                    } ${
                      isActive
                        ? 'text-primary bg-primary/10'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/50'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    {headerActionLabels && <span className="hidden whitespace-nowrap md:inline">{item.label}</span>}
                  </button>
                )
              })}
            </div>

            <div className="hidden sm:flex items-center gap-1.5">
              <ModeSwitcher />
              <SyncStatus />
            </div>

            <div className="hidden lg:block h-5 w-px bg-border/60 mx-1" />

            {/* 用户头像 */}
            <button
              type="button"
              onClick={() => setShowProfile(!showProfile)}
              className={`${buttonStyle.icon} p-1.5 sm:p-2 rounded-lg sm:rounded-xl`}
            >
              <div className="w-7 h-7 sm:w-8 sm:h-8 bg-primary/90 rounded-full flex items-center justify-center">
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
        <main className="flex-1 overflow-hidden bg-surface-2">
          <Outlet />
        </main>
      </div>

      {/* ===== 移动端底部 Tab 栏 ===== */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 border-t border-border/50 bg-surface-1/95 backdrop-blur-xl" style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}>
        <div className="flex items-center justify-around h-14">
          {navGroups.map((group) => {
            const isActive = isModuleActive(group.id, currentPath)
            const groupIcons: Record<string, typeof icons.Chat> = {
              'ai-legal': icons.Chat,
              'collaboration': icons.Cases,
              'info-center': icons.DueDiligence,
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
        </div>
      </nav>

      {/* 通知中心 */}
      {showNotifications && (
        <NotificationCenter
          onClose={() => setShowNotifications(false)}
        />
      )}

      {/* 用户中心 */}
      {showProfile && (
        <UserProfile
          onClose={() => setShowProfile(false)}
          headerActionLabels={headerActionLabels}
          onToggleHeaderActionLabels={toggleHeaderActionLabels}
        />
      )}
    </div>
  )
}
