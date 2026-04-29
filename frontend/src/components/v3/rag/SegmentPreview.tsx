/**
 * SegmentPreview — 单个 segment 的预览卡片（V3 P13-D）
 *
 * 视觉规则（按 modality 着色，参考 modalityStyle.ts）：
 *   - text   → 灰
 *   - image  → 蓝（直接显示 image_url 缩略图）
 *   - table  → 绿（content 是 markdown 表格）
 *   - formula → 紫（content 是 latex / 公式）
 *   - seal   → 红（image_url + caption + bbox 高亮提示）
 */

import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

import type { Segment } from '@/lib/api/rag'
import { modalityVisual } from './modalityStyle'

export interface SegmentPreviewProps {
  segment: Segment
  /** 是否高亮（命中 query / 选中 entity 时） */
  highlighted?: boolean
  /** 点击回调（跳转 / focus） */
  onClick?: (segmentId: string) => void
  /** 命中 score（query 视角） */
  score?: number
  /** 紧凑模式（用于侧栏） */
  compact?: boolean
}

export function SegmentPreview({ segment, highlighted, onClick, score, compact }: SegmentPreviewProps) {
  const v = modalityVisual(segment.modality)
  const isMedia = segment.modality === 'image' || segment.modality === 'seal'

  return (
    <Card
      onClick={() => onClick?.(segment.segment_id)}
      className={`group relative cursor-pointer overflow-hidden border ${v.border} ${v.bg} p-3 transition-all hover:-translate-y-0.5 hover:shadow-card ${
        highlighted ? 'ring-2 ring-primary' : ''
      }`}
    >
      {/* 顶栏：modality badge + layout_path + score */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Badge
            variant="outline"
            className={`flex items-center gap-1 ${v.text} ${v.border} bg-background/60 text-[10px] font-medium`}
          >
            <span aria-hidden>{v.emoji}</span>
            {v.label}
          </Badge>
          {segment.layout_path && (
            <span className="truncate text-[11px] text-muted-foreground" title={segment.layout_path}>
              {segment.layout_path}
            </span>
          )}
        </div>
        {typeof score === 'number' && (
          <span className="shrink-0 rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold tabular-nums text-primary">
            {score.toFixed(2)}
          </span>
        )}
      </div>

      {/* 主体内容 */}
      {isMedia && segment.image_url ? (
        <div className="space-y-1.5">
          <div className={`overflow-hidden rounded-xl border ${v.border} bg-background`}>
            <img
              src={segment.image_url}
              alt={segment.caption ?? segment.content}
              className={`block w-full ${compact ? 'h-28 object-cover' : 'max-h-48 object-contain'}`}
              loading="lazy"
            />
          </div>
          {segment.caption && (
            <p className="line-clamp-2 text-xs text-foreground/80">{segment.caption}</p>
          )}
        </div>
      ) : segment.modality === 'table' ? (
        <pre className={`whitespace-pre-wrap break-words text-[11px] leading-relaxed ${v.text} ${compact ? 'line-clamp-4' : 'line-clamp-8'}`}>
          {segment.content}
        </pre>
      ) : segment.modality === 'formula' ? (
        <div className={`rounded-lg border ${v.border} bg-background/60 p-2 font-mono text-[12px] ${v.text} ${compact ? 'line-clamp-2' : 'line-clamp-4'}`}>
          {segment.content}
        </div>
      ) : (
        <p className={`text-sm leading-relaxed ${v.text} ${compact ? 'line-clamp-2' : 'line-clamp-4'}`}>
          {segment.content}
        </p>
      )}

      {/* footer */}
      {segment.bbox && (
        <div className="mt-2 flex items-center gap-2 text-[10px] text-muted-foreground">
          <span>p.{segment.bbox.page}</span>
          <span aria-hidden>·</span>
          <span className="tabular-nums">
            bbox {segment.bbox.x.toFixed(2)}, {segment.bbox.y.toFixed(2)}, {segment.bbox.w.toFixed(2)}, {segment.bbox.h.toFixed(2)}
          </span>
        </div>
      )}
    </Card>
  )
}

export default SegmentPreview
