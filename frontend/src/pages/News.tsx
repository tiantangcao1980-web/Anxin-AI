import { useState, useEffect, useCallback } from'react'
import { icons } from'@/lib/icons'
import { cardStyle, heading, statusBadge, buttonStyle, iconSize } from'@/lib/design-tokens'
import { sentimentApi, type SentimentRecord } from'@/lib/api'
import { toast } from'sonner'
import { PageContainer } from'@/components/ui/PageContainer'
import { ErrorState, LoadingState } from'@/components/common'

type NewsCategory ='all' |'regulation' |'case_law' |'policy' |'industry'

interface NewsItem {
 id: string
 title: string
 summary: string
 source: string
 category: Exclude<NewsCategory,'all'>
 publishedAt: string
 tags: string[]
 isImportant: boolean
}

const categoryConfig: Record<string, { label: string; badge: string }> = {
 regulation: { label:'法规动态', badge: statusBadge.info },
 case_law: { label:'判例速递', badge: statusBadge.success },
 policy: { label:'政策解读', badge: statusBadge.warning },
 industry: { label:'行业资讯', badge: statusBadge.neutral },
}

// 将后端舆情记录转换为新闻条目
function recordToNewsItem(record: SentimentRecord): NewsItem {
 const categoryMap: Record<string, Exclude<NewsCategory,'all'>> = {
 positive:'industry',
 negative:'case_law',
 neutral:'regulation',
 }
 return {
 id: record.id,
 title: record.title || record.keyword,
 summary: record.summary || record.content?.slice(0, 200) ||'',
 source: record.source || record.source_type ||'系统采集',
 category: categoryMap[record.sentiment_type] ||'regulation',
 publishedAt: record.created_at?.split('T')[0] ||'',
 tags: [record.keyword, record.risk_level ==='high' ?'高风险' :''].filter(Boolean),
 isImportant: record.risk_level ==='high' || record.sentiment_score > 0.8,
 }
}

/* ---------- 筛选栏 ---------- */
function FilterBar({ category, setCategory }: { category: NewsCategory; setCategory: (c: NewsCategory) => void }) {
 const tabs: { key: NewsCategory; label: string }[] = [
 { key:'all', label:'全部' },
 ...Object.entries(categoryConfig).map(([k, v]) => ({ key: k as NewsCategory, label: v.label })),
 ]

 return (
 <div className="flex flex-wrap gap-2">
 {tabs.map(c => (
 <button
 key={c.key}
 onClick={() => setCategory(c.key)}
 className={`${buttonStyle.sm} ${
 category === c.key
 ?'bg-primary text-primary-foreground'
 :'bg-muted text-muted-foreground hover:text-foreground'
 }`}
 >
 {c.label}
 </button>
 ))}
 </div>
 )
}

/* ---------- 新闻详情视图 ---------- */
function NewsDetail({ item, onBack }: { item: NewsItem; onBack: () => void }) {
 const cfg = categoryConfig[item.category]

 return (
 <PageContainer
 title={item.title}
 actions={
 <button onClick={onBack} className={buttonStyle.ghost}>
 <icons.ArrowLeft className={`${iconSize.sm} mr-1.5 inline-block`} />
 返回列表
 </button>
 }
 >
 <div className="max-w-3xl space-y-6">
 {/* 元信息 */}
 <div className="flex items-center gap-3">
 <span className={`text-xs px-2 py-0.5 rounded-md ${cfg?.badge || statusBadge.neutral}`}>
 {cfg?.label ||'资讯'}
 </span>
 <span className="text-xs text-muted-foreground">{item.source}</span>
 <span className="text-xs text-muted-foreground">{item.publishedAt}</span>
 </div>

 {/* 正文 */}
 <p className="text-sm text-foreground leading-relaxed">{item.summary}</p>

 {/* 标签 */}
 {item.tags.length > 0 && (
 <div className="flex flex-wrap gap-2">
 {item.tags.map(tag => (
 <span key={tag} className={`text-xs px-2 py-0.5 rounded-md ${statusBadge.neutral}`}>
 {tag}
 </span>
 ))}
 </div>
 )}
 </div>
 </PageContainer>
 )
}

/* ---------- 新闻卡片 ---------- */
function NewsCard({ item, onClick }: { item: NewsItem; onClick: () => void }) {
 const cfg = categoryConfig[item.category]

 return (
 <div onClick={onClick} className={cardStyle.interactive}>
 <div className="flex items-start gap-3">
 {item.isImportant && (
 <icons.Zap className={`${iconSize.sm} text-warning flex-shrink-0 mt-0.5`} />
 )}
 <div className="flex-1 min-w-0">
 {/* 分类 + 日期 */}
 <div className="flex items-center gap-2 mb-1.5">
 <span className={`text-xs px-2 py-0.5 rounded-md ${cfg?.badge || statusBadge.neutral}`}>
 {cfg?.label ||'资讯'}
 </span>
 <span className="text-xs text-muted-foreground">{item.publishedAt}</span>
 </div>

 {/* 标题 */}
 <h3 className={`${heading.card} mb-1`}>{item.title}</h3>

 {/* 摘要 */}
 <p className="text-xs text-muted-foreground line-clamp-2">{item.summary}</p>

 {/* 来源 + 标签 */}
 <div className="flex flex-wrap items-center gap-2 mt-2">
 <span className="text-xs text-muted-foreground">{item.source}</span>
 {item.tags.slice(0, 3).map(tag => (
 <span key={tag} className={`text-xs px-1.5 py-0.5 rounded-md ${statusBadge.neutral}`}>
 {tag}
 </span>
 ))}
 </div>
 </div>
 </div>
 </div>
 )
}

/* ---------- 主页面 ---------- */
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
 } catch (e: any) {
 setNews([])
 setError(e.message ||'资讯加载失败')
 toast.error(e.message ||'资讯加载失败')
 } finally {
 setLoading(false)
 }
 }, [])

 useEffect(() => { loadNews() }, [loadNews])

 const filtered = category ==='all' ? news : news.filter(n => n.category === category)

 /* 详情视图 */
 if (selectedNews) {
 return <NewsDetail item={selectedNews} onBack={() => setSelectedNews(null)} />
 }

 /* 列表视图：PageHeader -> FilterBar -> Content */
 return (
 <PageContainer
 title="司法资讯"
 toolbar={<FilterBar category={category} setCategory={setCategory} />}
 >
 {loading ? (
 <LoadingState variant="page" text="加载资讯..." />
 ) : error ? (
 <ErrorState title="资讯加载失败" message={error} onRetry={loadNews} />
 ) : filtered.length === 0 ? (
 <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
 <icons.FileSearch className={`${iconSize['2xl']} mb-3 opacity-30`} />
 <p className="text-sm">暂无该分类的资讯</p>
 </div>
 ) : (
 <div className="space-y-4 max-w-3xl">
 {filtered.map(item => (
 <NewsCard key={item.id} item={item} onClick={() => setSelectedNews(item)} />
 ))}
 </div>
 )}
 </PageContainer>
 )
}
