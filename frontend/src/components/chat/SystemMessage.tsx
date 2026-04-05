/**
 * 系统消息组件
 *
 * Chat.tsx renderMessage 中提取的系统消息渲染。
 * 居中提示条 + 错误消息带重试按钮。
 */

import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'

interface SystemMessageProps {
  content: string
  isError?: boolean
  actionable?: 'retry' | 'switch_model'
  onRetry?: () => void
  onSwitchModel?: () => void
}

export function SystemMessage({ content, isError, actionable, onRetry, onSwitchModel }: SystemMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex justify-center"
    >
      <div className={`text-[11px] mx-auto font-medium px-4 py-1.5 rounded-full flex items-center gap-2 ${
        isError
          ? 'bg-destructive/5 text-destructive border border-destructive/20'
          : 'bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
      }`}>
        <span>{content}</span>
        {isError && onRetry && (
          <button
            onClick={onRetry}
            className="ml-1 px-2 py-0.5 bg-destructive/10 hover:bg-destructive/20 text-destructive rounded-full text-[10px] font-semibold transition-colors"
          >
            重试
          </button>
        )}
        {isError && actionable === 'switch_model' && onSwitchModel && (
          <button
            onClick={onSwitchModel}
            className="ml-1 px-2 py-0.5 bg-primary/10 hover:bg-primary/20 text-primary rounded-full text-[10px] font-semibold transition-colors"
          >
            切换基础模型
          </button>
        )}
      </div>
    </motion.div>
  )
}
