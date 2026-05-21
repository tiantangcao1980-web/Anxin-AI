/**
 * News · 司法资讯（Editorial Luxury 改造 · Phase 1.9 News）
 *
 * 旧版用 PageContainer + cardStyle.interactive + statusBadge 色块 chip。
 * 新版：ListPageTemplate + DetailPageTemplate + tone-only category 标识。
 */

import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { Zap, ArrowLeft, FileSearch } from 'lucide-react'

import { ListPageTemplate, ListPageStatus } from '@/components/ui/ListPageTemplate'
import { DetailPageTemplate } from '@/components/ui/PageTemplates'
import { sentimentApi, type SentimentRecord } from '@/lib/api'
import { cn } from '@/components/ui/utils'

type NewsCategory = 'all' | 'regulation' | 'case_law' | 'policy' | 'industry'

interface NewsItem {
  id: string
  title: string
  summary: string
  source: string
  category: Exclude<NewsCategory, 'all'>
  publishedAt: string
  tags: string[]
  isImportant: boolean
}

const CATEGORY_META: Record<Exclude<NewsCategory, 'all'>, { label: string; labelEn: string }> = {
  regulation: { label: '法规动态', labelEn: 'Regulation' },
  case_law:   { label: '判例速递', labelEn: 'Case Law' },
  policy:     { label: '政策解读', labelEn: 'Policy' },
  industry:   { label: '行业资讯', labelEn: 'Industry' },
}

function recordToNewsItem(record: SentimentRecord): NewsItem {
  const categoryMap: Record<string, Exclude<NewsCategory, 'all'>> = {
    positive: 'industry',
    negative: 'case_law',
    neutral:  'regulation',
  }
  return {
    id: record.id,
    title: record.title || record.keyword,
    summary: record.summary || record.content?.slice(0, 200) || '',
    source: record.source || record.source_type || '系统采集',
    category: categoryMap[record.sentiment_type] || 'regulation',
    publishedAt: record.created_at?.split('T')[0] || '',
    tags: [record.keyword, record.risk_level === 'high' ? '高风险' : ''].filter(Boolean),
    isImportant: record.risk_level === 'high' || record.sentiment_score > 0.8,
  }
}

function CategoryTracker({ category }: { category: Exclude<NewsCategory, 'all'> }) {
  const meta = CATEGORY_META[category]
  return (
    <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
      <span>{meta.labelEn}</span>
      <span className="text-foreground/30" aria-hidden>·</span>
      <span className="normal-case tracking-normal text-foreground/70">{meta.label}</span>
    </span>
  )
}

/* ------------ 详情视图 ------------ */
function NewsDetail({ item, onBack }: { item: NewsItem; onBack: () => void }) {
  return (
    <DetailPageTemplate
      tracker={['Knowledge', '司法资讯', CATEGORY_META[item.category].label]}
      title={item.title}
      description={`${item.source} · ${item.publishedAt}`}
      actions={
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="w-4 h-4 stroke-[1.5]" />
          <span>返回列表</span>
        </button>
      }
    >
      <article className="max-w-[68ch] space-y-6">
        <div className="flex flex-wrap items-center gap-4">
          <CategoryTracker category={item.category} />
          {item.isImportant && (
            <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.16em] text-warning">
              <Zap className="w-3 h-3 stroke-[1.5]" />
              <span>Highlight</span>
            </span>
          )}
        </div>
        <p className="text-[15px] leading-[1.85] text-foreground/90">{item.summary}</p>
        {item.tags.length > 0 && (
          <footer className="pt-6 border-t border-border flex flex-wrap items-center gap-4">
            <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
              Tags
            </span>
            {item.tags.map((tag) => (
              <span key={tag} className="text-[13px] text-foreground/80 border border-border px-2.5 py-0.5">
                {tag}
              </span>
            ))}
          </footer>
        )}
      </article>
    </DetailPageTemplate>
  )
}

