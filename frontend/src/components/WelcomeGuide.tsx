import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, X } from 'lucide-react'

import { DOMAINS } from '@/lib/domains'

interface WelcomeGuideProps {
  onClose: () => void
  /** 兼容旧 API */
  onSelectView?: (view: string) => void
}

/**
 * WelcomeGuide — 首次登录欢迎引导 (V3 · Editorial Luxury · Reset)
 *
 * 2026-05 Reset 说明：
 *   原版用 DomainGrid 渲染 8 张高饱和卡片 + 大幅域色 surface 底色，
 *   违反 ui-design skill 与 DESIGN.md §1 哲学，已重写为：
 *     - 编辑部目录式（serif Display 标题 + 8 行域名录 + 单 CTA）
 *     - 单一品牌琥珀橙仅出现在 CTA 按钮
 *     - 域名用衬线字体（Noto Serif SC）
 *     - 序号 01–08 标号
 */
export function WelcomeGuide({ onClose, onSelectView }: WelcomeGuideProps) {
  const navigate = useNavigate()

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-md z-modal flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative bg-background max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-border shadow-elev-4"
      >
        {/* Close */}
        <button
          onClick={onClose}
          aria-label="关闭"
          className="absolute top-5 right-5 z-10 p-2 hover:bg-surface-2 transition-colors"
        >
          <X className="w-5 h-5 text-muted-foreground stroke-[1.5]" />
        </button>

        {/* Header */}
        <header className="px-10 py-10 border-b border-border">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-3">
            Welcome · 欢迎使用
          </div>
          <h1 className="font-serif text-[40px] leading-[1.1] tracking-[-0.04em] font-medium text-foreground">
            安心智能助手
          </h1>
          <p className="font-serif italic text-[18px] leading-[1.4] text-foreground/80 mt-3 max-w-[40ch]">
            全链路 AI 经营助理 — 一个 App 搞定企业 8 大业务。
          </p>
        </header>

        {/* 8 行编辑部目录 */}
        <div className="px-10 py-8">
          <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground mb-4">
            Domains · 选择一个领域开始
          </div>
          <ol className="grid grid-cols-1 sm:grid-cols-2 gap-x-12 gap-y-px">
            {DOMAINS.map((d, i) => (
              <li key={d.id}>
                <button
                  type="button"
                  onClick={() => {
                    navigate(d.defaultPath)
                    if (onSelectView) onSelectView(d.id)
                    onClose()
                  }}
                  className="group flex items-baseline gap-4 py-4 w-full text-left border-b border-border/60 hover:bg-surface-2/40 -mx-3 px-3 transition-colors"
                >
                  <span className="font-serif text-[22px] tracking-tight text-muted-foreground w-10 shrink-0">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="font-serif text-[20px] leading-tight text-foreground">{d.label}</div>
                    <div className="text-[13px] text-muted-foreground mt-1">{d.tagline}</div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-foreground group-hover:translate-x-0.5 transition-all stroke-[1.5]" aria-hidden />
                </button>
              </li>
            ))}
          </ol>
        </div>

        {/* Footer CTA */}
        <footer className="px-10 py-6 border-t border-border bg-surface-2/30 flex items-center justify-between gap-4">
          <div className="text-[13px] text-muted-foreground leading-relaxed">
            不确定从哪里开始？
            <span className="font-serif italic text-foreground/80"> 让 AI 引导你 — </span>
            它会根据你的问题决定该走哪条流程。
          </div>
          <button
            onClick={() => {
              if (onSelectView) onSelectView('chat')
              navigate('/chat')
              onClose()
            }}
            className="shrink-0 inline-flex items-center gap-2 bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium tracking-wide transition-colors"
          >
            <span>打开 AI 对话</span>
            <ArrowRight className="w-4 h-4 stroke-[1.75]" />
          </button>
        </footer>
      </motion.div>
    </div>
  )
}
