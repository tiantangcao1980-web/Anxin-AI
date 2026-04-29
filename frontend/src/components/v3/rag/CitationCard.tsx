/**
 * CitationCard — 引文卡片（V3 P13-D，DeepTutor 风格）
 *
 * 显示一条 VLM 答案的引用：
 *   - 顶部：modality badge + score
 *   - 主体：snippet（高亮关键词）
 *   - footer：layout_path + 跳转图标
 *
 * 点击 → onClick(segmentId) 跳到 segment 原位（library 选中态 + 高亮）。
 */

import { ArrowUpRight } from 'lucide-react'

import { Badge } from '@/components/ui/badge'

import type { Citation } from '@/lib/api/rag'
import { modalityVisual } from './modalityStyle'

export interface CitationCardProps {
  citation: Citation
  index: number
  onClick?: (segmentId: string, docId: string) => void
}

export function CitationCard({ citation, index, onClick }: CitationCardProps) {
  const v = modalityVisual(citation.modality)
  return (
    <button
      type="button"
      onClick={() => onClick?.(citation.segment_id, citation.doc_id)}
      className={`group flex w-full flex-col items-stretch gap-1.5 rounded-2xl border ${v.border} ${v.bg} p-3 text-left transition-all hover:-translate-y-0.5 hover:shadow-card`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="flex h-5 w-5 items-center justify-center rounded-full bg-primary text-[10px] font-bold text-primary-foreground">
            {index + 1}
          </span>
          <Badge
            variant="outline"
            className={`flex items-center gap-1 ${v.text} ${v.border} bg-background/60 text-[10px]`}
          >
            <span aria-hidden>{v.emoji}</span>
            {v.label}
          </Badge>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-primary">
            {citation.score.toFixed(2)}
          </span>
          <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
      </div>
      <p className={`line-clamp-3 text-xs leading-relaxed ${v.text}`}>{citation.snippet}</p>
      <div className="flex items-center justify-between text-[10px] text-muted-foreground">
        <span className="truncate">
          {citation.layout_path ?? '—'}
        </span>
        {citation.bbox && (
          <span className="shrink-0 tabular-nums">
            p.{citation.bbox.page}
          </span>
        )}
      </div>
    </button>
  )
}

export default CitationCard
