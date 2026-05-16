/**
 * DomainHomePage — V3 8 大业务域永久索引页（路径 `/domains`）
 *
 * 不同于 WelcomeGuide（首登一次性弹出 modal），本页是永久路由，用户随时可访问
 * 全局业务域视图：
 *   - 顶部 8 大业务域 DomainGrid（点击域卡片直接跳入口路径）
 *   - 中部按域分组展示常用子页（与 Layout ModuleSidebar item.domain 对齐）
 *   - 底部品牌定位（V3「全链路 AI 经营助理」+ 制造业场景）
 *
 * 入口路径建议（由 Layout / 顶部 nav 决定）：
 *   - `/domains` ← 本页
 *   - Layout 顶部 logo 或用户菜单的"全局业务域"链接（follow-up）
 */

import { Link } from 'react-router-dom'

import { heading } from '@/lib/design-tokens'
import { DOMAINS, type DomainId } from '@/lib/domains'
import { DomainGrid } from '@/components/ui/domain'
import { PageContainer } from '@/components/ui/PageContainer'

// 与 Layout.tsx moduleSidebarConfig 对齐的"域 → 子页"映射（用于本页下方分组展示）
// 修改必须同步 frontend/src/components/Layout.tsx 中的 item.domain 字段
const DOMAIN_SHORTCUTS: Record<DomainId, Array<{ label: string; path: string }>> = {
  legal: [
    { label: '案件中心', path: '/case-center' },
    { label: '管理中心', path: '/management' },
    { label: '律师精英', path: '/find-lawyer' },
    { label: '知识库', path: '/knowledge-base' },
    { label: '知识图谱', path: '/knowledge-graph' },
  ],
  finance: [],
  tax: [],
  compliance: [{ label: 'AI 审批', path: '/agent-approvals' }],
  operations: [{ label: 'AI 对话', path: '/chat' }],
  growth: [
    { label: '尽职调查', path: '/investigation' },
    { label: '舆情监测', path: '/monitoring' },
  ],
  content: [{ label: '智能文档', path: '/documents' }],
  global: [],
}

export default function DomainHomePage() {
  return (
    <PageContainer
      title="8 大业务一站式"
      description="安心智能助手 V3 · 全链路 AI 经营助理"
    >
      {/* 8 域 DomainGrid — 每张卡片是 Link，点击跳到对应入口 */}
      <section className="mb-8">
        <DomainGrid />
      </section>

      {/* 按域分组的常用子页 */}
      <section className="space-y-6">
        <h2 className={`${heading.section} mb-4`}>常用模块</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {DOMAINS.map((d) => {
            const shortcuts = DOMAIN_SHORTCUTS[d.id]
            if (shortcuts.length === 0) {
              // 暂无入口的业务域 — 用占位卡片提示"敬请期待"
              return (
                <div
                  key={d.id}
                  className="rounded-2xl border border-border/40 bg-card p-4 opacity-60"
                  data-domain={d.id}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      aria-hidden
                      className="h-2 w-2 rounded-full"
                      style={{ backgroundColor: `hsl(var(--${d.cssVar}))` }}
                    />
                    <span className={`text-sm font-medium ${d.colorClass}`}>
                      {d.label}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">敬请期待</p>
                </div>
              )
            }
            return (
              <div
                key={d.id}
                className="rounded-2xl border border-border/40 bg-card p-4 transition-colors hover:border-border-strong"
                data-domain={d.id}
              >
                <div className="flex items-center gap-2 mb-3">
                  <span
                    aria-hidden
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: `hsl(var(--${d.cssVar}))` }}
                  />
                  <span className={`text-sm font-medium ${d.colorClass}`}>
                    {d.label}
                  </span>
                </div>
                <ul className="space-y-1">
                  {shortcuts.map((s) => (
                    <li key={s.path}>
                      <Link
                        to={s.path}
                        className="text-sm text-foreground/80 hover:text-primary transition-colors block py-0.5"
                      >
                        {s.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )
          })}
        </div>
      </section>

      {/* 品牌定位 */}
      <section className="mt-12 text-center text-xs text-muted-foreground/60">
        安心智能助手 · 法务 · 财务 · 税务 · 合规 · 经营 · 获客 · 内容 · 出海
      </section>
    </PageContainer>
  )
}
