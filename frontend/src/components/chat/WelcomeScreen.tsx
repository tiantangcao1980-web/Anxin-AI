/**
 * 欢迎页组件
 *
 * Chat.tsx renderMessage 中提取的欢迎页渲染。
 * 品牌问候 + 能力简介。
 */

import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { heading } from '@/lib/design-tokens'

export function WelcomeScreen() {
  return (
    <motion.div
      data-chat-welcome
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="mx-auto flex min-h-[42vh] w-full max-w-xl flex-col items-center justify-start px-5 pt-8 text-center sm:min-h-[50vh] sm:justify-center sm:pt-0"
    >
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/80 to-primary shadow-lg shadow-primary/20">
        <icons.Scale className="w-8 h-8 text-white" />
      </div>
      <h1 className={`${heading.page} mt-4`}>你好，有什么可以帮您？</h1>
      <p className="mt-3 max-w-md text-sm leading-relaxed text-muted-foreground">
        我是安心 AI 法务助手，您可以直接在下方输入问题，
        <br className="hidden sm:block" />
        或使用底部工具栏选择具体服务。我可以帮您：
      </p>
      <div className="mt-5 rounded-2xl border border-border/70 bg-surface-1/80 px-5 py-4 text-sm leading-loose text-muted-foreground/80 shadow-card">
        审查合同条款与风险 · 起草法律文书与函件
        <br />
        合规检查与尽职调查 · 检索法规与裁判案例
        <br />
        梳理证据链 · 拆解法务任务 · 推荐律师
      </div>
    </motion.div>
  )
}
