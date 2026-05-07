/**
 * ProLayout — 服务方端（律师/律所）专属布局
 *
 * V2 架构：与需求方端 Layout.tsx 完全分离的导航和视觉风格
 * - 顶栏品牌区别（"安心法务 Pro"）
 * - 侧边栏导航（案源/客户/案件/账单/设置）
 * - 专业深色调，信息密度更高
 */

import { useState } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { useAuthStore } from '@/lib/store'

type HeroIcon = React.ComponentType<React.SVGProps<SVGSVGElement>>

interface NavItem {
  path: string
  label: string
  icon: HeroIcon
  badge?: string
}

interface NavGroup {
  label: string
  items: NavItem[]
}

// V2: 全部导航指向 /pro/* 子路径，与 App.tsx 中 /pro 的子路由对齐
const navGroups: NavGroup[] = [
  {
    label: '',
    items: [
      { path: '/pro/dashboard', label: '工作台', icon: icons.Dashboard },
    ],
  },
  {
    label: '业务管理',
    items: [
      { path: '/pro/cases', label: '案件管理', icon: icons.Briefcase },
      { path: '/pro/contracts', label: '合同管理', icon: icons.FileText },
      { path: '/pro/documents', label: '文档工作台', icon: icons.Edit },
    ],
  },
  {
    label: '客户与案源',
    items: [
      { path: '/pro/market', label: '案源市场', icon: icons.Search },
      { path: '/pro/messages', label: '客户消息', icon: icons.MessageCircle },
    ],
  },
  {
    label: '智能工具',
    items: [
      { path: '/pro/chat', label: 'AI 法律助手', icon: icons.Sparkles },
      { path: '/pro/knowledge', label: '法律智库', icon: icons.BookOpen },
      { path: '/pro/investigation', label: '尽职调查', icon: icons.BarChart3 },
    ],
  },
  {
    label: '账户',
    items: [
      { path: '/pro/onboarding', label: '执业认证', icon: icons.Shield },
      { path: '/pro/subscription', label: '订阅与账单', icon: icons.DollarSign },
      { path: '/pro/settings', label: '设置', icon: icons.Settings },
    ],
  },
]

const allNavItems = navGroups.flatMap(g => g.items)

export default function ProLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuthStore()

  const currentNav = allNavItems.find(
    (item) =>
      item.path === location.pathname ||
      (item.path !== '/pro/dashboard' && location.pathname.startsWith(item.path))
  ) || allNavItems[0]

  return (
    <div className="flex h-screen bg-surface-2 overflow-hidden">
      {/* 移动端遮罩 */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* 侧边栏 */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 56 : 240 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className={`flex flex-col border-r border-border bg-card text-card-foreground shrink-0 ${
          mobileMenuOpen
            ? 'fixed inset-y-0 left-0 z-50 w-60'
            : 'hidden lg:flex'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <icons.Scale className="w-5 h-5 text-primary-foreground" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <h1 className="text-base font-semibold text-foreground">安心法务 Pro</h1>
                <p className="text-[10px] text-muted-foreground">律师工作台</p>
              </motion.div>
            )}
          </AnimatePresence>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="ml-auto p-1 rounded hover:bg-muted transition-colors hidden lg:flex"
          >
            {collapsed ? (
              <icons.ChevronRight className="w-4 h-4 text-muted-foreground" />
            ) : (
              <icons.ChevronLeft className="w-4 h-4 text-muted-foreground" />
            )}
          </button>
        </div>

        {/* 导航 */}
        <nav className="flex-1 overflow-y-auto py-2">
          {navGroups.map((group, gi) => (
            <div key={gi}>
              {group.label && !collapsed && (
                <div className="px-4 pt-4 pb-1.5">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                    {group.label}
                  </span>
                </div>
              )}
              {group.label && collapsed && gi > 0 && (
                <div className="mx-3 my-2 border-t border-border" />
              )}
              {group.items.map((item) => {
                const isActive =
                  item.path === location.pathname ||
                  (item.path !== '/pro/dashboard' && location.pathname.startsWith(item.path))
                const Icon = item.icon
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={() => setMobileMenuOpen(false)}
                    className={`flex items-center gap-3 mx-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                      isActive
                        ? 'bg-primary/10 text-primary font-medium'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    }`}
                  >
                    <Icon className={`w-4.5 h-4.5 shrink-0 ${isActive ? 'text-primary' : ''}`} />
                    <AnimatePresence>
                      {!collapsed && (
                        <motion.span
                          initial={{ opacity: 0, width: 0 }}
                          animate={{ opacity: 1, width: 'auto' }}
                          exit={{ opacity: 0, width: 0 }}
                          className="whitespace-nowrap overflow-hidden"
                        >
                          {item.label}
                        </motion.span>
                      )}
                    </AnimatePresence>
                    {item.badge && !collapsed && (
                      <span className="ml-auto text-[10px] bg-destructive text-destructive-foreground px-1.5 py-0.5 rounded-full">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                )
              })}
            </div>
          ))}
        </nav>

        {/* 底部用户区 */}
        <div className="border-t border-border p-3">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
              <icons.User className="w-4 h-4 text-primary" />
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate">{user?.name || '律师'}</p>
                <p className="text-[10px] text-muted-foreground truncate">{user?.email}</p>
              </div>
            )}
            {!collapsed && (
              <button
                onClick={() => { navigate('/login'); logout() }}
                className="p-1.5 rounded hover:bg-muted transition-colors"
                title="退出登录"
              >
                <icons.LogOut className="w-3.5 h-3.5 text-muted-foreground" />
              </button>
            )}
          </div>
          {/* 切换到需求方端 */}
          {!collapsed && (
            <button
              onClick={() => navigate('/chat')}
              className="mt-2 w-full text-[10px] text-muted-foreground hover:text-primary transition-colors text-center py-1"
            >
              切换到用户端 →
            </button>
          )}
        </div>
      </motion.aside>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶栏 */}
        <header className="h-14 border-b border-border bg-card flex items-center px-4 gap-3 shrink-0">
          {/* 移动端菜单按钮 */}
          <button
            className="lg:hidden p-2 rounded-lg hover:bg-muted"
            onClick={() => setMobileMenuOpen(true)}
          >
            <icons.Menu className="w-5 h-5" />
          </button>
          {/* 面包屑 */}
          <div className="flex items-center gap-1.5 text-sm">
            <span className="text-muted-foreground">Pro</span>
            <icons.ChevronRight className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="font-medium text-foreground">{currentNav?.label}</span>
          </div>
          <div className="flex-1" />
          {/* 右侧功能 */}
          <button
            onClick={() => navigate('/admin')}
            className="p-2 rounded-lg hover:bg-muted transition-colors"
            title="后台管理"
          >
            <icons.Settings className="w-4.5 h-4.5 text-muted-foreground" />
          </button>
        </header>

        {/* 内容 */}
        <main className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
