/**
 * 欢迎页组件
 *
 * Chat.tsx renderMessage 中提取的欢迎页渲染。
 * 品牌问候 + 能力简介。
 */

import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'

export function WelcomeScreen() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full min-h-[50vh] flex flex-col items-center justify-center mx-auto max-w-lg px-4"
    >
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary/80 to-primary flex items-center justify-center shadow-lg shadow-primary/20">
        <icons.Scale className="w-8 h-8 text-white" />
      </div>
      <h1 className="text-2xl font-bold text-foreground tracking-tight mt-4">你好，有什么可以帮您？</h1>
      <p className="text-sm text-muted-foreground mt-3 text-center leading-relaxed">
        我是安心 AI 法务助手，您可以直接在下方输入问题，
        <br className="hidden sm:block" />
        或使用底部工具栏选择具体服务。我可以帮您：
      </p>
      <div className="mt-4 text-sm text-muted-foreground/80 text-center leading-loose">
        审查合同条款与风险 · 起草法律文书与函件
        <br />
        合规检查与尽职调查 · 检索法规与裁判案例
        <br />
        梳理证据链 · 拆解法务任务 · 推荐律师
      </div>
    </motion.div>
  )
}
