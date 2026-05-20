/**
 * MarketingLayout —— 公开官网布局（无需登录）
 *
 * 顶部导航（产品 / 角色 / 价格 / 安全 / 关于 / 登录）+ 内容插槽 + 页脚。
 * 使用现有 design-tokens，避免新颜色或新尺寸常量。
 */

import { Outlet, NavLink, Link, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { icons } from '@/lib/icons'
import { iconSize } from '@/lib/design-tokens'
import { Button } from '@/components/ui/button'

const NAV_ITEMS: { to: string; label: string }[] = [
  { to: '/site', label: '首页' },
  { to: '/site/features', label: '产品功能' },
  { to: '/site/personas', label: '角色矩阵' },
  { to: '/site/cases', label: '客户案例' },
  { to: '/site/pricing', label: '价格' },
  { to: '/site/security', label: '安全与合规' },
  { to: '/site/blog', label: '博客' },
  { to: '/site/about', label: '关于' },
  { to: '/site/contact', label: '联系我们' },
]

export function MarketingLayout() {
  const { pathname } = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  // 路由切换时滚到顶部 + 关菜单
  useEffect(() => {
    window.scrollTo({ top: 0 })
    setMobileOpen(false)
  }, [pathname])

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-30 bg-background/85 backdrop-blur border-b border-border">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 h-14 flex items-center justify-between">
          <Link to="/site" className="flex items-center gap-2 font-semibold">
            <icons.Sparkles className={iconSize.md} />
            <span>安心智能助手</span>
          </Link>

          <nav className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.slice(1).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end
                className={({ isActive }) =>
                  `px-3 py-1.5 text-sm rounded-lg transition-colors ${
                    isActive
                      ? 'text-foreground bg-muted'
                      : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-2">
            <Link to="/login">
              <Button variant="ghost" size="sm">登录</Button>
            </Link>
            <Link to="/site/contact">
              <Button size="sm">申请试用</Button>
            </Link>
          </div>

          <button
            className="md:hidden p-2 rounded-lg hover:bg-muted text-muted-foreground"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label="切换菜单"
          >
            {mobileOpen ? <icons.X className={iconSize.md} /> : <icons.Menu className={iconSize.md} />}
          </button>
        </div>

        {mobileOpen && (
          <div className="md:hidden border-t border-border">
            <div className="mx-auto max-w-6xl px-4 py-3 flex flex-col gap-1">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end
                  className={({ isActive }) =>
                    `px-3 py-2 text-sm rounded-lg ${
                      isActive ? 'text-foreground bg-muted' : 'text-muted-foreground'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
              <div className="flex gap-2 mt-2">
                <Link to="/login" className="flex-1">
                  <Button variant="outline" size="sm" className="w-full">登录</Button>
                </Link>
                <Link to="/site/contact" className="flex-1">
                  <Button size="sm" className="w-full">申请试用</Button>
                </Link>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* 内容区 */}
      <main className="flex-1">
        <Outlet />
      </main>

      {/* 页脚 */}
      <footer className="border-t border-border bg-muted/30">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 py-10 grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
          <div>
            <div className="flex items-center gap-2 font-semibold mb-3">
              <icons.Sparkles className={iconSize.sm} />
              安心智能助手
            </div>
            <p className="text-muted-foreground">
              覆盖法务 / 财税 / 合规 / 营销 / 出海全链路的企业级 AI 助手。
            </p>
          </div>
          <div>
            <div className="font-medium mb-3">产品</div>
            <ul className="space-y-2 text-muted-foreground">
              <li><Link to="/site/features" className="hover:text-foreground">功能</Link></li>
              <li><Link to="/site/personas" className="hover:text-foreground">10 个 Persona</Link></li>
              <li><Link to="/site/cases" className="hover:text-foreground">客户案例</Link></li>
              <li><Link to="/site/pricing" className="hover:text-foreground">价格</Link></li>
              <li><Link to="/site/blog" className="hover:text-foreground">博客</Link></li>
            </ul>
          </div>
          <div>
            <div className="font-medium mb-3">企业</div>
            <ul className="space-y-2 text-muted-foreground">
              <li><Link to="/site/security" className="hover:text-foreground">安全与合规</Link></li>
              <li><Link to="/site/about" className="hover:text-foreground">关于我们</Link></li>
              <li><Link to="/site/contact" className="hover:text-foreground">商务合作</Link></li>
            </ul>
          </div>
          <div>
            <div className="font-medium mb-3">法律</div>
            <ul className="space-y-2 text-muted-foreground">
              <li><Link to="/site/privacy" className="hover:text-foreground">隐私政策</Link></li>
              <li><Link to="/site/terms" className="hover:text-foreground">服务条款</Link></li>
              <li><Link to="/site/contact" className="hover:text-foreground">DSAR 数据主体请求</Link></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-border">
          <div className="mx-auto max-w-6xl px-4 sm:px-6 py-4 text-xs text-muted-foreground flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <span>© {new Date().getFullYear()} 安心智能助手 / Anxin AI · 保留所有权利</span>
            <span>ICP 备案号待补 · 数据按 GB/T 35273-2020 分级</span>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default MarketingLayout
