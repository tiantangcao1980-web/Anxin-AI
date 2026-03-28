import { useState, useEffect, useMemo } from 'react'
import { icons } from '@/lib/icons'
import { toast } from 'sonner'
import { cardStyle, buttonStyle, heading, iconSize, statusBadge, chartColors } from '@/lib/design-tokens'
import { PageContainer, PageSection } from '@/components/ui/PageContainer'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis, CartesianGrid, Legend,
} from 'recharts'

// ====================================================================
// @mock-data FALLBACK: 后端就绪后从 API 获取
// ====================================================================

interface ConversationSummary {
  id: string
  title: string
  date: string
  topics: string[]
  summary: string
  fullSummary: string
  sentiment: 'positive' | 'neutral' | 'negative'
  todoCount: number
  todos: string[]
  legalDomains: string[]
}

interface FeedbackItem {
  id: string
  date: string
  rating: number
  type: string
  content: string
}

interface StatsCard {
  label: string
  value: string | number
  icon: keyof typeof icons
  trend?: string
  trendUp?: boolean
}

const mockStats: StatsCard[] = [
  { label: '总对话数', value: '2,846', icon: 'Chat', trend: '+12%', trendUp: true },
  { label: '本月新增', value: '342', icon: 'Calendar', trend: '+8%', trendUp: true },
  { label: '平均满意度', value: '4.6', icon: 'Star', trend: '+0.2', trendUp: true },
  { label: '待办事项', value: 28, icon: 'Tasks', trend: '-3', trendUp: false },
]

const mockSummaries: ConversationSummary[] = [
  {
    id: 'conv-001',
    title: '劳动合同解除咨询',
    date: '2026-03-28',
    topics: ['劳动法', '合同解除', '经济补偿'],
    summary: '客户咨询关于员工不胜任工作的合同解除流程，涉及N+1补偿标准和合规操作步骤...',
    fullSummary: '客户咨询关于员工不胜任工作的合同解除流程。AI 助手详细说明了《劳动合同法》第40条相关规定，包括培训或调岗义务、经济补偿N+1标准、解除通知要求等。建议客户保留完整的绩效考核记录和培训记录。',
    sentiment: 'neutral',
    todoCount: 3,
    todos: ['整理员工绩效考核记录', '准备培训方案文件', '咨询法律顾问确认流程'],
    legalDomains: ['劳动法', '人力资源'],
  },
  {
    id: 'conv-002',
    title: '股权架构设计咨询',
    date: '2026-03-27',
    topics: ['公司法', '股权结构', '期权池'],
    summary: '初创企业咨询 A 轮融资前的股权架构设计，包括期权池设置和投资者权利...',
    fullSummary: '初创企业咨询 A 轮融资前的股权架构设计方案。AI 助手分析了创始人持股比例、期权池大小（建议10-15%）、投资者优先权条款等关键议题，并提供了标准 Term Sheet 的主要条款解读。',
    sentiment: 'positive',
    todoCount: 2,
    todos: ['起草期权激励方案', '审查现有股东协议'],
    legalDomains: ['公司法', '投融资'],
  },
  {
    id: 'conv-003',
    title: '合同违约纠纷分析',
    date: '2026-03-26',
    topics: ['合同法', '违约责任', '损害赔偿'],
    summary: '供应商延迟交货构成违约，分析违约金与实际损失的赔偿方案...',
    fullSummary: '客户反映供应商延迟交货30天构成违约。AI 助手分析了合同中的违约金条款（日千分之三），计算违约金总额，评估了违约金是否过高的法律风险，并建议发送正式催告函。',
    sentiment: 'negative',
    todoCount: 4,
    todos: ['计算违约金总额', '起草催告函', '收集损失证据', '评估诉讼成本'],
    legalDomains: ['合同法', '民事诉讼'],
  },
  {
    id: 'conv-004',
    title: '数据隐私合规审查',
    date: '2026-03-25',
    topics: ['数据保护', 'PIPL', '隐私政策'],
    summary: '企业数据处理流程的隐私合规审查，涉及个人信息保护法合规...',
    fullSummary: '企业委托对其 APP 数据处理流程进行隐私合规审查。AI 助手检查了隐私政策、用户同意机制、数据跨境传输、第三方 SDK 数据收集等合规要点，指出了三处需整改的问题。',
    sentiment: 'neutral',
    todoCount: 3,
    todos: ['修改隐私政策文本', '增加明示同意弹窗', '审查第三方 SDK 清单'],
    legalDomains: ['数据保护', '网络安全'],
  },
  {
    id: 'conv-005',
    title: '商标侵权分析',
    date: '2026-03-24',
    topics: ['知识产权', '商标法', '侵权认定'],
    summary: '竞品使用近似商标的侵权可能性分析及维权建议...',
    fullSummary: '客户发现竞品使用与自己注册商标高度近似的标识。AI 助手从商标近似度、商品类别、消费者混淆可能性等角度进行了分析，建议收集侵权证据并考虑向市场监管局投诉。',
    sentiment: 'positive',
    todoCount: 2,
    todos: ['收集侵权证据截图', '委托代理人发送律师函'],
    legalDomains: ['知识产权', '商标法'],
  },
]

