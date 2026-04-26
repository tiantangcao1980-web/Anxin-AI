/**
 * LayoutV3.tsx — V3 应用主布局（仅在 VITE_V3_NAV=true 时使用）
 *
 * 与旧 Layout.tsx 并存，互不影响：
 * - 旧 Layout：顶部导航 + 模块侧边栏
 * - V3 Layout：左侧全局 SidebarV3 + 主内容 Outlet
 */

import { Outlet } from 'react-router-dom'
import { SidebarV3 } from './SidebarV3'

export default function LayoutV3() {
  return (
    <div className="flex h-[100dvh] min-h-[100dvh] overflow-hidden bg-surface-2">
      <SidebarV3 />
      <main className="flex-1 overflow-y-auto bg-surface-2">
        <Outlet />
      </main>
    </div>
  )
}
