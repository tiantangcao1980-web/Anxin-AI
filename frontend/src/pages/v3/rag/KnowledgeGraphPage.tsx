/**
 * KnowledgeGraphPage — 跨模态知识图谱（V3 P13-D）
 *
 * 路由：/v3/rag/kg
 *
 * 内容：
 *   - 顶部：文档选择器（聚合 / 单文档）+ 概览（实体 / 关系 / 跨模态比）
 *   - 主区：CrossModalGraph
 *   - 右侧（lg+）：选中 entity 的详情 + 同 anchor segment preview
 */

import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

import { CrossModalGraph } from '@/components/v3/rag/CrossModalGraph'
import { SegmentPreview } from '@/components/v3/rag/SegmentPreview'
import { modalityVisual } from '@/components/v3/rag/modalityStyle'

import { useRagStore } from '@/lib/store/ragStore'

export default function KnowledgeGraphPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const docIdParam = searchParams.get('doc_id')

  const documents = useRagStore((s) => s.documents)
  const loadDocuments = useRagStore((s) => s.loadDocuments)
  const currentKG = useRagStore((s) => s.currentKG)
  const kgLoading = useRagStore((s) => s.kgLoading)
  const kgError = useRagStore((s) => s.kgError)
  const loadKGForDoc = useRagStore((s) => s.loadKGForDoc)
  const loadAggregateKG = useRagStore((s) => s.loadAggregateKG)
  const loadDocument = useRagStore((s) => s.loadDocument)
  const currentDocument = useRagStore((s) => s.currentDocument)

  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null)

  useEffect(() => {
    if (documents.length === 0) void loadDocuments()
  }, [documents.length, loadDocuments])

  useEffect(() => {
    if (docIdParam) {
      void loadKGForDoc(docIdParam)
      void loadDocument(docIdParam)
    } else {
      void loadAggregateKG()
    }
    setSelectedEntityId(null)
  }, [docIdParam, loadKGForDoc, loadAggregateKG, loadDocument])

  const selectedEntity = useMemo(() => {
    if (!currentKG || !selectedEntityId) return null
    return currentKG.entities.find((e) => e.entity_id === selectedEntityId) ?? null
  }, [currentKG, selectedEntityId])

  const anchorSegment = useMemo(() => {
    if (!selectedEntity?.anchor_segment_id || !currentDocument) return null
    return currentDocument.segments.find((s) => s.segment_id === selectedEntity.anchor_segment_id) ?? null
  }, [selectedEntity, currentDocument])

  const totals = currentKG
    ? {
        entities: currentKG.entities.length,
        relations: currentKG.relations.length,
        crossModal: currentKG.relations.filter((r) => r.cross_modal).length,
      }
    : { entities: 0, relations: 0, crossModal: 0 }

  return (
    <div className="mx-auto flex h-full w-full max-w-[1400px] flex-col gap-4 p-6">
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
              <icons.Network className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">
                跨模态知识图谱
              </h1>
              <p className="mt-0.5 max-w-xl text-xs text-muted-foreground">
                节点颜色 = 主模态；多模态实体 → 渐变外环；跨模态边 → 虚线 + 渐变 + 颗粒流动。
              </p>
            </div>
          </div>
        </div>

        {/* 文档选择 */}
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant={!docIdParam ? 'default' : 'outline'}
            onClick={() => {
              setSearchParams({})
            }}
          >
            聚合视图
          </Button>
          {documents.map((d) => (
            <Button
              key={d.doc_id}
              size="sm"
              variant={docIdParam === d.doc_id ? 'default' : 'outline'}
              onClick={() => setSearchParams({ doc_id: d.doc_id })}
              className="max-w-[160px] truncate"
            >
              {d.doc_type}
            </Button>
          ))}
        </div>
      </header>

      {/* 概览 */}
      <div className="flex flex-wrap items-center gap-3">
        <Badge variant="outline" className="rounded-full px-3 py-1 text-[11px]">
          实体 <span className="ml-1 font-semibold tabular-nums">{totals.entities}</span>
        </Badge>
        <Badge variant="outline" className="rounded-full px-3 py-1 text-[11px]">
          关系 <span className="ml-1 font-semibold tabular-nums">{totals.relations}</span>
        </Badge>
        <Badge variant="outline" className="rounded-full px-3 py-1 text-[11px]">
          跨模态边{' '}
          <span className="ml-1 font-semibold tabular-nums text-amber-600 dark:text-amber-400">
            {totals.crossModal}
          </span>{' '}
          / {totals.relations}
        </Badge>
        {kgError && <span className="text-xs text-destructive">加载失败：{kgError}</span>}
        {kgLoading && <span className="text-xs text-muted-foreground">构建图谱中…</span>}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        {/* 主区：图谱 */}
        <CrossModalGraph
          kg={currentKG}
          selectedEntityId={selectedEntityId}
          onSelectEntity={setSelectedEntityId}
          onJumpToSegment={(segId) => {
            // 跳到 library，把 doc_id 带过去（这里简化为提示）
            navigate(`/v3/rag/library`)
            console.info('[KG] jump to segment', segId)
          }}
        />

        {/* 右栏：entity / segment 详情 */}
        <aside className="overflow-y-auto rounded-3xl border border-border/40 bg-surface-1 p-3">
          {selectedEntity ? (
            <div className="space-y-3">
              <div>
                <p className="text-[11px] uppercase tracking-wider text-muted-foreground">
                  Entity
                </p>
                <h2 className="text-sm font-semibold text-foreground">{selectedEntity.name}</h2>
                <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
                  <Badge variant="secondary" className="text-[10px]">
                    {selectedEntity.entity_type}
                  </Badge>
                  {selectedEntity.modalities.map((m) => {
                    const v = modalityVisual(m)
                    return (
                      <span
                        key={m}
                        className={`flex items-center gap-1 rounded-full border ${v.border} ${v.bg} px-2 py-0.5 text-[10px] ${v.text}`}
                      >
                        <span aria-hidden>{v.emoji}</span>
                        {v.label}
                      </span>
                    )
                  })}
                </div>
                <div className="mt-2 flex items-center gap-3 text-[11px] text-muted-foreground">
                  <span>提及 {selectedEntity.mentions}</span>
                  {typeof selectedEntity.confidence === 'number' && (
                    <span>
                      置信 {(selectedEntity.confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>

              {anchorSegment && (
                <div>
                  <p className="mb-1 text-[11px] uppercase tracking-wider text-muted-foreground">
                    锚定 segment
                  </p>
                  <SegmentPreview segment={anchorSegment} highlighted />
                </div>
              )}

              {/* 关联关系 */}
              {currentKG && (
                <div>
                  <p className="mb-1 text-[11px] uppercase tracking-wider text-muted-foreground">
                    关联关系
                  </p>
                  <ul className="space-y-1">
                    {currentKG.relations
                      .filter(
                        (r) =>
                          r.source === selectedEntity.entity_id ||
                          r.target === selectedEntity.entity_id,
                      )
                      .slice(0, 8)
                      .map((r) => {
                        const otherId =
                          r.source === selectedEntity.entity_id ? r.target : r.source
                        const other = currentKG.entities.find((e) => e.entity_id === otherId)
                        return (
                          <li
                            key={r.relation_id}
                            className="flex items-center gap-2 rounded-lg border border-border/40 bg-background px-2 py-1.5 text-[11px]"
                          >
                            <span className="truncate text-foreground/80">
                              {other?.name ?? otherId}
                            </span>
                            <span className="ml-auto flex items-center gap-1">
                              {r.cross_modal && (
                                <span className="rounded-full bg-amber-500/15 px-1.5 text-[9px] font-medium text-amber-700 dark:text-amber-400">
                                  跨模态
                                </span>
                              )}
                              <span className="text-muted-foreground">{r.label}</span>
                            </span>
                          </li>
                        )
                      })}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <p className="px-2 py-4 text-xs text-muted-foreground">
              点击图中节点查看 entity 详情、关联关系与 anchor segment。
            </p>
          )}
        </aside>
      </div>
    </div>
  )
}
