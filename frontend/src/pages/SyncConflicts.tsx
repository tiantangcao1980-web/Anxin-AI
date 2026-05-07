import { useCallback, useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { icons } from '@/lib/icons'
import {
  getSyncConflicts,
  isTauri,
  resolveSyncConflict,
  triggerSync,
} from '@/lib/tauri-bridge'
import {
  buildMergedConflictDraft,
  formatConflictData,
  parseConflictMergeDraft,
} from '@/lib/sync-conflict-utils'

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

  const handleResolve = useCallback(async (
    conflict: SyncConflictItem,
    resolution: SyncResolution,
  ) => {
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
  }, [drafts, loadConflicts])

  useEffect(() => {
    void loadConflicts()
  }, [loadConflicts])

  useEffect(() => {
    if (selectedConflict) {
      ensureDraft(selectedConflict)
    }
  }, [ensureDraft, selectedConflict])

  if (!desktop) {
    return (
      <div className="min-h-full bg-background p-6">
        <div className="mx-auto flex max-w-3xl items-center gap-3 rounded-lg border border-border bg-card p-4">
          <icons.Database className="h-5 w-5 text-muted-foreground" />
          <div>
            <h1 className="text-base font-semibold text-foreground">同步冲突</h1>
            <p className="mt-1 text-sm text-muted-foreground">当前环境没有本地同步数据库。</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-full bg-background p-4 lg:p-6">
      <div className="mx-auto max-w-7xl space-y-4">
        <header className="flex flex-col gap-3 border-b border-border pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <icons.AlertTriangle className="h-5 w-5 text-destructive" />
              <h1 className="text-xl font-semibold text-foreground">同步冲突</h1>
              <Badge variant={conflicts.length > 0 ? 'destructive' : 'secondary'}>
                {conflicts.length}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              本地与云端同时更新的记录会停在这里等待处理。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button variant="outline" size="sm" onClick={loadConflicts} disabled={loading}>
              <icons.RefreshCw className="mr-2 h-4 w-4" />
              刷新
            </Button>
            <Button size="sm" onClick={handleManualSync} disabled={syncing}>
              <icons.Cloud className="mr-2 h-4 w-4" />
              {syncing ? '同步中' : '立即同步'}
            </Button>
          </div>
        </header>

        <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="min-h-72 rounded-lg border border-border bg-card">
            <div className="border-b border-border px-4 py-3">
              <h2 className="text-sm font-medium text-foreground">待处理记录</h2>
            </div>
            <div className="max-h-[66vh] overflow-y-auto p-2">
              {loading ? (
                <div className="px-3 py-8 text-sm text-muted-foreground">加载中...</div>
              ) : conflicts.length === 0 ? (
                <div className="px-3 py-8 text-sm text-muted-foreground">没有待处理冲突。</div>
              ) : conflicts.map((conflict) => {
                const active = selectedConflict?.log_id === conflict.log_id
                return (
                  <button
                    key={conflict.log_id}
                    type="button"
                    onClick={() => setSelectedId(conflict.log_id)}
                    className={`mb-2 w-full rounded-md border p-3 text-left transition-colors ${
                      active
                        ? 'border-primary bg-primary/5'
                        : 'border-border bg-background hover:bg-muted'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium text-foreground">
                        {conflict.entity_type}
                      </span>
                      <Badge variant="outline">{conflict.log_id}</Badge>
                    </div>
                    <p className="mt-1 truncate text-xs text-muted-foreground">{conflict.entity_id}</p>
                  </button>
                )
              })}
            </div>
          </aside>

          <section className="min-h-72 rounded-lg border border-border bg-card">
            {!selectedConflict ? (
              <div className="flex min-h-72 items-center justify-center p-6 text-sm text-muted-foreground">
                当前没有需要处理的同步冲突。
              </div>
            ) : (
              <div className="space-y-4 p-4">
                <div className="flex flex-col gap-2 border-b border-border pb-4 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <h2 className="truncate text-base font-semibold text-foreground">
                      {selectedConflict.entity_type} / {selectedConflict.entity_id}
                    </h2>
                    <p className="mt-1 text-xs text-muted-foreground">
                      本地 {formatTime(selectedConflict.local_timestamp)} · 云端 {formatTime(selectedConflict.remote_timestamp)}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={resolvingId === selectedConflict.log_id}
                      onClick={() => handleResolve(selectedConflict, 'keep_remote')}
                    >
                      <icons.Cloud className="mr-2 h-4 w-4" />
                      保留云端
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={resolvingId === selectedConflict.log_id}
                      onClick={() => handleResolve(selectedConflict, 'keep_local')}
                    >
                      <icons.Database className="mr-2 h-4 w-4" />
                      保留本地
                    </Button>
                  </div>
                </div>

                <div className="grid gap-3 xl:grid-cols-2">
                  <div className="rounded-md border border-border bg-background">
                    <div className="border-b border-border px-3 py-2 text-sm font-medium text-foreground">
                      本地版本
                    </div>
                    <pre className="max-h-72 overflow-auto p-3 text-xs text-muted-foreground">
                      {formatConflictData(selectedConflict.local_data)}
                    </pre>
                  </div>
                  <div className="rounded-md border border-border bg-background">
                    <div className="border-b border-border px-3 py-2 text-sm font-medium text-foreground">
                      云端版本
                    </div>
                    <pre className="max-h-72 overflow-auto p-3 text-xs text-muted-foreground">
                      {formatConflictData(selectedConflict.remote_data)}
                    </pre>
                  </div>
                </div>

                <div className="rounded-md border border-border bg-background">
                  <div className="flex flex-col gap-2 border-b border-border px-3 py-2 md:flex-row md:items-center md:justify-between">
                    <h3 className="text-sm font-medium text-foreground">合并版本</h3>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setDrafts((current) => ({
                        ...current,
                        [selectedConflict.log_id]: buildMergedConflictDraft(
                          selectedConflict.local_data,
                          selectedConflict.remote_data,
                        ),
                      }))}
                    >
                      <icons.Refresh className="mr-2 h-4 w-4" />
                      重置草稿
                    </Button>
                  </div>
                  <div className="space-y-3 p-3">
                    <Textarea
                      className="min-h-64 font-mono text-xs"
                      value={drafts[selectedConflict.log_id] ?? ''}
                      onChange={(event) => setDrafts((current) => ({
                        ...current,
                        [selectedConflict.log_id]: event.target.value,
                      }))}
                    />
                    <div className="flex justify-end">
                      <Button
                        disabled={resolvingId === selectedConflict.log_id}
                        onClick={() => handleResolve(selectedConflict, 'merge')}
                      >
                        <icons.Check className="mr-2 h-4 w-4" />
                        提交合并
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
