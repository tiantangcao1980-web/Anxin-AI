/**
 * IngestUploader — 多模态文档拖拽上传 + 解析进度面板（V3 P13-D）
 *
 * 设计思路：
 *   - 顶部：dropzone（拖拽 / 点击选文件）。HTML5 drag 事件，无第三方依赖。
 *   - 下方：当前 ingestTasks 进度列表（每条一行：文件名 + 阶段 + Progress + segments_done/total）
 *
 * 数据流：
 *   - 调用 ragStore.enqueueIngest(file) → 自动入队 + 启动后台轮询。
 */

import { useCallback, useRef, useState } from 'react'
import { CheckCircle2, FileText, Loader2, Upload, XCircle } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

import { useRagStore } from '@/lib/store/ragStore'
import type { IngestStatus } from '@/lib/api/rag'

const STATUS_LABELS: Record<IngestStatus, string> = {
  pending: '排队中',
  parsing: 'Layout 解析',
  embedding: '多模态 embedding',
  completed: '已完成',
  failed: '失败',
}

function statusIcon(status: IngestStatus) {
  if (status === 'completed') return <CheckCircle2 className="h-4 w-4 text-emerald-600" />
  if (status === 'failed') return <XCircle className="h-4 w-4 text-destructive" />
  return <Loader2 className="h-4 w-4 animate-spin text-primary" />
}

export function IngestUploader() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  const ingestTasks = useRagStore((s) => s.ingestTasks)
  const enqueueIngest = useRagStore((s) => s.enqueueIngest)

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0) return
      for (const file of Array.from(files)) {
        try {
          await enqueueIngest(file)
        } catch (e) {
          console.error('[IngestUploader] enqueue failed', e)
        }
      }
    },
    [enqueueIngest],
  )

  const tasks = Object.values(ingestTasks).sort((a, b) =>
    b.created_at.localeCompare(a.created_at),
  )

  return (
    <div className="space-y-4">
      {/* dropzone */}
      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragOver(true)
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragOver(false)
          void handleFiles(e.dataTransfer.files)
        }}
        className={`flex flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed p-10 text-center transition-colors ${
          dragOver
            ? 'border-primary bg-primary/5'
            : 'border-border/60 bg-surface-1 hover:border-primary/40 hover:bg-primary/2'
        }`}
      >
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Upload className="h-7 w-7" />
        </div>
        <div className="space-y-1">
          <p className="text-base font-medium text-foreground">
            拖拽文档到此处，或点击下方按钮选择
          </p>
          <p className="text-xs text-muted-foreground">
            支持 PDF / Word / 图片 / 扫描件 — 自动识别文本、图像、表格、公式、印章 5 种模态
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => inputRef.current?.click()}
          iconLeft={<Upload className="h-4 w-4" />}
        >
          选择文件
        </Button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.webp"
          className="hidden"
          onChange={(e) => void handleFiles(e.target.files)}
        />
      </div>

      {/* 进度列表 */}
      {tasks.length === 0 ? (
        <div className="rounded-2xl border border-border/40 bg-surface-1 px-4 py-6 text-center text-xs text-muted-foreground">
          尚无解析任务。上传文档后，进度会在这里实时刷新。
        </div>
      ) : (
        <ul className="space-y-2">
          {tasks.map((t) => (
            <li
              key={t.task_id}
              className="rounded-2xl border border-border/40 bg-surface-1 p-3 shadow-sm"
            >
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-muted/60">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate text-sm font-medium text-foreground" title={t.filename}>
                      {t.filename}
                    </span>
                    <span className="flex shrink-0 items-center gap-1 text-[11px] text-muted-foreground">
                      {statusIcon(t.status)} {STATUS_LABELS[t.status]}
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center gap-3">
                    <Progress value={t.progress} className="h-1.5 flex-1" />
                    <span className="shrink-0 text-[11px] tabular-nums text-muted-foreground">
                      {t.progress}%
                    </span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span className="truncate">{t.stage_label}</span>
                    <span className="shrink-0 tabular-nums">
                      segments {t.segments_done} / {t.segments_total}
                    </span>
                  </div>
                  {t.error && (
                    <p className="mt-1 text-[11px] text-destructive">错误：{t.error}</p>
                  )}
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default IngestUploader
