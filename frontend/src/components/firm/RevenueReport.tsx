/**
 * RevenueReport - 收入报表看板
 *
 * - KPI 卡片行(4个): 总收入、已收款、待收款、平均客单价
 * - 月度收入趋势 LineChart
 * - 收入来源分布 PieChart（按案件类型）
 * - 律师业绩排行 Table
 * 全部 mock 数据，使用 recharts + design-tokens
 */

import {
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { icons } from '@/lib/icons'
import { cardStyle, heading, iconSize, chartColors, statusBadge } from '@/lib/design-tokens'
import { Badge } from '@/components/ui/badge'

// @mock-data FALLBACK: 后端就绪后从 /firm/revenue-report API 获取

const KPI_DATA = {
  totalRevenue: 2856000,
  paidAmount: 2142000,
  pendingAmount: 714000,
  avgOrderValue: 47600,
}

const MONTHLY_DATA = [
  { month: '2025/10', amount: 186000 },
  { month: '2025/11', amount: 215000 },
  { month: '2025/12', amount: 248000 },
  { month: '2026/01', amount: 312000 },
  { month: '2026/02', amount: 278000 },
  { month: '2026/03', amount: 356000 },
]

const SOURCE_DATA = [
  { name: '合同纠纷', value: 980000 },
  { name: '知识产权', value: 650000 },
  { name: '劳动争议', value: 420000 },
  { name: '公司治理', value: 380000 },
  { name: '刑事辩护', value: 260000 },
  { name: '其他', value: 166000 },
]

const LAWYER_RANKING = [
  { rank: 1, name: '张明远', hours: 486, revenue: 583200, cases: 12 },
  { rank: 2, name: '陈伟达', hours: 412, revenue: 494400, cases: 9 },
  { rank: 3, name: '刘婉清', hours: 368, revenue: 441600, cases: 8 },
  { rank: 4, name: '黄建国', hours: 324, revenue: 356400, cases: 11 },
  { rank: 5, name: '李思晨', hours: 298, revenue: 298000, cases: 7 },
  { rank: 6, name: '杨丽娜', hours: 276, revenue: 276000, cases: 6 },
  { rank: 7, name: '王浩然', hours: 245, revenue: 220500, cases: 5 },
  { rank: 8, name: '韩思远', hours: 218, revenue: 185300, cases: 4 },
]

// ========== 工具函数 ==========

function formatCurrency(value: number): string {
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}万`
  }
  return value.toLocaleString()
}

// ========== KPI 卡片 ==========

interface KpiCardProps {
  icon: React.ReactNode
  label: string
  value: string
  sub?: string
  colorClass?: string
}

function KpiCard({ icon, label, value, sub, colorClass = 'text-foreground' }: KpiCardProps) {
  return (
    <div className={cardStyle.base}>
      <div className="flex items-center gap-2 mb-2">
        {icon}
        <span className={heading.muted}>{label}</span>
      </div>
      <p className={`text-2xl font-bold ${colorClass}`}>{value}</p>
      {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
    </div>
  )
}

// ========== 组件 ==========

export default function RevenueReport() {
  return (
    <div className="space-y-6">
      {/* KPI 卡片行 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          icon={<icons.DollarSign className={`${iconSize.md} text-primary`} />}
          label="总收入"
          value={`${formatCurrency(KPI_DATA.totalRevenue)}元`}
          sub="本年累计"
          colorClass="text-foreground"
        />
        <KpiCard
          icon={<icons.CheckCircle className={`${iconSize.md} text-emerald-600 dark:text-emerald-400`} />}
          label="已收款"
          value={`${formatCurrency(KPI_DATA.paidAmount)}元`}
          sub={`回款率 ${((KPI_DATA.paidAmount / KPI_DATA.totalRevenue) * 100).toFixed(0)}%`}
          colorClass="text-emerald-600 dark:text-emerald-400"
        />
        <KpiCard
          icon={<icons.Clock className={`${iconSize.md} text-amber-600 dark:text-amber-400`} />}
          label="待收款"
          value={`${formatCurrency(KPI_DATA.pendingAmount)}元`}
          sub="含已发送和逾期"
          colorClass="text-amber-600 dark:text-amber-400"
        />
        <KpiCard
          icon={<icons.TrendingUp className={`${iconSize.md} text-primary`} />}
          label="平均客单价"
          value={`${formatCurrency(KPI_DATA.avgOrderValue)}元`}
          sub="同比 +12.3%"
          colorClass="text-primary"
        />
      </div>

      {/* 图表行 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* 月度收入趋势 */}
        <div className={`${cardStyle.base} lg:col-span-2`}>
          <h3 className={`${heading.section} mb-4`}>月度收入趋势</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={MONTHLY_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="month"
                tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
              />
              <YAxis
                tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
                axisLine={{ stroke: 'hsl(var(--border))' }}
                tickFormatter={v => `${(v / 10000).toFixed(0)}万`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '13px',
                }}
                formatter={(value: number) => [`${formatCurrency(value)}元`, '收入']}
              />
              <Line
                type="monotone"
                dataKey="amount"
                stroke={chartColors[0]}
                strokeWidth={2}
                dot={{ r: 4, fill: chartColors[0] }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 收入来源分布 */}
        <div className={cardStyle.base}>
          <h3 className={`${heading.section} mb-4`}>收入来源分布</h3>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={SOURCE_DATA}
                cx="50%"
                cy="45%"
                innerRadius={55}
                outerRadius={90}
                paddingAngle={2}
                dataKey="value"
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ strokeWidth: 1 }}
              >
                {SOURCE_DATA.map((_, idx) => (
                  <Cell key={idx} fill={chartColors[idx % chartColors.length]} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{
                  backgroundColor: 'hsl(var(--background))',
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '8px',
                  fontSize: '13px',
                }}
                formatter={(value: number) => [`${formatCurrency(value)}元`, '收入']}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 律师业绩排行 */}
      <div className={cardStyle.base}>
        <h3 className={`${heading.section} mb-4`}>律师业绩排行</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-16">排名</TableHead>
              <TableHead>律师</TableHead>
              <TableHead className="text-right">工时 (h)</TableHead>
              <TableHead className="text-right">收入</TableHead>
              <TableHead className="text-right">案件数</TableHead>
              <TableHead className="text-right">时均产出</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {LAWYER_RANKING.map(row => {
              const hourlyRate = row.hours > 0 ? Math.round(row.revenue / row.hours) : 0
              return (
                <TableRow key={row.rank}>
                  <TableCell>
                    {row.rank <= 3 ? (
                      <Badge
                        variant="outline"
                        className={`text-xs px-1.5 py-0 ${
                          row.rank === 1
                            ? statusBadge.warning
                            : row.rank === 2
                              ? statusBadge.neutral
                              : statusBadge.info
                        }`}
                      >
                        {row.rank === 1 ? '🥇' : row.rank === 2 ? '🥈' : '🥉'}
                      </Badge>
                    ) : (
                      <span className="text-sm text-muted-foreground ml-2">{row.rank}</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <div className="w-7 h-7 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary">
                        {row.name.slice(0, 1)}
                      </div>
                      <span className="text-sm font-medium text-foreground">{row.name}</span>
                    </div>
                  </TableCell>
                  <TableCell className="text-right text-sm">{row.hours}</TableCell>
                  <TableCell className="text-right text-sm font-medium text-foreground">
                    {formatCurrency(row.revenue)}元
                  </TableCell>
                  <TableCell className="text-right text-sm">{row.cases}</TableCell>
                  <TableCell className="text-right text-sm text-muted-foreground">
                    {hourlyRate}元/h
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
