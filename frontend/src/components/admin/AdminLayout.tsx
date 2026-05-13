import { useState, type ComponentType, type SVGProps } from 'react'
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { useAuthStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'

type HeroIcon = ComponentType<SVGProps<SVGSVGElement>>

interface NavItem {
  path: string
  label: string
  icon: HeroIcon
}

// 治理后台导航 — 按功能分组
interface NavGroup {
  label: string
  items: NavItem[]
}

const navGroups: NavGroup[] = [
  {
    label: '',
    items: [
      { path: '/admin', label: '治理总览', icon: icons.Dashboard },
    ],
  },
  {
    label: '用户与权限',
    items: [
      { path: '/admin/users', label: '用户管理', icon: icons.Users },
      { path: '/admin/roles', label: '角色权限', icon: icons.Shield },
      { path: '/admin/orgs', label: '组织管理', icon: icons.Building },
      { path: '/admin/security', label: '安全策略', icon: icons.Lock },
      { path: '/admin/audit', label: '审计日志', icon: icons.FileText },
      { path: '/admin/feature-flags', label: '功能开关', icon: icons.Target },
    ],
  },
  {
    label: '平台配置',
    items: [
      { path: '/admin/basic', label: '平台基础', icon: icons.Settings },
      { path: '/admin/ai-config', label: '模型治理', icon: icons.Cpu },
      { path: '/admin/integrations', label: '系统集成', icon: icons.Globe },
      { path: '/admin/health', label: '系统监控', icon: icons.Server },
      { path: '/admin/harness', label: 'Harness', icon: icons.Shield },
      { path: '/admin/incidents', label: '事件中心', icon: icons.AlertTriangle },
    ],
  },
  {
    label: '业务管理',
    items: [
      { path: '/admin/lawyer-verify', label: '律师认证', icon: icons.CheckCircle },
      { path: '/admin/billing', label: '计费管理', icon: icons.DollarSign },
    ],
  },
]

// 扁平化用于面包屑查找
const allNavItems = navGroups.flatMap(g => g.items)

export default function AdminLayout() {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuthStore()

  // 面包屑
  const currentNav = allNavItems.find(
    (item) =>
      item.path === location.pathname ||
      (item.path !== '/admin' && location.pathname.startsWith(item.path))
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

      {/* 侧边栏 — 使用主题系统颜色 */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 56 : 220 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className={`flex flex-col border-r border-border bg-card text-card-foreground shrink-0 ${
          mobileMenuOpen
            ? 'fixed inset-y-0 left-0 z-50 w-60'
            : 'hidden lg:flex'
        }`}
      >
        {/* Logo区域 */}
        <div className="flex items-center gap-3 px-4 h-16 border-b border-border">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0">
            <icons.Shield className="w-5 h-5 text-primary-foreground" />
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <h1 className="text-base font-medium text-foreground">治理后台</h1>
                <p className="text-xs text-muted-foreground">组织与平台治理</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* 导航列表（分组） */}
        <nav className="flex-1 py-2 overflow-y-auto">
          {navGroups.map((group, gi) => (
            <div key={gi}>
              {/* 分组标题 */}
              {group.label && !collapsed && (
                <div className="px-4 pt-4 pb-1">
                  <span className="text-[10px] font-medium text-muted-foreground/60 uppercase tracking-caption">
                    {group.label}
                  </span>
                </div>
              )}
              {group.label && collapsed && gi > 0 && (
                <div className="mx-3 my-2 h-px bg-border/50" />
              )}

              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive =
                    item.path === '/admin'
                      ? location.pathname === '/admin'
                      : location.pathname.startsWith(item.path)
                  const Icon = item.icon

                  return (
                    <NavLink
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 mx-2 px-3 py-2 rounded-lg transition-colors ${
                        isActive
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                      }`}
                      title={collapsed ? item.label : undefined}
                    >
                      <Icon className="w-4.5 h-4.5 shrink-0" />
                      <AnimatePresence>
                        {!collapsed && (
                          <motion.span
                            initial={{ opacity: 0, width: 0 }}
                            animate={{ opacity: 1, width: 'auto' }}
                            exit={{ opacity: 0, width: 0 }}
                            className="text-[13px] font-medium overflow-hidden whitespace-nowrap"
                          >
                            {item.label}
                          </motion.span>
                        )}
                      </AnimatePresence>
                    </NavLink>
                  )
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* 折叠按钮 */}
        <div className="p-3 border-t border-border">
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
          >
            {collapsed ? (
              <icons.ChevronRight className="w-5 h-5" />
            ) : (
              <>
                <icons.ChevronLeft className="w-5 h-5" />
                <span className="text-sm">收起侧栏</span>
              </>
            )}
          </button>
        </div>
      </motion.aside>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部栏 */}
        <header className="h-14 lg:h-16 shrink-0 border-b border-border bg-surface-1 flex items-center justify-between px-3 sm:px-6">
          <div className="flex items-center gap-2 sm:gap-3">
            {/* 移动端菜单按钮 */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="lg:hidden p-2 -ml-1 rounded-lg hover:bg-muted transition-colors"
            >
              <icons.Menu className="w-5 h-5 text-muted-foreground" />
            </button>
            <Badge className="bg-primary text-primary-foreground hover:bg-primary/90 text-xs">
              治理后台
            </Badge>
            <Separator orientation="vertical" className="h-5 hidden sm:block" />
            <nav className="hidden sm:flex items-center gap-1 text-sm text-muted-foreground">
              <span>治理</span>
              <icons.ChevronRight className="w-4 h-4" />
              <span className="text-foreground font-medium">{currentNav.label}</span>
            </nav>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate('/chat')}
              className="gap-1.5 text-xs sm:text-sm"
            >
              <icons.ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">返回前台</span>
            </Button>
            <div className="hidden sm:flex items-center gap-2">
              <Separator orientation="vertical" className="h-5" />
              <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-sm font-medium">
                {user?.name?.charAt(0) || 'A'}
              </div>
              <div className="text-sm hidden md:block">
                <p className="font-medium">{user?.name || '管理员'}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
            </div>
          </div>
        </header>

        {/* 页面内容 */}
        <main className="flex-1 overflow-auto bg-surface-2">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
