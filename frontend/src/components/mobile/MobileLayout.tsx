/**
 * MobileLayout - 移动端 Tauri 客户端专用布局
 *
 * 特性：
 * - 底部导航栏（固定 5 个核心入口）
 * - 顶部状态栏（模式指示器 + 标题）
 * - 安全区域适配（iOS 刘海屏）
 * - 下拉刷新支持
 * - 手势返回支持
 */

import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { MobileNavBar } from './MobileNavBar'
import { ModeIndicator } from '@/components/mode-switcher/ModeIndicator'
import { isTauri } from '@/lib/tauri-bridge'

interface MobileLayoutProps {
  children: React.ReactNode
}

// 页面标题映射
const PAGE_TITLES: Record<string, string> = {
  '/chat': 'AI法务',
  '/cases': '案件管理',
  '/contracts': '合同管理',
  '/messages': '消息',
  '/settings': '设置',
  '/knowledge-base': '法律智库',
  '/due-diligence': '尽职调查',
  '/collaboration': '在线协作',
  '/find-lawyer': '找律师',
  '/tasks': '任务中心',
  '/pricing': '订阅',
}

function getPageTitle(pathname: string): string {
  // 精确匹配
  if (PAGE_TITLES[pathname]) return PAGE_TITLES[pathname]

  // 前缀匹配
  for (const [path, title] of Object.entries(PAGE_TITLES)) {
    if (pathname.startsWith(path)) return title
  }

  return '安心法务'
}

export function MobileLayout({ children }: MobileLayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const title = getPageTitle(location.pathname)
  const showBackButton = location.key !== 'default' && !['/chat', '/cases', '/messages', '/settings'].includes(location.pathname)

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* 顶部状态栏 */}
      <header
        className="flex items-center justify-between px-4 h-12 border-b border-border/50 bg-background/95 backdrop-blur-sm sticky top-0 z-30"
        style={{ paddingTop: 'env(safe-area-inset-top)' }}
      >
        <div className="flex items-center gap-2">
          {showBackButton && (
            <button
              onClick={() => navigate(-1)}
              className="p-1 -ml-1 text-muted-foreground hover:text-foreground"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
              </svg>
            </button>
          )}
          <h1 className="text-base font-semibold text-foreground">{title}</h1>
        </div>

        <div className="flex items-center gap-2">
          {isTauri() && <ModeIndicator showLabel={false} />}
        </div>
      </header>

      {/* 内容区域 */}
      <main className="flex-1 overflow-y-auto">
        {children}
      </main>

      {/* 底部导航栏 */}
      <MobileNavBar />
    </div>
  )
}
