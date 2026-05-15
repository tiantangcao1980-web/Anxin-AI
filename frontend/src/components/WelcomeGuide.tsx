import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'

import { icons } from '@/lib/icons'
import { heading } from '@/lib/design-tokens'
import { DomainGrid } from '@/components/ui/domain'

interface WelcomeGuideProps {
  onClose: () => void
  /** 兼容旧 API：第一版用 onSelectView(viewId) 跳转，现在 DomainGrid 自带 Link 跳转，
   *  保留参数以避免破坏调用方签名，但仅在 fallback "开始使用" 按钮上使用 */
  onSelectView?: (view: string) => void
}

/**
 * WelcomeGuide — 首次登录欢迎引导 modal (V3)
 *
 * 2026-05 升级：从 V2 时代的 6 大功能模块（智能对话 / 案件管理 / 司法学院 ...）
 * 改造为 V3 8 大业务域 DomainGrid，与 Login 页跨端视觉对齐。
 *
 * 设计哲学：
 * - 不再列举"功能"（V2 视角），而是列举"业务域"（V3 视角）
 * - 每个域卡片是 Link，点击直接跳到对应入口路径（由 @/lib/domains 提供）
 * - 底部 fallback 按钮提供"先用 AI 对话试试"快速入口
 */
export function WelcomeGuide({ onClose, onSelectView }: WelcomeGuideProps) {
  const navigate = useNavigate()

  return (
    <div className="fixed inset-0 bg-black/30 backdrop-blur-md z-modal flex items-center justify-center p-6">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative bg-background rounded-3xl shadow-2xl max-w-5xl w-full max-h-[90vh] overflow-hidden"
      >
        {/* Close */}
        <button
          onClick={onClose}
          aria-label="关闭"
          className="absolute top-5 right-5 z-10 p-2 hover:bg-muted rounded-full transition-colors"
        >
          <icons.X className="w-5 h-5 text-muted-foreground" />
        </button>

        {/* Header */}
        <div className="px-8 py-6 border-b border-border flex items-center gap-4">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.1, type: 'spring', stiffness: 200 }}
            className="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center shadow-md flex-shrink-0"
          >
            <icons.Sparkles className="w-7 h-7 text-primary-foreground" />
          </motion.div>
          <div className="flex-1">
            <h1 className={heading.page}>欢迎使用安心智能助手</h1>
            <p className="text-muted-foreground text-sm mt-0.5">
              全链路 AI 经营助理 · 一个 App 搞定企业 8 大业务
            </p>
          </div>
        </div>

        {/* 8 大业务域 grid（DomainCard 自带跳转） */}
        <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
          <DomainGrid
            className="mb-5"
            meta={{
              // 给"AI 智能助手"对应的「经营管理」域加 "推荐" 徽章作为默认入口提示
              operations: { badge: '推荐入口' },
            }}
          />

          {/* 快速开始 fallback */}
          <div className="bg-muted rounded-2xl p-4 lg:p-5">
            <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3">
              <div>
                <h3 className="font-medium text-foreground mb-1 lg:mb-1.5 text-sm lg:text-base">
                  不确定从哪里开始？
                </h3>
                <p className="text-xs lg:text-sm text-muted-foreground">
                  直接打开 AI 智能对话，告诉它你的业务问题，它会把你引导到合适的业务域。
                </p>
              </div>
              <button
                onClick={() => {
                  if (onSelectView) onSelectView('chat')
                  navigate('/chat')
                  onClose()
                }}
                className="w-full lg:w-auto px-5 lg:px-6 py-2.5 lg:py-3 bg-primary text-primary-foreground rounded-xl hover:bg-primary/90 active:scale-95 transition-[background-color,transform] flex items-center justify-center gap-2 font-medium shadow-sm text-sm"
              >
                打开 AI 对话
                <icons.ArrowRight className="w-4 h-4 lg:w-5 lg:h-5" />
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  )
}
