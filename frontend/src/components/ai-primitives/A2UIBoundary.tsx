import type { ReactNode } from 'react'
import { icons } from '@/lib/icons'
import { cn } from '@/lib/utils'

type BoundaryTone = 'ai' | 'neutral' | 'suggestion'

interface A2UIBoundaryProps {
  children: ReactNode
  title?: string
  tone?: BoundaryTone
  streaming?: boolean
  footer?: ReactNode
  className?: string
  dense?: boolean
}

const TONE_CLS: Record<BoundaryTone, { border: string; surface: string; accent: string }> = {
  ai: {
    border: 'border-ai/20',
    surface: 'bg-ai-thinking-surface/50',
    accent: 'text-ai',
  },
  neutral: {
    border: 'border-border',
    surface: 'bg-surface-2',
    accent: 'text-foreground-tertiary',
  },
  suggestion: {
    border: 'border-ai-suggestion/25',
    surface: 'bg-ai-suggestion-surface/60',
    accent: 'text-ai-suggestion',
  },
}

/**
 * A2UIBoundary — 为后端下发的动态 UI 组件提供标准化外壳。
 *
 * 强制约束：
 * - 统一圆角 (rounded-dd_lg) 与阴影 (shadow-elev-2)
 * - 统一内边距节奏（dense 模式给表格/列表用）
 * - AI tone 场景自动展示来源标识，避免动态组件"无主"
 * - 流式生成中展示柔和脉冲，替代 spinner
 */
export function A2UIBoundary({
  children,
  title,
  tone = 'ai',
  streaming = false,
  footer,
  className,
  dense = false,
}: A2UIBoundaryProps) {
  const toneCls = TONE_CLS[tone]

  return (
    <section
      className={cn(
        'group/a2ui overflow-hidden rounded-dd_lg border',
        toneCls.border,
        toneCls.surface,
        'shadow-elev-2 transition-shadow duration-normal ease-standard',
        'hover:shadow-elev-3',
        streaming && 'ring-1 ring-ai/20',
        className,
      )}
      data-a2ui-tone={tone}
      data-a2ui-streaming={streaming || undefined}
    >
      {(title || tone === 'ai') && (
        <header
          className={cn(
            'flex items-center gap-2 border-b border-border-subtle/70 bg-background/40 px-4 py-2',
            'backdrop-blur-sm',
          )}
        >
          <icons.Sparkles
            className={cn(
              'size-3.5',
              toneCls.accent,
              streaming && 'animate-ai-pulse',
            )}
          />
          <span className="text-caption font-medium text-foreground">
            {title ?? (tone === 'ai' ? 'AI 生成内容' : '动态模块')}
          </span>
          {streaming && (
            <span className="ml-auto flex items-center gap-1 text-[11px] text-ai-thinking">
              <span className="size-1 rounded-pill bg-ai-thinking animate-ai-thinking-dot [animation-delay:-0.3s]" />
              <span className="size-1 rounded-pill bg-ai-thinking animate-ai-thinking-dot [animation-delay:-0.15s]" />
              <span className="size-1 rounded-pill bg-ai-thinking animate-ai-thinking-dot" />
            </span>
          )}
        </header>
      )}

      <div className={cn(dense ? 'p-2' : 'p-4')}>{children}</div>

      {footer && (
        <footer
          className={cn(
            'border-t border-border-subtle/70 bg-background/30 px-4 py-2',
            'text-caption text-foreground-tertiary',
          )}
        >
          {footer}
        </footer>
      )}
    </section>
  )
}
