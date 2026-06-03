/**
 * DomainHomePage — 8 大业务域永久索引页 (/domains)
 *
 * V3 · Editorial Luxury · Reset 版本：
 *   - 编辑部目录式 4+8 双栏（非 4×2 卡片墙）
 *   - 左栏：8 业务域 serif 名录 + 序号 01–08
 *   - 右栏：当前选中域的「常用模块」入口列（lucide 图标 + 衬线名 + caption）
 *   - 单色调（暖灰阶 + 单一品牌琥珀橙仅用于 active 项 1px 左线 + 主 CTA）
 *   - 无 8 域高饱和拼盘、无 emoji
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { icons } from '@/lib/icons'

import { DOMAINS, type DomainId } from '@/lib/domains'

interface ModuleEntry {
  path: string
  label: string
  caption: string
}

/**
 * 每个业务域的「常用模块」入口列表。
 * legal 当前有真实路由；其它域 V3 P17-* 后续实装，先用 /chat 由 AI 引导。
 */
const DOMAIN_MODULES: Record<DomainId, ModuleEntry[]> = {
  legal: [
    { path: '/case-center',    label: '案件中心', caption: '案件全生命周期 · 团队协作' },
    { path: '/management',     label: '合同审查', caption: '条款风险 · 三档分级提示' },
    { path: '/find-lawyer',    label: '律师精英', caption: '匿名咨询 · 推荐匹配' },
    { path: '/knowledge-base', label: '知识库',   caption: '法规 · 判例 · 文书模板' },
    { path: '/agent-approvals',label: 'AI 审批',  caption: '审批工作流' },
    { path: '/documents',      label: '智能文档', caption: 'AI 起草 · 模板库' },
  ],
  finance:    [{ path: '/chat', label: '财务对话', caption: '让 AI 引导你（V3 模块上线中）' }],
  tax:        [{ path: '/chat', label: '税务对话', caption: '让 AI 引导你（V3 模块上线中）' }],
  compliance: [
    { path: '/compliance-check', label: '合规自检', caption: '企业风控点核查清单' },
    { path: '/agent-approvals',  label: 'AI 审批',  caption: '审批工作流' },
  ],
  operations: [{ path: '/dashboard', label: '驾驶舱', caption: 'KPI · 决策可视化（V3 模块上线中）' }],
  growth: [
    { path: '/investigation', label: '尽职调查', caption: '企业 / 主体 / 关联方全维度' },
    { path: '/monitoring',    label: '舆情监测', caption: '事件 · 关键词跟踪' },
  ],
  content: [
    { path: '/documents', label: '智能文档', caption: 'AI 起草 · 模板库' },
    { path: '/chat',      label: '内容对话', caption: '让 AI 引导你（V3 模块上线中）' },
  ],
  global: [{ path: '/chat', label: '出海对话', caption: '让 AI 引导你（V3 模块上线中）' }],
}

