/**
 * AdminEnterprise — 后台企业管理页面
 *
 * Tab1 "企业信息": 组织列表 + 基本信息
 * Tab2 "合规监控": 合规自检历史 + 风险趋势图
 * Tab3 "风险概览": 企业风险评分卡 + 待处理风险项
 */
import { useState } from 'react'
import { PageContainer } from '@/components/ui/PageContainer'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { icons } from '@/lib/icons'
import { cardStyle, heading, statusBadge, buttonStyle, inputStyle } from '@/lib/design-tokens'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend,
} from 'recharts'

// @mock-data FALLBACK
const MOCK_ENTERPRISES = [
  { id: '1', name: '北京科技有限公司', industry: '信息技术', scale: '500-1000人', contact: '张总', phone: '138****1234', riskScore: 82, status: 'active' as const },
  { id: '2', name: '上海贸易集团', industry: '国际贸易', scale: '1000-5000人', contact: '李总', phone: '139****5678', riskScore: 65, status: 'active' as const },
  { id: '3', name: '深圳智能制造', industry: '高端制造', scale: '200-500人', contact: '王总', phone: '137****9012', riskScore: 91, status: 'active' as const },
  { id: '4', name: '广州生物医药', industry: '生物医药', scale: '100-200人', contact: '陈总', phone: '136****3456', riskScore: 45, status: 'inactive' as const },
  { id: '5', name: '杭州电商科技', industry: '电子商务', scale: '500-1000人', contact: '赵总', phone: '135****7890', riskScore: 73, status: 'active' as const },
]

// @mock-data FALLBACK
const MOCK_COMPLIANCE_HISTORY = [
  { date: '2025-10', score: 78, issues: 5 },
  { date: '2025-11', score: 82, issues: 3 },
  { date: '2025-12', score: 80, issues: 4 },
  { date: '2026-01', score: 85, issues: 2 },
  { date: '2026-02', score: 88, issues: 1 },
  { date: '2026-03', score: 86, issues: 2 },
]

// @mock-data FALLBACK
const MOCK_COMPLIANCE_RECORDS = [
  { id: '1', enterprise: '北京科技有限公司', type: '数据安全', result: 'pass' as const, date: '2026-03-15', issues: 0 },
  { id: '2', enterprise: '上海贸易集团', type: '反洗钱', result: 'warning' as const, date: '2026-03-12', issues: 2 },
  { id: '3', enterprise: '深圳智能制造', type: '环保合规', result: 'pass' as const, date: '2026-03-10', issues: 0 },
  { id: '4', enterprise: '广州生物医药', type: 'GMP认证', result: 'fail' as const, date: '2026-03-08', issues: 5 },
  { id: '5', enterprise: '杭州电商科技', type: '消费者保护', result: 'warning' as const, date: '2026-03-05', issues: 1 },
]

// @mock-data FALLBACK
const MOCK_RISK_ITEMS = [
  { id: '1', enterprise: '广州生物医药', category: 'GMP合规', level: 'critical' as const, description: 'GMP认证即将到期，需在30天内续期', deadline: '2026-04-08' },
  { id: '2', enterprise: '上海贸易集团', category: '反洗钱', level: 'high' as const, description: '大额交易异常预警，需人工复核', deadline: '2026-03-30' },
  { id: '3', enterprise: '杭州电商科技', category: '消费者保护', level: 'medium' as const, description: '退货政策不符合新规要求', deadline: '2026-04-15' },
  { id: '4', enterprise: '北京科技有限公司', category: '数据安全', level: 'low' as const, description: '隐私协议版本待更新', deadline: '2026-05-01' },
]

// @mock-data FALLBACK
const MOCK_RISK_TREND = [
  { month: '10月', critical: 2, high: 5, medium: 8, low: 12 },
  { month: '11月', critical: 1, high: 4, medium: 6, low: 10 },
  { month: '12月', critical: 3, high: 3, medium: 7, low: 9 },
  { month: '01月', critical: 1, high: 2, medium: 5, low: 11 },
  { month: '02月', critical: 0, high: 3, medium: 4, low: 8 },
  { month: '03月', critical: 1, high: 2, medium: 3, low: 7 },
]

