/**
 * LayoutV3.tsx — V3 应用主布局（仅在 VITE_V3_NAV=true 时使用）
 *
 * 与旧 Layout.tsx 并存，互不影响：
 * - 旧 Layout：顶部导航 + 模块侧边栏
 * - V3 Layout：左侧全局 SidebarV3 + 主内容 Outlet
 * - 移动端（<lg）：侧边栏变抽屉式，顶部显示汉堡菜单
 */

import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { SidebarV3 } from './SidebarV3'

export default function LayoutV3() {
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)
  const location = useLocation()

  // 路由变化时自动关闭移动端抽屉（useEffect 级别的简单处理）
  // 但 SidebarV3 内部点击导航时已主动调用 onMobileClose，这里作为二次保障
  return (
    <div className="flex h-[100dvh] min-h-[100dvh] overflow-hidden bg-surface-2">
      <SidebarV3
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* 移动端顶栏（桌面端隐藏） */}
        <header className="lg:hidden flex h-12 items-center justify-between gap-2 border-b border-border/60 bg-surface-1 px-3">
          <button
            type="button"
            onClick={() => setMobileSidebarOpen(true)}
            className="h-9 w-9 flex items-center justify-center rounded-md hover:bg-muted"
            aria-label="打开菜单"
          >
            <icons.Menu className="h-5 w-5" />
          </button>
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <icons.Scale className="h-3.5 w-3.5" />
            </div>
            <span className="text-sm font-semibold">安心智能助手</span>
          </div>
          <div className="w-9" />
        </header>
        <main className="flex-1 overflow-y-auto bg-surface-2">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
