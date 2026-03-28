import { useState, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, buttonStyle, heading, statusColor } from '@/lib/design-tokens'
import { knowledgeApi } from '@/lib/api'
import { toast } from 'sonner'

type SearchMode = 'hybrid' | 'keyword' | 'vector' | 'rag'

interface SearchResult {
  id?: string
  title?: string
  content: string
  source?: string
  score?: number
  metadata?: Record<string, any>
}

interface RAGAnswer {
  answer: string
  sources: any[]
  context_used: boolean
  chunks_used?: number
}

const searchModes: { key: SearchMode; label: string; desc: string }[] = [
  { key: 'hybrid', label: '混合检索', desc: '关键词 + 向量综合排序' },
  { key: 'keyword', label: '关键词', desc: '精确匹配关键词' },
  { key: 'vector', label: '语义检索', desc: '基于语义相似度' },
  { key: 'rag', label: 'RAG 问答', desc: 'AI 智能问答' },
]

export default function Search() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<SearchMode>('hybrid')
  const [results, setResults] = useState<SearchResult[]>([])
  const [ragAnswer, setRagAnswer] = useState<RAGAnswer | null>(null)
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return
    setLoading(true)
    setHasSearched(true)
    setRagAnswer(null)

    try {
      if (mode === 'rag') {
        const answer = await knowledgeApi.ragQuery(query)
        setRagAnswer(answer)
        setResults([])
      } else {
        const data = await knowledgeApi.search(query, undefined, 20, mode === 'hybrid')
        setResults(Array.isArray(data) ? data : [])
      }
    } catch (err: any) {
      toast.error('搜索失败: ' + (err.message || '服务不可用'))
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [query, mode])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const highlightText = (text: string, q: string) => {
    if (!q.trim() || !text) return text
    const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'))
    return parts.map((part, i) =>
      part.toLowerCase() === q.toLowerCase()
        ? <mark key={i} className="bg-yellow-200 dark:bg-yellow-800 rounded px-0.5">{part}</mark>
        : part
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* 搜索头部 */}
      <div className="border-b border-border px-6 py-5">
        <h1 className={heading.page + ' mb-4'}>
          <icons.Search className="w-5 h-5 inline-block mr-2 -mt-0.5" />
          智慧搜索
        </h1>

        {/* 搜索框 */}
        <div className="flex gap-3 mb-4">
          <div className="flex-1 relative">
            <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入搜索关键词或问题..."
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
            />
          </div>
          <button onClick={handleSearch} disabled={loading || !query.trim()} className={buttonStyle.primary + ' min-w-[80px]'}>
            {loading ? <icons.Refresh className="w-4 h-4 animate-spin" /> : '搜索'}
          </button>
        </div>

        {/* 模式切换 */}
        <div className="flex gap-2">
          {searchModes.map(m => (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                mode === m.key
                  ? 'bg-primary text-white'
                  : 'bg-muted text-muted-foreground hover:text-foreground'
              }`}
              title={m.desc}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* 搜索结果 */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {!hasSearched && (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
            <icons.Search className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-sm">输入关键词开始搜索知识库</p>
            <p className="text-xs mt-1 opacity-60">支持关键词检索、语义检索和 RAG 智能问答</p>
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-20">
            <icons.Refresh className="w-6 h-6 animate-spin text-primary" />
            <span className="ml-2 text-sm text-muted-foreground">搜索中...</span>
          </div>
        )}

        {/* RAG 回答 */}
        {ragAnswer && !loading && (
          <div className="mb-6">
            <div className={cardStyle.highlight + ' mb-4'}>
              <div className="flex items-center gap-2 mb-3">
                <icons.Sparkles className="w-4 h-4 text-primary" />
                <span className={heading.section}>AI 回答</span>
              </div>
              <div className="text-sm text-foreground leading-relaxed whitespace-pre-wrap">
                {ragAnswer.answer}
              </div>
              {ragAnswer.chunks_used && (
                <p className="text-xs text-muted-foreground mt-3">
                  参考了 {ragAnswer.chunks_used} 个知识片段
                </p>
              )}
            </div>
            {ragAnswer.sources?.length > 0 && (
              <div>
                <h3 className={heading.card + ' mb-2'}>参考来源</h3>
                <div className="space-y-2">
                  {ragAnswer.sources.map((s: any, i: number) => (
                    <div key={i} className="text-xs p-2 rounded-lg bg-muted/50 text-muted-foreground">
                      {s.title || s.source || `来源 ${i + 1}`}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 常规结果列表 */}
        {hasSearched && !loading && results.length > 0 && (
          <div>
            <p className="text-xs text-muted-foreground mb-3">
              找到 {results.length} 条结果
            </p>
            <div className="space-y-3">
              {results.map((r, i) => (
                <div key={r.id || i} className={cardStyle.interactive}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex-1 min-w-0">
                      <h3 className={heading.card + ' mb-1'}>
                        {r.title ? highlightText(r.title, query) : `结果 ${i + 1}`}
                      </h3>
                      <p className="text-xs text-muted-foreground line-clamp-3">
                        {highlightText(r.content?.slice(0, 300) || '', query)}
                      </p>
                      {r.source && (
                        <div className="flex items-center gap-1 mt-2">
                          <icons.Link className="w-3 h-3 text-muted-foreground" />
                          <span className="text-xs text-muted-foreground">{r.source}</span>
                        </div>
                      )}
                    </div>
                    {r.score !== undefined && (
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        r.score > 0.8 ? statusColor.success : r.score > 0.5 ? statusColor.warning : statusColor.neutral
                      }`}>
                        {(r.score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {hasSearched && !loading && results.length === 0 && !ragAnswer && (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <icons.FileSearch className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm">未找到相关结果</p>
            <p className="text-xs mt-1">尝试使用不同的关键词或切换搜索模式</p>
          </div>
        )}
      </div>
    </div>
  )
}