/* ------------ 主页面 ------------ */
export default function News() {
  const [news, setNews] = useState<NewsItem[]>([])
  const [category, setCategory] = useState<NewsCategory>('all')
  const [selectedNews, setSelectedNews] = useState<NewsItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadNews = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await sentimentApi.listRecords({ page: 1, page_size: 50 })
      setNews((data.items || []).map(recordToNewsItem))
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '资讯加载失败'
      setNews([])
      setError(msg)
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadNews() }, [loadNews])

  const filtered = category === 'all' ? news : news.filter((n) => n.category === category)

  if (selectedNews) {
    return <NewsDetail item={selectedNews} onBack={() => setSelectedNews(null)} />
  }

  // tab 计数（含全部）
  const counts: Record<NewsCategory, number> = {
    all: news.length,
    regulation: news.filter((n) => n.category === 'regulation').length,
    case_law:   news.filter((n) => n.category === 'case_law').length,
    policy:     news.filter((n) => n.category === 'policy').length,
    industry:   news.filter((n) => n.category === 'industry').length,
  }

  return (
    <ListPageTemplate
      tracker={['Knowledge', '司法资讯']}
      title="司法资讯"
      description="法规 · 判例 · 政策 · 行业 — AI 监测，按需阅读。"
      tabs={[
        { key: 'all',        label: '全部',     count: counts.all },
        { key: 'regulation', label: '法规动态', count: counts.regulation },
        { key: 'case_law',   label: '判例速递', count: counts.case_law },
        { key: 'policy',     label: '政策解读', count: counts.policy },
        { key: 'industry',   label: '行业资讯', count: counts.industry },
      ]}
      activeTab={category}
      onTabChange={(k) => setCategory(k as NewsCategory)}
      loading={loading}
      error={error}
      empty={!loading && !error && filtered.length === 0}
      emptyState={
        <ListPageStatus
          tracker="Empty"
          title={category === 'all' ? '暂无资讯' : '该分类暂无资讯'}
          description={category === 'all' ? '系统正在采集，稍后再试。' : '试试切换其他分类。'}
          action={
            category === 'all' && (
              <button
                onClick={() => void loadNews()}
                className="bg-primary hover:bg-primary-700 text-primary-foreground px-5 py-2.5 text-[14px] font-medium transition-colors"
              >
                重新加载
              </button>
            )
          }
        />
      }
    >
      {filtered.map((item, i) => (
        <li key={item.id}>
          <button
            type="button"
            onClick={() => setSelectedNews(item)}
            className={cn(
              'group w-full text-left flex items-start gap-6 py-6 px-3 -mx-3 border-b border-border/60',
              'transition-colors hover:bg-surface-2/40',
            )}
          >
            <span className="font-serif text-[13px] text-muted-foreground w-10 shrink-0 pt-1 tabular-nums">
              {String(i + 1).padStart(3, '0')}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-baseline gap-3 flex-wrap mb-2">
                <CategoryTracker category={item.category} />
                <span className="text-[11px] text-muted-foreground tabular-nums">{item.publishedAt}</span>
                {item.isImportant && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-medium uppercase tracking-[0.16em] text-warning">
                    <Zap className="w-3 h-3 stroke-[1.5]" />
                    重点
                  </span>
                )}
              </div>
              <h3 className="font-serif text-[18px] leading-tight text-foreground">{item.title}</h3>
              <p className="text-[13px] text-muted-foreground line-clamp-2 mt-2 leading-relaxed">
                {item.summary}
              </p>
              <div className="text-[12px] text-muted-foreground mt-3 flex items-center gap-3 flex-wrap">
                <span>{item.source}</span>
                {item.tags.slice(0, 3).map((tag) => (
                  <span key={tag} className="text-foreground/60">· {tag}</span>
                ))}
              </div>
            </div>
          </button>
        </li>
      ))}
    </ListPageTemplate>
  )
}