function EnterpriseInfoTab() {
  const [search, setSearch] = useState('')

  const filtered = MOCK_ENTERPRISES.filter(e =>
    e.name.includes(search) || e.industry.includes(search)
  )

  const riskScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-600 dark:text-emerald-400'
    if (score >= 60) return 'text-amber-600 dark:text-amber-400'
    return 'text-red-600 dark:text-red-400'
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-3">
        <div className="flex-1 relative">
          <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="搜索企业名称或行业..."
            className={inputStyle.search + ' pl-10'}
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map(ent => (
          <div key={ent.id} className={cardStyle.interactive}>
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className={heading.card}>{ent.name}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">{ent.industry} / {ent.scale}</p>
              </div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${ent.status === 'active' ? statusBadge.success : statusBadge.neutral}`}>
                {ent.status === 'active' ? '活跃' : '非活跃'}
              </span>
            </div>
            <div className="space-y-1.5 text-xs text-muted-foreground">
              <div className="flex items-center gap-1.5">
                <icons.User className="w-3 h-3" />
                <span>联系人：{ent.contact}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <icons.Phone className="w-3 h-3" />
                <span>{ent.phone}</span>
              </div>
            </div>
            <div className="mt-3 pt-3 border-t border-border/50 flex items-center justify-between">
              <span className="text-xs text-muted-foreground">风险评分</span>
              <span className={`text-lg font-bold ${riskScoreColor(ent.riskScore)}`}>{ent.riskScore}</span>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
          <icons.Building2 className="w-12 h-12 mb-3 opacity-20" />
          <p className="text-sm">未找到匹配的企业</p>
        </div>
      )}
    </div>
  )
}

function ComplianceTab() {
  const resultStyle = (result: 'pass' | 'warning' | 'fail') => {
    switch (result) {
      case 'pass': return statusBadge.success
      case 'warning': return statusBadge.warning
      case 'fail': return statusBadge.error
    }
  }

  const resultLabel = (result: 'pass' | 'warning' | 'fail') => {
    switch (result) {
      case 'pass': return '通过'
      case 'warning': return '警告'
      case 'fail': return '不通过'
    }
  }

  return (
    <div className="space-y-6">
      {/* 合规趋势 */}
      <div className={cardStyle.base}>
        <h3 className={heading.section + ' mb-4'}>合规评分趋势</h3>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={MOCK_COMPLIANCE_HISTORY}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
            <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="score" name="合规评分" stroke="hsl(var(--primary))" strokeWidth={2} />
            <Line type="monotone" dataKey="issues" name="问题数" stroke="#FF9500" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 自检记录 */}
      <div className={cardStyle.base}>
        <h3 className={heading.section + ' mb-4'}>合规自检记录</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-3 pr-4 font-medium text-muted-foreground">企业</th>
                <th className="pb-3 pr-4 font-medium text-muted-foreground">检查类型</th>
                <th className="pb-3 pr-4 font-medium text-muted-foreground">日期</th>
                <th className="pb-3 pr-4 font-medium text-muted-foreground">问题数</th>
                <th className="pb-3 font-medium text-muted-foreground">结果</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_COMPLIANCE_RECORDS.map(record => (
                <tr key={record.id} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="py-3 pr-4 font-medium">{record.enterprise}</td>
                  <td className="py-3 pr-4 text-muted-foreground">{record.type}</td>
                  <td className="py-3 pr-4 text-xs text-muted-foreground">{record.date}</td>
                  <td className="py-3 pr-4">{record.issues}</td>
                  <td className="py-3">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${resultStyle(record.result)}`}>
                      {resultLabel(record.result)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function RiskOverviewTab() {
  const levelStyle = (level: 'critical' | 'high' | 'medium' | 'low') => {
    switch (level) {
      case 'critical': return statusBadge.error
      case 'high': return statusBadge.warning
      case 'medium': return statusBadge.info
      case 'low': return statusBadge.neutral
    }
  }

  const levelLabel = (level: 'critical' | 'high' | 'medium' | 'low') => {
    switch (level) {
      case 'critical': return '严重'
      case 'high': return '高'
      case 'medium': return '中'
      case 'low': return '低'
    }
  }

  // 风险评分卡
  const riskCounts = {
    critical: MOCK_RISK_ITEMS.filter(r => r.level === 'critical').length,
    high: MOCK_RISK_ITEMS.filter(r => r.level === 'high').length,
    medium: MOCK_RISK_ITEMS.filter(r => r.level === 'medium').length,
    low: MOCK_RISK_ITEMS.filter(r => r.level === 'low').length,
  }

  return (
    <div className="space-y-6">
      {/* 风险评分卡 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className={cardStyle.base + ' text-center border-red-200 dark:border-red-800'}>
          <p className="text-3xl font-bold text-red-600 dark:text-red-400">{riskCounts.critical}</p>
          <p className="text-xs text-muted-foreground mt-1">严重风险</p>
        </div>
        <div className={cardStyle.base + ' text-center border-amber-200 dark:border-amber-800'}>
          <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">{riskCounts.high}</p>
          <p className="text-xs text-muted-foreground mt-1">高风险</p>
        </div>
        <div className={cardStyle.base + ' text-center'}>
          <p className="text-3xl font-bold text-primary">{riskCounts.medium}</p>
          <p className="text-xs text-muted-foreground mt-1">中风险</p>
        </div>
        <div className={cardStyle.base + ' text-center'}>
          <p className="text-3xl font-bold text-muted-foreground">{riskCounts.low}</p>
          <p className="text-xs text-muted-foreground mt-1">低风险</p>
        </div>
      </div>

      {/* 风险趋势 */}
      <div className={cardStyle.base}>
        <h3 className={heading.section + ' mb-4'}>风险趋势</h3>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={MOCK_RISK_TREND}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
            <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" />
            <Tooltip />
            <Legend />
            <Bar dataKey="critical" name="严重" fill="#FF3B30" radius={[2, 2, 0, 0]} />
            <Bar dataKey="high" name="高" fill="#FF9500" radius={[2, 2, 0, 0]} />
            <Bar dataKey="medium" name="中" fill="hsl(var(--primary))" radius={[2, 2, 0, 0]} />
            <Bar dataKey="low" name="低" fill="#8E8E93" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* 待处理风险项 */}
      <div className={cardStyle.base}>
        <h3 className={heading.section + ' mb-4'}>待处理风险项</h3>
        <div className="space-y-3">
          {MOCK_RISK_ITEMS.map(item => (
            <div key={item.id} className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 hover:bg-muted/50 transition-colors">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium shrink-0 mt-0.5 ${levelStyle(item.level)}`}>
                {levelLabel(item.level)}
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-foreground">{item.enterprise}</p>
                  <span className="text-xs text-muted-foreground">/ {item.category}</span>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
              </div>
              <div className="text-right shrink-0">
                <p className="text-xs text-muted-foreground">截止日期</p>
                <p className="text-xs font-medium text-foreground">{item.deadline}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function AdminEnterprise() {
  return (
    <PageContainer title="企业管理" description="企业信息、合规监控与风险概览">
      <Tabs defaultValue="info">
        <TabsList>
          <TabsTrigger value="info">
            <icons.Building2 className="w-4 h-4 mr-1.5" />
            企业信息
          </TabsTrigger>
          <TabsTrigger value="compliance">
            <icons.ShieldCheck className="w-4 h-4 mr-1.5" />
            合规监控
          </TabsTrigger>
          <TabsTrigger value="risk">
            <icons.AlertTriangle className="w-4 h-4 mr-1.5" />
            风险概览
          </TabsTrigger>
        </TabsList>

        <TabsContent value="info">
          <EnterpriseInfoTab />
        </TabsContent>

        <TabsContent value="compliance">
          <ComplianceTab />
        </TabsContent>

        <TabsContent value="risk">
          <RiskOverviewTab />
        </TabsContent>
      </Tabs>
    </PageContainer>
  )
}