export default function DomainHomePage() {
  const [activeId, setActiveId] = useState<DomainId>('legal')
  const activeDomain = DOMAINS.find((d) => d.id === activeId) ?? DOMAINS[0]
  const modules = DOMAIN_MODULES[activeId]

  return (
    <div className="max-w-[1400px] mx-auto px-8 lg:px-16 xl:px-24 py-12 lg:py-20">

      {/* 顶部 masthead */}
      <header className="pb-10 mb-12 border-b border-border flex items-end justify-between">
        <div>
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-3">
            Index · 业务域目录
          </div>
          <h1 className="font-serif text-[48px] leading-[1.1] tracking-[-0.04em] font-medium text-foreground">
            业务域
          </h1>
          <p className="text-[15px] leading-[1.65] text-foreground/80 mt-4 max-w-[40ch]">
            选择一个领域开始 — 或继续上次进入的工作流。
          </p>
        </div>
        <div className="hidden lg:flex items-center gap-6 text-[13px] text-muted-foreground">
          <span className="text-[11px] font-medium uppercase tracking-[0.16em]">
            {new Date().toISOString().slice(0, 10).replace(/-/g, ' / ')}
          </span>
          <span className="font-serif italic">第 28 卷</span>
        </div>
      </header>

      {/* 4+8 双栏 */}
      <div className="grid grid-cols-12 gap-12">

        {/* 左栏：8 业务域目录 */}
        <nav className="col-span-12 lg:col-span-4" aria-label="业务域目录">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-6">
            Domains · 八大领域
          </div>
          <ol className="space-y-px">
            {DOMAINS.map((d, i) => {
              const isActive = d.id === activeId
              return (
                <li key={d.id}>
                  <button
                    type="button"
                    onClick={() => setActiveId(d.id)}
                    aria-current={isActive ? 'page' : undefined}
                    className={`relative group flex items-baseline gap-4 py-4 w-full text-left border-b border-border/60 transition-colors -mx-3 px-3 ${
                      isActive
                        ? 'bg-primary-50 text-foreground'
                        : 'text-foreground/70 hover:bg-surface-2/60 hover:text-foreground'
                    }`}
                  >
                    {isActive ? (
                      <span aria-hidden className="absolute left-0 top-2 bottom-2 w-0.5 bg-primary" />
                    ) : null}
                    <span className={`font-serif text-[22px] tracking-tight w-10 shrink-0 ${isActive ? 'text-foreground' : 'text-muted-foreground'}`}>
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className={`font-serif text-[20px] leading-tight ${isActive ? 'text-foreground' : 'text-foreground/85'}`}>
                        {d.label}
                      </div>
                      <div className="text-[13px] text-muted-foreground mt-1">{d.tagline}</div>
                    </div>
                    <icons.ArrowRight className={`w-4 h-4 stroke-[1.5] transition-all ${
                      isActive ? 'text-foreground' : 'text-muted-foreground opacity-0 group-hover:opacity-100'
                    }`} aria-hidden />
                  </button>
                </li>
              )
            })}
          </ol>
        </nav>

        {/* 右栏：当前业务域子页 */}
        <article className="col-span-12 lg:col-span-8">
          <div className="lg:sticky lg:top-24">
            <div className="flex items-baseline gap-4 mb-3">
              <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                {activeDomain.labelEn} · {String(DOMAINS.findIndex((d) => d.id === activeId) + 1).padStart(2, '0')}
              </span>
              <span className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground/60">
                {modules.length} 个入口
              </span>
            </div>
            <h2 className="font-serif text-[48px] leading-[1.1] tracking-[-0.04em] font-medium text-foreground mb-4">
              {activeDomain.label}
            </h2>
            <p className="font-serif italic text-[18px] leading-[1.4] text-foreground/80 max-w-[40ch] mb-12">
              {activeDomain.tagline}
            </p>

            {/* 模块入口列表 */}
            <ol className="grid grid-cols-1 sm:grid-cols-2 gap-x-12 gap-y-px">
              {modules.map((m, i) => (
                <li key={m.path}>
                  <Link
                    to={m.path}
                    className="group flex items-start gap-4 py-5 border-b border-border/60 hover:bg-surface-2/40 -mx-3 px-3 transition-colors"
                  >
                    <span className="font-serif text-[13px] text-muted-foreground w-6 shrink-0 pt-1">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="font-serif text-[18px] leading-tight text-foreground">{m.label}</div>
                      <div className="text-[13px] text-muted-foreground mt-1">{m.caption}</div>
                    </div>
                    <icons.ArrowRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-foreground group-hover:translate-x-0.5 stroke-[1.5] transition-all mt-1.5" aria-hidden />
                  </Link>
                </li>
              ))}
            </ol>

            <div className="mt-12 pt-8 border-t border-border flex items-center justify-between">
              <Link
                to="/chat"
                className="inline-flex items-center gap-2 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground hover:text-foreground transition-colors"
              >
                <span>所有模块 / AI 引导</span>
                <icons.ArrowUpRight className="w-3 h-3 stroke-[1.5]" />
              </Link>
              <Link
                to={activeDomain.defaultPath}
                className="inline-flex items-center gap-2 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
              >
                <span>进入 {activeDomain.label}</span>
                <icons.ArrowRight className="w-4 h-4 stroke-[1.75]" />
              </Link>
            </div>
          </div>
        </article>

      </div>
    </div>
  )
}
