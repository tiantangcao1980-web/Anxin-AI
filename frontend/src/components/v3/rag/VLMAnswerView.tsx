/**
 * VLMAnswerView — VLM 答案 + visual grounding 高亮（V3 P13-D）
 *
 * 视觉布局：
 *   - 上：答案 markdown（用 prose）
 *   - 中：visual grounding 矩形列表（每条：segment 缩略图 + bbox 矩形 + label）
 *   - 下：modality_scores 横向条形（5 个模态各自一条）
 *   - 右上：latency / used_weights 摘要
 *
 * 注意：本组件只渲染答案对象，不依赖 store。
 */

import { icons } from '@/lib/icons'
import type { Modality, VLMQueryResponse } from '@/lib/api/rag'
import { MODALITIES, modalityVisual } from './modalityStyle'

export interface VLMAnswerViewProps {
  answer: VLMQueryResponse | null
  loading?: boolean
  error?: string | null
}

export function VLMAnswerView({ answer, loading, error }: VLMAnswerViewProps) {
  if (loading) {
    return (
      <div className="flex h-full min-h-[240px] items-center justify-center rounded-2xl border border-border/40 bg-surface-1">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <icons.Loader2 className="h-4 w-4 animate-spin" /> VLM 正在多模态推理…
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
        查询失败：{error}
      </div>
    )
  }

  if (!answer) {
    return (
      <div className="rounded-2xl border border-border/40 bg-surface-1 p-6 text-center text-sm text-muted-foreground">
        在右侧输入问题并点「检索」即可获得 VLM 多模态答案。
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 顶部 meta */}
      <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
        <span className="rounded-full bg-primary/10 px-2 py-0.5 font-medium text-primary">
          已用模态权重
        </span>
        {MODALITIES.map((m) => {
          const v = modalityVisual(m)
          return (
            <span
              key={m}
              className="flex items-center gap-1 rounded-full border border-border/60 bg-background px-2 py-0.5"
            >
              <span aria-hidden>{v.emoji}</span>
              <span className={v.text}>{v.label}</span>
              <span className="tabular-nums text-foreground/80">
                {answer.used_weights[m].toFixed(2)}
              </span>
            </span>
          )
        })}
        <span className="ml-auto tabular-nums text-foreground/70">
          延迟 {answer.latency_ms} ms
        </span>
      </div>

      {/* 答案正文（简化 markdown：换行 + bold） */}
      <article className="rounded-2xl border border-border/40 bg-surface-1 p-4">
        <p className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">答案</p>
        <div className="space-y-2 text-sm leading-relaxed text-foreground/90">
          {answer.answer.split(/\n\n+/).map((para, i) => (
            <p key={i} className="whitespace-pre-wrap">
              {para.replace(/\*\*(.+?)\*\*/g, '$1')}
            </p>
          ))}
        </div>
      </article>

      {/* Visual grounding */}
      {answer.groundings.length > 0 && (
        <section className="rounded-2xl border border-border/40 bg-surface-1 p-4">
          <p className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">
            Visual Grounding（定位高亮）
          </p>
          <ul className="grid grid-cols-2 gap-2.5">
            {answer.groundings.map((g, i) => (
              <li
                key={`${g.segment_id}-${i}`}
                className="rounded-xl border border-border/40 bg-background p-2"
              >
                {/* 用 SVG 模拟 page 上的 bbox 矩形 */}
                <div className="relative aspect-[3/4] w-full overflow-hidden rounded-lg bg-gradient-to-br from-slate-100 to-slate-50 dark:from-slate-800 dark:to-slate-900">
                  <svg
                    viewBox="0 0 100 100"
                    className="absolute inset-0 h-full w-full"
                    preserveAspectRatio="none"
                  >
                    <rect width="100" height="100" fill="transparent" />
                    <rect
                      x={(g.bbox.x * 100).toFixed(2)}
                      y={(g.bbox.y * 100).toFixed(2)}
                      width={(g.bbox.w * 100).toFixed(2)}
                      height={(g.bbox.h * 100).toFixed(2)}
                      fill="rgba(245,158,11,0.18)"
                      stroke="#f59e0b"
                      strokeWidth="0.6"
                      strokeDasharray="2 1"
                    />
                  </svg>
                  <span className="absolute left-1.5 top-1.5 rounded bg-amber-500/90 px-1.5 py-0.5 text-[9px] font-semibold text-white">
                    p.{g.bbox.page}
                  </span>
                </div>
                <p className="mt-1.5 line-clamp-1 text-[11px] text-foreground/80" title={g.label}>
                  {g.label}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* modality scores 直方图 */}
      <section className="rounded-2xl border border-border/40 bg-surface-1 p-4">
        <p className="mb-2 text-[11px] uppercase tracking-wider text-muted-foreground">
          各模态命中 score
        </p>
        <div className="space-y-1.5">
          {MODALITIES.map((m) => {
            const v = modalityVisual(m)
            const score = answer.modality_scores[m] ?? 0
            return (
              <div key={m} className="flex items-center gap-2">
                <div className="flex w-16 items-center gap-1 text-[11px]">
                  <span aria-hidden>{v.emoji}</span>
                  <span className={v.text}>{v.label}</span>
                </div>
                <div className="relative h-2 flex-1 overflow-hidden rounded bg-muted">
                  <div
                    className="h-full rounded transition-[width]"
                    style={{
                      width: `${Math.max(0, Math.min(1, score)) * 100}%`,
                      background: v.color,
                    }}
                  />
                </div>
                <span className="w-10 text-right text-[11px] tabular-nums text-foreground/80">
                  {score.toFixed(2)}
                </span>
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}

export default VLMAnswerView

// 避免 import 警告
export type { Modality }
