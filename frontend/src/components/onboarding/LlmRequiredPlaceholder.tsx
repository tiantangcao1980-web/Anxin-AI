/**
 * LlmRequiredPlaceholder — 在依赖 LLM 的页面（Chat / Persona / 智能搜索）中，
 * 当用户尚未配置任何 LLM 时显示的占位界面。
 *
 * 区别于 LlmNotConfiguredBanner（横幅，软提示）：
 *   - Banner：始终在 Layout 顶部，关闭后 24h 不再提示
 *   - Placeholder：阻断主功能页（chat 输入框等），强引导到 /private-llm
 *
 * 关联：docs/plans/2026-05-22-desktop-bootstrap.md §4.3
 */

import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'

interface LlmRequiredPlaceholderProps {
  /** 标题，默认"需要先配置 AI 模型" */
  title?: string
  /** 说明文案，默认提示去 /private-llm 配置 */
  description?: string
  /** CTA 按钮文案 */
  ctaLabel?: string
  /** 跳转路径，默认 /private-llm */
  ctaHref?: string
  /** 触发场景标识（用于 a11y / 埋点） */
  feature?: string
}

export function LlmRequiredPlaceholder({
  title = '需要先配置 AI 模型',
  description = '安心智能助手不绑定特定模型 — 你可以使用 OpenAI / Anthropic / 通义 / DeepSeek / 混元 等远程 provider，或本地 Ollama / LMStudio。配置完成后即可使用智能对话与工作台。',
  ctaLabel = '去配置模型',
  ctaHref = '/private-llm',
  feature,
}: LlmRequiredPlaceholderProps = {}) {
  const navigate = useNavigate()

  return (
    <div
      role="region"
      aria-label={feature ? `${feature}：需要先配置 AI 模型` : '需要先配置 AI 模型'}
      className="flex flex-col items-center justify-center h-full w-full px-6 py-12 bg-surface-2"
    >
      <div className="max-w-md w-full bg-surface-1 border border-border rounded-xl p-8 text-center shadow-card">
        <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mx-auto mb-5">
          <icons.Sparkles className="w-7 h-7 text-primary" />
        </div>
        <h2 className="text-lg font-medium text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground mt-3 leading-relaxed">{description}</p>

        <div className="mt-6 flex flex-col gap-2">
          <button
            type="button"
            onClick={() => navigate(ctaHref)}
            className="w-full h-10 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary-600 transition-colors flex items-center justify-center gap-2"
          >
            {ctaLabel}
            <icons.ArrowRight className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => navigate('/settings')}
            className="w-full h-10 rounded-md text-sm text-muted-foreground hover:bg-surface-2 transition-colors"
          >
            进入设置
          </button>
        </div>

        <p className="mt-6 text-xs text-muted-foreground">
          已配置模型？尝试
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="ml-1 underline text-primary hover:text-primary-600"
          >
            刷新页面
          </button>
        </p>
      </div>
    </div>
  )
}

export default LlmRequiredPlaceholder
