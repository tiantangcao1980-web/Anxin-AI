/**
 * DocumentLibraryPage — 文档库 + 单文档详情（V3 P13-D）
 *
 * 路由：/v3/rag/library
 *
 * 三栏布局：
 *   - 左：文档列表（卡片）
 *   - 中：选中文档的 Layout Tree（章 / 条 / 款 / 项）
 *   - 右：选中 segment 的 SegmentPreview（大图）+ 同文档其它 segments 网格
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Library, Network } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

import { LayoutTreeView } from '@/components/v3/rag/LayoutTreeView'
import { SegmentPreview } from '@/components/v3/rag/SegmentPreview'
import { MODALITIES, modalityVisual } from '@/components/v3/rag/modalityStyle'

import { useRagStore } from '@/lib/store/ragStore'

export default function DocumentLibraryPage() {
  const navigate = useNavigate()

  const documents = useRagStore((s) => s.documents)
  const documentsLoading = useRagStore((s) => s.documentsLoading)
  const documentsError = useRagStore((s) => s.documentsError)
  const loadDocuments = useRagStore((s) => s.loadDocuments)

  const currentDocument = useRagStore((s) => s.currentDocument)
  const currentDocumentLoading = useRagStore((s) => s.currentDocumentLoading)
  const loadDocument = useRagStore((s) => s.loadDocument)

  const [selectedDocId, setSelectedDocId] = useState<string | null>(null)
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null)

  useEffect(() => {
    if (documents.length === 0) void loadDocuments()
  }, [documents.length, loadDocuments])

  // 默认选中第一篇
  useEffect(() => {
    if (!selectedDocId && documents.length > 0) setSelectedDocId(documents[0].doc_id)
  }, [documents, selectedDocId])

  useEffect(() => {
    if (selectedDocId) void loadDocument(selectedDocId)
    setSelectedSegmentId(null)
  }, [selectedDocId, loadDocument])

  const selectedSegment = currentDocument?.segments.find((s) => s.segment_id === selectedSegmentId)

  return (
    <div className="mx-auto flex h-full w-full max-w-[1400px] flex-col gap-4 p-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => navigate('/v3/rag')}
            iconLeft={<ArrowLeft className="h-4 w-4" />}
            className="h-8"
          >
            返回看板
          </Button>
          <div className="flex items-start gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <Library className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">文档库</h1>
              <p className="mt-0.5 max-w-xl text-xs text-muted-foreground">
                浏览已 ingest 的文档 — 点 layout tree 节点查看对应的 segment 预览。
              </p>
            </div>
          </div>
        </div>
        {currentDocument?.kg_id && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => navigate(`/v3/rag/kg?doc_id=${currentDocument.doc_id}`)}
            iconLeft={<Network className="h-4 w-4" />}
          >
            打开知识图谱
          </Button>
        )}
      </header>

      {documentsError && (
        <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {documentsError}
        </div>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[260px_280px_minmax(0,1fr)]">
        {/* 文档列表 */}
        <aside className="rounded-3xl border border-border/40 bg-surface-1 p-3">
          <p className="mb-2 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            文档（{documents.length}）
          </p>
          {documentsLoading ? (
            <p className="px-3 py-4 text-xs text-muted-foreground">加载中…</p>
          ) : (
            <ul className="space-y-1.5">
              {documents.map((d) => {
                const active = d.doc_id === selectedDocId
                return (
                  <li key={d.doc_id}>
                    <button
                      type="button"
                      onClick={() => setSelectedDocId(d.doc_id)}
                      className={`group block w-full rounded-xl border p-2.5 text-left transition-colors ${
                        active
                          ? 'border-primary bg-primary/10'
                          : 'border-border/60 bg-background hover:border-primary/40'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="truncate text-xs font-medium text-foreground" title={d.filename}>
                          {d.filename}
                        </span>
                        <Badge variant="secondary" className="shrink-0 text-[9px]">
                          {d.doc_type}
                        </Badge>
                      </div>
                      <div className="mt-1.5 flex items-center gap-2 text-[10px] text-muted-foreground">
                        <span>{d.page_count} 页</span>
                        <span aria-hidden>·</span>
                        <span>{d.segments_count} segments</span>
                      </div>
                      {/* mini bar: modality breakdown */}
                      <div className="mt-1.5 flex h-1.5 overflow-hidden rounded">
                        {MODALITIES.map((m) => {
                          const v = modalityVisual(m)
                          const n = d.modality_breakdown[m] ?? 0
                          if (n === 0) return null
                          const ratio = (n / Math.max(1, d.segments_count)) * 100
                          return (
                            <span
                              key={m}
                              style={{ background: v.color, width: `${ratio}%` }}
                              title={`${v.label} ${n}`}
                            />
                          )
                        })}
                      </div>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </aside>

        {/* layout tree */}
        <aside className="overflow-y-auto rounded-3xl border border-border/40 bg-surface-1 p-3">
          <p className="mb-2 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            Layout 树
          </p>
          {currentDocumentLoading ? (
            <p className="px-3 py-4 text-xs text-muted-foreground">解析中…</p>
          ) : currentDocument ? (
            <LayoutTreeView
              segments={currentDocument.segments}
              selectedId={selectedSegmentId}
              onSelect={setSelectedSegmentId}
            />
          ) : (
            <p className="px-3 py-4 text-xs text-muted-foreground">请选择文档</p>
          )}
        </aside>

        {/* segment 详情 + segments 网格 */}
        <section className="overflow-y-auto rounded-3xl border border-border/40 bg-surface-1 p-3">
          {selectedSegment && (
            <div className="mb-3">
              <p className="mb-1.5 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                选中 segment
              </p>
              <SegmentPreview segment={selectedSegment} highlighted />
            </div>
          )}
          <p className="mb-2 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            所有 segments
          </p>
          {currentDocument ? (
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {currentDocument.segments.map((seg) => (
                <SegmentPreview
                  key={seg.segment_id}
                  segment={seg}
                  highlighted={selectedSegmentId === seg.segment_id}
                  onClick={(id) => setSelectedSegmentId(id)}
                />
              ))}
            </div>
          ) : (
            <p className="px-3 py-4 text-xs text-muted-foreground">请选择文档</p>
          )}
        </section>
      </div>
    </div>
  )
}