const mockRatingDistribution = [
  { rating: '1星', count: 12 },
  { rating: '2星', count: 28 },
  { rating: '3星', count: 56 },
  { rating: '4星', count: 189 },
  { rating: '5星', count: 245 },
]

const mockFeedbackTypes = [
  { name: '非常有帮助', value: 420, color: chartColors[1] },
  { name: '基本满意', value: 180, color: chartColors[0] },
  { name: '回答不够详细', value: 65, color: chartColors[2] },
  { name: '回答有误', value: 23, color: chartColors[4] },
  { name: '响应太慢', value: 18, color: chartColors[3] },
  { name: '其他', value: 34, color: chartColors[5] },
]

const mockSatisfactionTrend = Array.from({ length: 30 }, (_, i) => ({
  date: `03/${String(i + 1).padStart(2, '0')}`,
  满意度: +(3.8 + Math.random() * 1.2).toFixed(1),
}))

const mockFeedbackList: FeedbackItem[] = [
  { id: 'fb-1', date: '2026-03-28', rating: 5, type: '非常有帮助', content: '合同审查建议非常专业，帮我发现了好几个风险点' },
  { id: 'fb-2', date: '2026-03-27', rating: 4, type: '基本满意', content: '法律咨询回答详细，但希望能引用更多具体法条' },
  { id: 'fb-3', date: '2026-03-27', rating: 5, type: '非常有帮助', content: '尽职调查报告质量很高，节省了大量时间' },
  { id: 'fb-4', date: '2026-03-26', rating: 3, type: '回答不够详细', content: '对于跨境交易的法律分析还需要更详细' },
  { id: 'fb-5', date: '2026-03-26', rating: 2, type: '回答有误', content: '引用的法条已经修订，需要更新知识库' },
  { id: 'fb-6', date: '2026-03-25', rating: 4, type: '基本满意', content: '劳动仲裁方面的建议很实用' },
]

// ====================================================================

type PageState = 'loading' | 'error' | 'ready'

const sentimentConfig = {
  positive: { label: '积极', color: 'bg-emerald-500' },
  neutral: { label: '中性', color: 'bg-gray-400' },
  negative: { label: '消极', color: 'bg-red-500' },
} as const

