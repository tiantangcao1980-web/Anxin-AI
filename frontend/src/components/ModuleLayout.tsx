/**
 * ModuleLayout — 通用模块布局组件
 *
 * 左侧导航栏 + 右侧内容区。
 * 导航栏支持两种状态：展开（200px）和图标收起（56px）。
 * 样式与 AdminLayout 统一，使用主题系统颜色。
 */

import { useState, type ComponentType, type SVGProps } from 'react'
import { Outlet, NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'

type HeroIcon = ComponentType<SVGProps<SVGSVGElement>>

export interface ModuleNavItem {
  path: string
  label: string
  icon: HeroIcon
}

interface ModuleLayoutProps {
  title: string
  icon: HeroIcon
  navItems: ModuleNavItem[]
}

export default function ModuleLayout({ title, icon: TitleIcon, navItems }: ModuleLayoutProps) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const location = useLocation()

  return (
    <div className="flex h-full bg-background overflow-hidden">
      {/* 移动端遮罩 */}
      {mobileMenuOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* 左侧导航栏 */}
      <motion.aside
        initial={false}
        animate={{ width: collapsed ? 56 : 220 }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className={`flex flex-col border-r border-border bg-card shrink-0 ${
          mobileMenuOpen
            ? 'fixed inset-y-0 left-0 z-50 !w-52 top-[60px]'
            : 'hidden lg:flex'
        }`}
      >
        {/* 模块标题 */}
        <div className="flex items-center gap-2.5 px-3 h-12 border-b border-border shrink-0">
          <TitleIcon className="w-5 h-5 text-primary shrink-0" />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="text-sm font-medium text-foreground overflow-hidden whitespace-nowrap"
              >
                {title}
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* 导航列表 */}
        <nav className="flex-1 py-2 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || location.pathname.startsWith(item.path + '/')
            const Icon = item.icon

            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={() => setMobileMenuOpen(false)}
                className={`flex items-center gap-2.5 mx-1.5 px-2.5 py-2 rounded-lg text-[13px] transition-colors ${
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
                      className="overflow-hidden whitespace-nowrap"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
              </NavLink>
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
      </motion.aside>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* 移动端：菜单按钮（仅 lg 以下显示） */}
        <div className="lg:hidden h-10 border-b border-border bg-background flex items-center px-3 shrink-0">
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-1.5 rounded-lg hover:bg-muted transition-colors"
          >
            <icons.Menu className="w-4.5 h-4.5 text-muted-foreground" />
          </button>
          <span className="ml-2 text-sm font-medium text-foreground">{title}</span>
        </div>

        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </div>
    </div>
  )
}
