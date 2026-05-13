/**
 * IngestPage — 多模态文档上传 + 解析进度（V3 P13-D）
 *
 * 路由：/v3/rag/ingest
 *
 * 内容：
 *   - 顶部：返回 dashboard
 *   - 主体：IngestUploader（拖拽 + 进度列表）
 *   - 右侧（lg+）：刚刚解析完成的 segments 预览（取 latest task 的 segments）
 */

import { useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { Button } from '@/components/ui/button'

import { IngestUploader } from '@/components/v3/rag/IngestUploader'
import { SegmentPreview } from '@/components/v3/rag/SegmentPreview'

import { useRagStore } from '@/lib/store/ragStore'

export default function IngestPage() {
  const navigate = useNavigate()

  const ingestTasks = useRagStore((s) => s.ingestTasks)
  const stopAllPolling = useRagStore((s) => s.stopAllPolling)

  // 离开页面时停止所有 polling，避免泄露
  useEffect(() => () => stopAllPolling(), [stopAllPolling])

  const latestSegments = useMemo(() => {
    const tasks = Object.values(ingestTasks).sort((a, b) => b.created_at.localeCompare(a.created_at))
    return tasks[0]?.segments ?? []
  }, [ingestTasks])

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-5 p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/v3/rag')}
            iconLeft={<icons.ArrowLeft className="h-4 w-4" />}
            className="h-8"
          >
            返回看板
          </Button>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <icons.FileUp className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">多模态上传</h1>
              <p className="mt-0.5 max-w-xl text-xs text-muted-foreground">
                Layout 解析 → 章/条/款/项 → 5 模态 segment → embedding。整个 pipeline 由 P13-A/B/C 后端实现。
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        {/* 主面板 */}
        <section>
          <IngestUploader />
        </section>

        {/* 右侧：最近 segments */}
        <aside className="rounded-3xl border border-border/40 bg-surface-1 p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-medium text-foreground">最近 segments</p>
            <span className="text-[11px] tabular-nums text-muted-foreground">
              {latestSegments.length}
            </span>
          </div>
          {latestSegments.length === 0 ? (
            <p className="rounded-xl border border-dashed border-border/60 bg-background p-4 text-center text-[11px] text-muted-foreground">
              上传文档后，本面板将实时显示已识别的多模态 segments。
            </p>
          ) : (
            <div className="space-y-2">
              {latestSegments.slice(0, 8).map((seg) => (
                <SegmentPreview key={seg.segment_id} segment={seg} compact />
              ))}
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