export default function ConversationInsights() {
  const [state, setState] = useState<PageState>('loading')
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    const timer = setTimeout(() => setState('ready'), 600)
    return () => clearTimeout(timer)
  }, [])

  const filteredSummaries = useMemo(() => {
    if (!searchQuery.trim()) return mockSummaries
    const q = searchQuery.toLowerCase()
    return mockSummaries.filter(
      s =>
        s.title.toLowerCase().includes(q) ||
        s.summary.toLowerCase().includes(q) ||
        s.topics.some(t => t.toLowerCase().includes(q))
    )
  }, [searchQuery])

  if (state === 'loading') {
    return (
      <PageContainer title="对话洞察" description="AI 对话分析与反馈统计">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
        <Skeleton className="h-96 rounded-xl mt-6" />
      </PageContainer>
    )
  }

  if (state === 'error') {
    return (
      <PageContainer title="对话洞察" description="AI 对话分析与反馈统计">
        <div className={`${cardStyle.base} flex flex-col items-center justify-center py-16`}>
          <icons.AlertCircle className={`${iconSize.xl} text-destructive mb-3`} />
          <p className={heading.section}>加载失败</p>
          <Button className="mt-4" onClick={() => setState('loading')}>
            <icons.Refresh className={iconSize.sm} />
            重试
          </Button>
        </div>
      </PageContainer>
    )
  }

  return (
    <PageContainer title="对话洞察" description="AI 对话分析与反馈统计">
      {/* ===== 顶部统计卡片 ===== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {mockStats.map(stat => {
          const Icon = icons[stat.icon]
          return (
            <div key={stat.label} className={cardStyle.base}>
              <div className="flex items-start justify-between">
                <div>
                  <p className={heading.micro}>{stat.label}</p>
                  <p className="text-2xl font-bold text-foreground mt-1">
                    {stat.label === '平均满意度' ? (
                      <span className="flex items-center gap-1">
                        {stat.value}
                        <icons.Star className="w-5 h-5 text-amber-500 fill-amber-500" />
                      </span>
                    ) : (
                      stat.value
                    )}
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-primary/5">
                  <Icon className={`${iconSize.md} text-primary`} />
                </div>
              </div>
              {stat.trend && (
                <p className={`text-xs mt-2 ${stat.trendUp ? 'text-emerald-600' : 'text-red-600'}`}>
                  {stat.trendUp ? <icons.TrendingUp className="w-3 h-3 inline mr-1" /> : <icons.TrendingDown className="w-3 h-3 inline mr-1" />}
                  {stat.trend} 较上月
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* ===== 主区域 Tabs ===== */}
      <Tabs defaultValue="summaries" className="space-y-4">
        <TabsList>
          <TabsTrigger value="summaries" className="flex items-center gap-1.5 text-sm">
            <icons.FileText className={iconSize.sm} />
            对话摘要
          </TabsTrigger>
          <TabsTrigger value="feedback" className="flex items-center gap-1.5 text-sm">
            <icons.BarChart3 className={iconSize.sm} />
            反馈统计
          </TabsTrigger>
        </TabsList>

        {/* ===== Tab 1: 对话摘要 ===== */}
        <TabsContent value="summaries" className="space-y-4">
          <Input
            className={`${inputStyle.search} max-w-md`}
            placeholder="搜索对话摘要..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />

          <div className="space-y-3">
            {filteredSummaries.map(conv => {
              const isExpanded = expandedId === conv.id
              const sentCfg = sentimentConfig[conv.sentiment]
              return (
                <div key={conv.id} className={cardStyle.base}>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : conv.id)}
                    className="w-full text-left"
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-2.5 h-2.5 rounded-full mt-1.5 shrink-0 ${sentCfg.color}`} title={sentCfg.label} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <p className={heading.card}>{conv.title}</p>
                          <span className={heading.micro}>{conv.date}</span>
                          {conv.todoCount > 0 && (
                            <Badge variant="secondary" className="text-xs">
                              <icons.Tasks className="w-3 h-3 mr-1" />
                              {conv.todoCount}
                            </Badge>
                          )}
                        </div>
                        <div className="flex flex-wrap gap-1 mt-1.5">
                          {conv.topics.map(topic => (
                            <Badge key={topic} variant="outline" className="text-xs">{topic}</Badge>
                          ))}
                        </div>
                        <p className="text-sm text-muted-foreground mt-2 line-clamp-2">{conv.summary}</p>
                      </div>
                      <icons.ChevronDown
                        className={`${iconSize.sm} text-muted-foreground shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                      />
                    </div>
                  </button>

                  {isExpanded && (
                    <div className="mt-4 pt-4 border-t border-border space-y-3 ml-5.5">
                      <div>
                        <p className={heading.card + ' mb-1'}>完整摘要</p>
                        <p className="text-sm text-foreground/80 leading-relaxed">{conv.fullSummary}</p>
                      </div>
                      {conv.todos.length > 0 && (
                        <div>
                          <p className={heading.card + ' mb-1'}>待办事项</p>
                          <ul className="space-y-1">
                            {conv.todos.map((todo, i) => (
                              <li key={i} className="flex items-center gap-2 text-sm text-foreground/80">
                                <icons.Circle className="w-3 h-3 text-muted-foreground shrink-0" />
                                {todo}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1">
                        {conv.legalDomains.map(domain => (
                          <Badge key={domain} className={statusBadge.info + ' text-xs'}>{domain}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )
            })}

            {filteredSummaries.length === 0 && (
              <div className={`${cardStyle.base} text-center py-12`}>
                <icons.Search className={`${iconSize.xl} text-muted-foreground mx-auto mb-3`} />
                <p className={heading.muted}>未找到匹配的对话摘要</p>
              </div>
            )}
          </div>
        </TabsContent>

        {/* ===== Tab 2: 反馈统计 ===== */}
        <TabsContent value="feedback" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 评分分布 */}
            <div className={cardStyle.base}>
              <PageSection title="评分分布">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={mockRatingDistribution}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis dataKey="rating" tick={{ fontSize: 12 }} />
                      <YAxis tick={{ fontSize: 12 }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                      <Bar dataKey="count" name="次数" fill={chartColors[0]} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </PageSection>
            </div>

            {/* 反馈类型分布 */}
            <div className={cardStyle.base}>
              <PageSection title="反馈类型分布">
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={mockFeedbackTypes}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={90}
                        paddingAngle={3}
                        dataKey="value"
                        nameKey="name"
                        label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        labelLine={false}
                      >
                        {mockFeedbackTypes.map((entry, i) => (
                          <Cell key={i} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'hsl(var(--background))',
                          border: '1px solid hsl(var(--border))',
                          borderRadius: '8px',
                          fontSize: '12px',
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </PageSection>
            </div>
          </div>

          {/* 满意度趋势 */}
          <div className={cardStyle.base}>
            <PageSection title="满意度趋势（近30天）">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={mockSatisfactionTrend}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={4} />
                    <YAxis domain={[3, 5]} tick={{ fontSize: 12 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: 'hsl(var(--background))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: '8px',
                        fontSize: '12px',
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="满意度"
                      stroke={chartColors[0]}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </PageSection>
          </div>

          {/* 最新反馈列表 */}
          <div className={cardStyle.base}>
            <PageSection title="最新反馈">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px]">日期</TableHead>
                      <TableHead className="w-[80px]">评分</TableHead>
                      <TableHead className="w-[120px]">类型</TableHead>
                      <TableHead>内容</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {mockFeedbackList.map(fb => (
                      <TableRow key={fb.id}>
                        <TableCell className="text-sm text-muted-foreground">{fb.date}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-0.5">
                            {Array.from({ length: 5 }, (_, i) => (
                              <icons.Star
                                key={i}
                                className={`w-3.5 h-3.5 ${
                                  i < fb.rating ? 'text-amber-500 fill-amber-500' : 'text-muted-foreground/30'
                                }`}
                              />
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className="text-xs">{fb.type}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-foreground/80">{fb.content}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </PageSection>
          </div>
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
