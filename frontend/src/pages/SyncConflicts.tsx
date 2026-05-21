/**
 * SyncConflicts · 同步冲突处理（Editorial Luxury 改造 · Phase 1）
 *
 * Tauri 桌面端专用 — 列出本地/云端同时更新的记录，提供 保留本地 / 保留云端 / 手动合并 三种解决方式。
 *
 * 旧版用裸 div + Badge variant chip。新版：EditorialPageHeader + 暖灰阶 1px hairline。
 * 状态色 tone-only（destructive 冲突计数）。
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { AlertTriangle, Check, Cloud, Database, RefreshCw, Server } from 'lucide-react'

import { EditorialPageHeader } from '@/components/ui/EditorialPageHeader'
import {
  buildMergedConflictDraft,
  formatConflictData,
  parseConflictMergeDraft,
} from '@/lib/sync-conflict-utils'
import {
  getSyncConflicts,
  isTauri,
  resolveSyncConflict,
  triggerSync,
} from '@/lib/tauri-bridge'
import { cn } from '@/components/ui/utils'

interface SyncConflictItem {
  log_id: number
  entity_type: string
  entity_id: string
  local_data: Record<string, unknown>
  remote_data: Record<string, unknown>
  local_timestamp?: string | null
  remote_timestamp?: string | null
}

type SyncResolution = 'keep_local' | 'keep_remote' | 'merge'

function formatTime(value?: string | null) {
  if (!value) return '无时间'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN')
}

export default function SyncConflicts() {
  const [conflicts, setConflicts] = useState<SyncConflictItem[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [drafts, setDrafts] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [resolvingId, setResolvingId] = useState<number | null>(null)
  const desktop = isTauri()

  const selectedConflict = useMemo(
    () => conflicts.find((conflict) => conflict.log_id === selectedId) ?? conflicts[0] ?? null,
    [conflicts, selectedId],
  )

  const ensureDraft = useCallback((conflict: SyncConflictItem) => {
    setDrafts((current) => {
      if (current[conflict.log_id]) return current
      return {
        ...current,
        [conflict.log_id]: buildMergedConflictDraft(conflict.local_data, conflict.remote_data),
      }
    })
  }, [])

  const loadConflicts = useCallback(async () => {
    if (!desktop) {
      setLoading(false)
      return
    }
    setLoading(true)
    try {
      const rows = await getSyncConflicts()
      const next = rows as SyncConflictItem[]
      setConflicts(next)
      setSelectedId((current) => {
        if (current && next.some((item) => item.log_id === current)) return current
        return next[0]?.log_id ?? null
      })
      next.forEach(ensureDraft)
    } finally {
      setLoading(false)
    }
  }, [desktop, ensureDraft])

  const handleManualSync = useCallback(async () => {
    setSyncing(true)
    try {
      const result = await triggerSync()
      if (result?.success) {
        toast.success(result.message)
      } else {
        toast.error(result?.message ?? '同步失败')
      }
      await loadConflicts()
    } finally {
      setSyncing(false)
    }
  }, [loadConflicts])

  const handleResolve = useCallback(
    async (conflict: SyncConflictItem, resolution: SyncResolution) => {
      let mergedData: Record<string, unknown> | undefined
      if (resolution === 'merge') {
        const parsed = parseConflictMergeDraft(drafts[conflict.log_id] ?? '')
        if (!parsed.ok) {
          toast.error(parsed.message)
          return
        }
        mergedData = parsed.data
      }
      setResolvingId(conflict.log_id)
      try {
        const result = await resolveSyncConflict(conflict.log_id, resolution, mergedData)
        if (result.success) {
          toast.success(result.message)
          await loadConflicts()
        } else {
          toast.error(result.message)
        }
      } finally {
        setResolvingId(null)
      }
    },
    [drafts, loadConflicts],
  )

  useEffect(() => { void loadConflicts() }, [loadConflicts])
  useEffect(() => {
    if (selectedConflict) ensureDraft(selectedConflict)
  }, [ensureDraft, selectedConflict])

  // === 非 Tauri 环境：友好提示 ===
  if (!desktop) {
    return (
      <div className="mx-auto max-w-3xl px-6 sm:px-8 lg:px-12 py-12 lg:py-20">
        <EditorialPageHeader
          tracker={['Sync', '同步冲突']}
          title="同步冲突"
          description="本功能仅在桌面客户端（Tauri）启用。"
        />
        <div className="border border-border bg-card px-6 py-8 flex items-start gap-4">
          <Database className="h-5 w-5 stroke-[1.5] text-muted-foreground shrink-0 mt-0.5" />
          <div>
            <h3 className="text-[15px] font-medium text-foreground">当前环境无本地同步数据库</h3>
            <p className="mt-1 text-[13px] text-muted-foreground leading-relaxed">
              请使用安心智能助手桌面客户端打开此页面。Web 端不持有本地同步队列，因此无法显示冲突。
            </p>
          </div>
        </div>
      </div>
    )
  }

  const conflictCountClass = conflicts.length > 0 ? 'text-destructive' : 'text-success'

  return (
    <div className="mx-auto max-w-[1600px] px-6 sm:px-8 lg:px-12 xl:px-16 py-8 lg:py-12">
      <EditorialPageHeader
        tracker={['Sync', '同步冲突']}
        title="同步冲突"
        description="本地与云端同时更新的记录会停在这里等待处理。"
        actions={
          <>
            <span
              className={cn(
                'inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em]',
                conflictCountClass,
              )}
            >
              {conflicts.length > 0 && <AlertTriangle className="w-3 h-3 stroke-[1.5]" />}
              <span>{conflicts.length === 0 ? 'In Sync' : `${conflicts.length} Pending`}</span>
            </span>
            <button
              type="button"
              onClick={() => void loadConflicts()}
              disabled={loading}
              className="inline-flex items-center gap-2 border border-border hover:border-foreground text-foreground/80 hover:text-foreground px-3 py-1.5 text-[13px] transition-colors disabled:opacity-50"
            >
              <RefreshCw className={cn('w-3.5 h-3.5 stroke-[1.5]', loading && 'animate-spin')} />
              <span>刷新</span>
            </button>
            <button
              type="button"
              onClick={() => void handleManualSync()}
              disabled={syncing}
              className="inline-flex items-center gap-2 bg-primary hover:bg-primary-700 text-primary-foreground px-4 py-1.5 text-[13px] font-medium transition-colors disabled:opacity-50"
            >
              <Cloud className="w-3.5 h-3.5 stroke-[1.5]" />
              <span>{syncing ? '同步中…' : '立即同步'}</span>
            </button>
          </>
        }
      />

      <div className="grid gap-px bg-border border border-border lg:grid-cols-[340px_minmax(0,1fr)]">
        {/* 左栏：冲突列表 */}
        <aside className="bg-card min-h-[420px]">
          <header className="px-4 py-3 border-b border-border">
            <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Pending · 待处理记录
            </div>
          </header>
          <div className="max-h-[66vh] overflow-y-auto">
            {loading ? (
              <div className="px-4 py-12 text-center text-[13px] text-muted-foreground">加载中…</div>
            ) : conflicts.length === 0 ? (
              <div className="px-4 py-12 text-center">
                <Check className="w-5 h-5 stroke-[1.5] mx-auto text-success mb-3" />
                <p className="text-[13px] text-foreground">没有待处理冲突</p>
                <p className="mt-1 text-[12px] text-muted-foreground">本地与云端一致。</p>
              </div>
            ) : (
              <ol>
                {conflicts.map((conflict, i) => {
                  const active = selectedConflict?.log_id === conflict.log_id
                  return (
                    <li key={conflict.log_id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(conflict.log_id)}
                        aria-current={active ? 'page' : undefined}
                        className={cn(
                          'relative w-full text-left flex items-baseline gap-3 px-4 py-3 border-b border-border/60 transition-colors',
                          active ? 'bg-primary-50' : 'hover:bg-surface-2/40',
                        )}
                      >
                        {active && (
                          <span aria-hidden className="absolute left-0 top-2 bottom-2 w-px bg-primary" />
                        )}
                        <span className="font-serif text-[13px] text-muted-foreground w-8 shrink-0 tabular-nums">
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-baseline gap-2">
                            <span className="font-serif text-[15px] text-foreground truncate">
                              {conflict.entity_type}
                            </span>
                            <span className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground shrink-0">
                              #{conflict.log_id}
                            </span>
                          </div>
                          <p className="mt-1 text-[12px] text-muted-foreground truncate">
                            {conflict.entity_id}
                          </p>
                        </div>
                      </button>
                    </li>
                  )
                })}
              </ol>
            )}
          </div>
        </aside>

        {/* 右栏：详情 + 解决 */}
        <section className="bg-card min-h-[420px]">
          {!selectedConflict ? (
            <div className="flex min-h-[420px] items-center justify-center p-6">
              <p className="text-[13px] text-muted-foreground">当前没有需要处理的同步冲突。</p>
            </div>
          ) : (
            <div className="p-6 space-y-6">
              {/* 标题 + 操作 */}
              <header className="flex flex-col gap-3 pb-5 border-b border-border md:flex-row md:items-start md:justify-between">
                <div className="min-w-0">
                  <div className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
                    {selectedConflict.entity_type} · #{selectedConflict.log_id}
                  </div>
                  <h2 className="font-serif text-[22px] leading-tight tracking-tight text-foreground mt-1 truncate">
                    {selectedConflict.entity_id}
                  </h2>
                  <p className="mt-2 text-[13px] text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5">
                      <Database className="w-3 h-3 stroke-[1.5]" /> 本地 {formatTime(selectedConflict.local_timestamp)}
                    </span>
                    <span className="mx-3 text-foreground/30">·</span>
                    <span className="inline-flex items-center gap-1.5">
                      <Cloud className="w-3 h-3 stroke-[1.5]" /> 云端 {formatTime(selectedConflict.remote_timestamp)}
                    </span>
                  </p>
                </div>
                <div className="flex flex-wrap gap-2 shrink-0">
                  <button
                    type="button"
                    disabled={resolvingId === selectedConflict.log_id}
                    onClick={() => void handleResolve(selectedConflict, 'keep_remote')}
                    className="inline-flex items-center gap-2 border border-border hover:border-foreground text-foreground/80 hover:text-foreground px-3 py-1.5 text-[13px] transition-colors disabled:opacity-50"
                  >
                    <Cloud className="w-3.5 h-3.5 stroke-[1.5]" />
                    <span>保留云端</span>
                  </button>
                  <button
                    type="button"
                    disabled={resolvingId === selectedConflict.log_id}
                    onClick={() => void handleResolve(selectedConflict, 'keep_local')}
                    className="inline-flex items-center gap-2 border border-border hover:border-foreground text-foreground/80 hover:text-foreground px-3 py-1.5 text-[13px] transition-colors disabled:opacity-50"
                  >
                    <Database className="w-3.5 h-3.5 stroke-[1.5]" />
                    <span>保留本地</span>
                  </button>
                </div>
              </header>

              {/* 本地 vs 云端 对比 */}
              <div className="grid gap-3 xl:grid-cols-2">
                <div className="border border-border">
                  <header className="px-3 py-2 border-b border-border flex items-center gap-2">
                    <Database className="w-3.5 h-3.5 stroke-[1.5] text-muted-foreground" />
                    <span className="text-[12px] font-medium uppercase tracking-[0.12em] text-foreground/80">本地版本</span>
                  </header>
                  <pre className="max-h-72 overflow-auto p-3 text-[12px] leading-relaxed text-foreground/80 font-mono bg-surface-2/30">
                    {formatConflictData(selectedConflict.local_data)}
                  </pre>
                </div>
                <div className="border border-border">
                  <header className="px-3 py-2 border-b border-border flex items-center gap-2">
                    <Server className="w-3.5 h-3.5 stroke-[1.5] text-muted-foreground" />
                    <span className="text-[12px] font-medium uppercase tracking-[0.12em] text-foreground/80">云端版本</span>
                  </header>
                  <pre className="max-h-72 overflow-auto p-3 text-[12px] leading-relaxed text-foreground/80 font-mono bg-surface-2/30">
                    {formatConflictData(selectedConflict.remote_data)}
                  </pre>
                </div>
              </div>

              {/* 合并草稿 */}
              <div className="border border-border">
                <header className="px-3 py-2 border-b border-border flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <span className="text-[12px] font-medium uppercase tracking-[0.12em] text-foreground/80">
                    Merged · 合并草稿
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setDrafts((current) => ({
                        ...current,
                        [selectedConflict.log_id]: buildMergedConflictDraft(
                          selectedConflict.local_data,
                          selectedConflict.remote_data,
                        ),
                      }))
                    }
                    className="inline-flex items-center gap-1.5 border border-border hover:border-foreground text-foreground/70 hover:text-foreground px-2.5 py-1 text-[12px] transition-colors"
                  >
                    <RefreshCw className="w-3 h-3 stroke-[1.5]" />
                    <span>重置草稿</span>
                  </button>
                </header>
                <div className="space-y-3 p-3">
                  <textarea
                    className="w-full min-h-64 font-mono text-[12px] leading-relaxed border border-border bg-surface-1 p-3 text-foreground/90 outline-none focus:border-foreground transition-colors"
                    value={drafts[selectedConflict.log_id] ?? ''}
                    onChange={(event) =>
                      setDrafts((current) => ({
                        ...current,
                        [selectedConflict.log_id]: event.target.value,
                      }))
                    }
                  />
                  <div className="flex justify-end">
                    <button
                      type="button"
                      disabled={resolvingId === selectedConflict.log_id}
                      onClick={() => void handleResolve(selectedConflict, 'merge')}
                      className="inline-flex items-center gap-2 bg-primary hover:bg-primary-700 text-primary-foreground px-4 py-2 text-[13px] font-medium transition-colors disabled:opacity-50"
                    >
                      <Check className="w-4 h-4 stroke-[1.5]" />
                      <span>提交合并</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
