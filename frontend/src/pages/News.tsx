import { useState, useEffect, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, heading, statusBadge, buttonStyle, iconSize } from '@/lib/design-tokens'
import { sentimentApi, type SentimentRecord } from '@/lib/api'
import { PageContainer } from '@/components/ui/PageContainer'

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

const categoryConfig: Record<string, { label: string; badge: string }> = {
  regulation: { label: '法规动态', badge: statusBadge.info },
  case_law: { label: '判例速递', badge: statusBadge.success },
  policy: { label: '政策解读', badge: statusBadge.warning },
  industry: { label: '行业资讯', badge: statusBadge.neutral },
}

const mockNews: NewsItem[] = [
  { id: '1', title: '最高人民法院发布民法典合同编司法解释（二）', summary: '针对合同效力、合同履行、合同解除等方面的法律适用问题作出详细规定，进一步明确了违约责任的认定标准。', source: '最高人民法院', category: 'regulation', publishedAt: '2026-03-17', tags: ['民法典', '合同'], isImportant: true },
  { id: '2', title: '知名互联网企业竞业限制纠纷案终审判决', summary: '法院认定竞业限制补偿金过低不影响协议效力，但可作为违约金调整的参考因素。', source: '北京高院', category: 'case_law', publishedAt: '2026-03-16', tags: ['劳动法', '竞业限制'], isImportant: true },
  { id: '3', title: '国务院发布数据安全管理新规', summary: '新规要求企业建立数据分类分级保护制度，对跨境数据传输提出更严格的合规要求。', source: '国务院', category: 'policy', publishedAt: '2026-03-15', tags: ['数据安全', '合规'], isImportant: true },
  { id: '4', title: '2026年法律科技行业融资报告', summary: '一季度法律科技领域融资总额同比增长45%，AI合同审查赛道最受资本青睐。', source: '法律科技研究院', category: 'industry', publishedAt: '2026-03-14', tags: ['法律科技', '融资'], isImportant: false },
  { id: '5', title: '新修订的公司法配套细则出台', summary: '明确了注册资本认缴制改实缴制的过渡期安排及存量公司调整方案。', source: '市场监管总局', category: 'regulation', publishedAt: '2026-03-13', tags: ['公司法', '注册资本'], isImportant: false },
  { id: '6', title: '全国首例AI生成内容著作权案判决', summary: '法院认定AI工具使用者对生成内容享有一定权利，但需满足独创性要求。', source: '北京互联网法院', category: 'case_law', publishedAt: '2026-03-12', tags: ['AI', '著作权'], isImportant: false },
  { id: '7', title: '反垄断法执法指南更新', summary: '针对平台经济领域的反垄断执法标准进行了细化，明确算法合谋的认定方式。', source: '反垄断局', category: 'policy', publishedAt: '2026-03-11', tags: ['反垄断', '平台经济'], isImportant: false },
  { id: '8', title: '律师事务所数字化转型白皮书', summary: '调研显示超过60%的律所已启动数字化转型，智能文档管理和AI辅助是首要投入方向。', source: '律协报告', category: 'industry', publishedAt: '2026-03-10', tags: ['数字化', '律所管理'], isImportant: false },
  { id: '9', title: '个人信息保护法实施细则公布', summary: '对敏感个人信息处理、自动化决策、个人信息跨境提供等关键条款给出实操指引。', source: '网信办', category: 'regulation', publishedAt: '2026-03-09', tags: ['个保法', '隐私'], isImportant: false },
  { id: '10', title: '环境公益诉讼新规解读', summary: '扩大了环境公益诉讼的起诉主体范围，引入惩罚性赔偿机制。', source: '最高检', category: 'policy', publishedAt: '2026-03-08', tags: ['环保', '公益诉讼'], isImportant: false },
]

// 将后端舆情记录转换为新闻条目
function recordToNewsItem(record: SentimentRecord): NewsItem {
  const categoryMap: Record<string, Exclude<NewsCategory, 'all'>> = {
    positive: 'industry',
    negative: 'case_law',
    neutral: 'regulation',
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

/* ---------- 筛选栏 ---------- */
function FilterBar({ category, setCategory }: { category: NewsCategory; setCategory: (c: NewsCategory) => void }) {
  const tabs: { key: NewsCategory; label: string }[] = [
    { key: 'all', label: '全部' },
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
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:text-foreground'
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
            {cfg?.label || '资讯'}
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
          <icons.Zap className={`${iconSize.sm} text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5`} />
        )}
        <div className="flex-1 min-w-0">
          {/* 分类 + 日期 */}
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-xs px-2 py-0.5 rounded-md ${cfg?.badge || statusBadge.neutral}`}>
              {cfg?.label || '资讯'}
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
  const [news, setNews] = useState<NewsItem[]>(mockNews)
  const [category, setCategory] = useState<NewsCategory>('all')
  const [selectedNews, setSelectedNews] = useState<NewsItem | null>(null)
  const [loading, setLoading] = useState(true)

  const loadNews = useCallback(async () => {
    setLoading(true)
    try {
      const data = await sentimentApi.listRecords({ page: 1, page_size: 50 })
      if (data.items?.length > 0) {
        setNews(data.items.map(recordToNewsItem))
      } else {
        setNews(mockNews)
      }
    } catch {
      setNews(mockNews)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadNews() }, [loadNews])

  const filtered = category === 'all' ? news : news.filter(n => n.category === category)

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
        <div className="flex items-center justify-center py-20">
          <icons.Refresh className={`${iconSize.lg} animate-spin text-primary`} />
          <span className="ml-2 text-sm text-muted-foreground">加载资讯...</span>
        </div>
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
