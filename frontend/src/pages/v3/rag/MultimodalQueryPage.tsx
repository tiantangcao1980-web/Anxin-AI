/**
 * MultimodalQueryPage — 多模态 VLM 查询（V3 P13-D）
 *
 * 路由：/v3/rag/query
 *
 * 三栏：
 *   - 左：query 输入 + ModalityWeightSlider + visual_grounding 开关 + 文档过滤 + 历史
 *   - 中：VLMAnswerView（答案 + visual grounding + modality scores）
 *   - 右：CitationCard 列表（点击跳到 library）
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'

import { CitationCard } from '@/components/v3/rag/CitationCard'
import { ModalityWeightSlider } from '@/components/v3/rag/ModalityWeightSlider'
import { VLMAnswerView } from '@/components/v3/rag/VLMAnswerView'

import { useRagStore } from '@/lib/store/ragStore'

const SUGGESTED_QUERIES = [
  '甲方公章对应的法定代表人是谁？',
  '2025 年 ROE 是怎么算出来的？',
  'B 轮融资估值和披露金额是否一致？',
  '合同总价表格里的设备 A 单价是多少？',
]

export default function MultimodalQueryPage() {
  const navigate = useNavigate()

  const documents = useRagStore((s) => s.documents)
  const loadDocuments = useRagStore((s) => s.loadDocuments)
  const visualGrounding = useRagStore((s) => s.visualGrounding)
  const setVisualGrounding = useRagStore((s) => s.setVisualGrounding)
  const selectedDocIdsForQuery = useRagStore((s) => s.selectedDocIdsForQuery)
  const setSelectedDocIdsForQuery = useRagStore((s) => s.setSelectedDocIdsForQuery)
  const currentAnswer = useRagStore((s) => s.currentAnswer)
  const queryPending = useRagStore((s) => s.queryPending)
  const queryError = useRagStore((s) => s.queryError)
  const runQuery = useRagStore((s) => s.runQuery)
  const history = useRagStore((s) => s.history)
  const loadHistory = useRagStore((s) => s.loadHistory)

  const [query, setQuery] = useState('')

  useEffect(() => {
    if (documents.length === 0) void loadDocuments()
  }, [documents.length, loadDocuments])

  useEffect(() => {
    if (history.length === 0) void loadHistory()
  }, [history.length, loadHistory])

  const submit = async () => {
    const q = query.trim()
    if (!q) return
    await runQuery(q)
  }

  const toggleDoc = (docId: string) => {
    if (selectedDocIdsForQuery.includes(docId)) {
      setSelectedDocIdsForQuery(selectedDocIdsForQuery.filter((x) => x !== docId))
    } else {
      setSelectedDocIdsForQuery([...selectedDocIdsForQuery, docId])
    }
  }

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
              <icons.Sparkles className="size-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-foreground">
                多模态 VLM 查询
              </h1>
              <p className="mt-0.5 max-w-xl text-xs text-muted-foreground">
                调节 5 模态权重 → 检索 → VLM 综合答案 + visual grounding 高亮 + 引文跳转。
              </p>
            </div>
          </div>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[320px_minmax(0,1fr)_320px]">
        {/* 左：query 输入 + 权重 + 历史 */}
        <aside className="flex flex-col gap-4 overflow-y-auto rounded-3xl border border-border/40 bg-surface-1 p-4">
          {/* 输入 */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-foreground">查询</p>
            <Input
              placeholder="问点什么…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void submit()
                }
              }}
            />
            <Button
              size="sm"
              className="w-full"
              onClick={() => void submit()}
              loading={queryPending}
              disabled={!query.trim()}
              iconLeft={<icons.Search className="h-4 w-4" />}
            >
              检索
            </Button>
            {/* 建议问题 */}
            <div className="space-y-1 pt-1">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">建议</p>
              {SUGGESTED_QUERIES.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => setQuery(q)}
                  className="block w-full truncate rounded-md px-2 py-1 text-left text-[11px] text-foreground/70 hover:bg-muted"
                  title={q}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* 权重 */}
          <ModalityWeightSlider />

          {/* visual grounding */}
          <div className="flex items-center justify-between rounded-xl border border-border/40 bg-background p-2.5">
            <div className="flex items-center gap-2">
              <icons.Eye className="h-4 w-4 text-muted-foreground" />
              <div>
                <p className="text-xs font-medium text-foreground">Visual Grounding</p>
                <p className="text-[10px] text-muted-foreground">在 segment 上画 bbox 高亮</p>
              </div>
            </div>
            <Switch checked={visualGrounding} onCheckedChange={setVisualGrounding} />
          </div>

          {/* 文档过滤 */}
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-foreground">检索范围</p>
            {documents.length === 0 ? (
              <p className="text-[11px] text-muted-foreground">未加载文档</p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {documents.map((d) => {
                  const active = selectedDocIdsForQuery.includes(d.doc_id)
                  return (
                    <button
                      key={d.doc_id}
                      type="button"
                      onClick={() => toggleDoc(d.doc_id)}
                      className={`rounded-full border px-2 py-0.5 text-[10px] transition-colors ${
                        active
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border/60 bg-background text-foreground/70 hover:border-primary/40'
                      }`}
                    >
                      {d.doc_type}
                    </button>
                  )
                })}
              </div>
            )}
            <p className="text-[10px] text-muted-foreground">不勾即在全部文档检索</p>
          </div>

          {/* 历史 */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-1.5 text-xs font-medium text-foreground">
              <icons.History className="h-3.5 w-3.5" /> 历史
            </div>
            {history.length === 0 ? (
              <p className="text-[11px] text-muted-foreground">尚无历史查询</p>
            ) : (
              <ul className="space-y-1">
                {history.slice(0, 8).map((h) => (
                  <li key={h.query_id}>
                    <button
                      type="button"
                      onClick={() => setQuery(h.query)}
                      className="flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-[11px] hover:bg-muted"
                    >
                      <Badge variant="secondary" className="shrink-0 text-[9px]">
                        {h.citations_count} 引文
                      </Badge>
                      <span className="line-clamp-1 text-foreground/80">{h.query}</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </aside>

        {/* 中：答案 */}
        <section className="overflow-y-auto rounded-3xl border border-border/40 bg-surface-1 p-4">
          <VLMAnswerView answer={currentAnswer} loading={queryPending} error={queryError} />
        </section>

        {/* 右：引文 */}
        <aside className="overflow-y-auto rounded-3xl border border-border/40 bg-surface-1 p-3">
          <p className="mb-2 px-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
            引文（{currentAnswer?.citations.length ?? 0}）
          </p>
          {currentAnswer ? (
            <div className="space-y-2">
              {currentAnswer.citations.map((c, i) => (
                <CitationCard
                  key={c.citation_id}
                  citation={c}
                  index={i}
                  onClick={(_segId, _docId) => navigate('/v3/rag/library')}
                />
              ))}
            </div>
          ) : (
            <p className="px-2 py-4 text-[11px] text-muted-foreground">
              检索后这里会显示带 score 的引文卡片，点击跳到 segment 原位。
            </p>
          )}
        </aside>
      </div>
    </div>
  )
}
