/**
 * InvestigationOverview - 调查概览仪表板
 * 显示关键指标卡片 + 最新预警 + 快速操作
 */
import { useMemo } from 'react'
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, heading, statusBadge, buttonStyle } from '@/lib/design-tokens'
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, Tooltip,
} from 'recharts'

interface InvestigationOverviewProps {
  data: {
    basicInfo?: any
    risk?: any
    litigation?: any
    credit?: any
  }
  companyName: string
  onNavigate: (section: string) => void
  onGenerateReport: () => void
}

const CREDIT_RATING_ORDER = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C', 'D']

function isGoodRating(rating?: string): boolean {
  if (!rating) return true
  const idx = CREDIT_RATING_ORDER.indexOf(rating.toUpperCase())
  return idx >= 0 && idx <= 2 // AAA, AA, A
}

/** 基于调查数据自动生成预警列表 */
function deriveAlerts(data: InvestigationOverviewProps['data']): Array<{ id: string; severity: string; title: string; time: string }> {
  const alerts: Array<{ id: string; severity: string; title: string; time: string }> = []
  const risk = data.risk || {}
  const litigation = data.litigation || {}
  const credit = data.credit || {}

  if ((risk.compliance_risk || 0) > 50) {
    alerts.push({ id: 'r1', severity: 'critical', title: `合规风险评分 ${risk.compliance_risk}，需重点关注`, time: '实时' })
  }
  if ((risk.operation_risk || 0) > 60) {
    alerts.push({ id: 'r2', severity: 'critical', title: `经营风险评分 ${risk.operation_risk}，建议深入排查`, time: '实时' })
  }
  const caseCount = litigation.total_cases || litigation.major_cases?.length || 0
  if (caseCount > 0) {
    alerts.push({ id: 'l1', severity: caseCount > 5 ? 'critical' : 'warning', title: `涉诉 ${caseCount} 起，被告 ${litigation.as_defendant || 0} 起`, time: '调查发现' })
  }
  if ((credit.administrative_penalties || 0) > 0) {
    alerts.push({ id: 'c1', severity: 'warning', title: `行政处罚 ${credit.administrative_penalties} 条`, time: '调查发现' })
  }
  if (!isGoodRating(credit.credit_rating) && credit.credit_rating) {
    alerts.push({ id: 'c2', severity: 'warning', title: `信用评级 ${credit.credit_rating}，低于 A 级`, time: '调查发现' })
  }
  if (risk.risk_points?.length > 0) {
    alerts.push({ id: 'rp', severity: 'info', title: `发现 ${risk.risk_points.length} 个风险要点`, time: '调查发现' })
  }
  return alerts
}

export function InvestigationOverview({ data, companyName, onNavigate, onGenerateReport }: InvestigationOverviewProps) {
  const riskScore = data.risk
    ? Math.round(
        ((data.risk.operation_risk || 0) +
          (data.risk.litigation_risk || 0) +
          (data.risk.credit_risk || 0) +
          (data.risk.compliance_risk || 0) +
          (data.risk.relation_risk || 0)) / 5
      )
    : 0

  const riskLevel = riskScore > 60 ? 'high' : riskScore > 35 ? 'medium' : 'low'
  const riskConfig = {
    high: { label: '高风险', color: 'text-red-600 dark:text-red-400', bg: 'bg-red-50 dark:bg-red-950/30', border: 'border-red-200 dark:border-red-800' },
    medium: { label: '中风险', color: 'text-amber-600 dark:text-amber-400', bg: 'bg-amber-50 dark:bg-amber-950/30', border: 'border-amber-200 dark:border-amber-800' },
    low: { label: '低风险', color: 'text-emerald-600 dark:text-emerald-400', bg: 'bg-emerald-50 dark:bg-emerald-950/30', border: 'border-emerald-200 dark:border-emerald-800' },
  }

  const rc = riskConfig[riskLevel]

  const litigationCount = data.litigation?.total_cases || data.litigation?.major_cases?.length || 0
  const creditRating = data.credit?.credit_rating || 'N/A'
  const creditIsGood = isGoodRating(data.credit?.credit_rating)

  const alerts = useMemo(() => deriveAlerts(data), [data])

  const radarData = data.risk ? [
    { dimension: '经营风险', score: data.risk.operation_risk || 0 },
    { dimension: '诉讼风险', score: data.risk.litigation_risk || 0 },
    { dimension: '信用风险', score: data.risk.credit_risk || 0 },
    { dimension: '合规风险', score: data.risk.compliance_risk || 0 },
    { dimension: '关联风险', score: data.risk.relation_risk || 0 },
  ] : []

  const kpiCards = [
    {
      label: '风险等级',
      value: rc.label,
      sub: `综合评分 ${riskScore}`,
      icon: icons.ShieldAlert,
      color: rc.color,
      bg: rc.bg,
      border: rc.border,
      section: 'risk',
    },
    {
      label: '涉诉案件',
      value: `${litigationCount} 起`,
      sub: `被告 ${data.litigation?.as_defendant || 0} / 原告 ${data.litigation?.as_plaintiff || 0}`,
      icon: icons.Scale,
      color: litigationCount > 3 ? 'text-red-600 dark:text-red-400' : 'text-foreground',
      bg: litigationCount > 3 ? 'bg-red-50 dark:bg-red-950/30' : 'bg-muted/50',
      border: litigationCount > 3 ? 'border-red-200 dark:border-red-800' : 'border-border',
      section: 'litigation',
    },
    {
      label: '信用评级',
      value: creditRating,
      sub: `行政处罚 ${data.credit?.administrative_penalties || 0} 条`,
      icon: icons.FileCheck,
      color: creditIsGood ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400',
      bg: creditIsGood ? 'bg-emerald-50 dark:bg-emerald-950/30' : 'bg-amber-50 dark:bg-amber-950/30',
      border: creditIsGood ? 'border-emerald-200 dark:border-emerald-800' : 'border-amber-200 dark:border-amber-800',
      section: 'compliance',
    },
    {
      label: '预警数量',
      value: `${alerts.length} 条`,
      sub: `严重 ${alerts.filter(a => a.severity === 'critical').length} / 警告 ${alerts.filter(a => a.severity === 'warning').length}`,
      icon: icons.Bell,
      color: alerts.some(a => a.severity === 'critical') ? 'text-red-600 dark:text-red-400' : 'text-emerald-600 dark:text-emerald-400',
      bg: alerts.some(a => a.severity === 'critical') ? 'bg-red-50 dark:bg-red-950/30' : 'bg-emerald-50 dark:bg-emerald-950/30',
      border: alerts.some(a => a.severity === 'critical') ? 'border-red-200 dark:border-red-800' : 'border-emerald-200 dark:border-emerald-800',
      section: 'sentiment',
    },
  ]

  // 数据质量标识
  const dataQuality = data.risk?.data_quality
  const dataSources = data.risk?.data_sources || []
  const dataQualityLabel = dataQuality === 'real' ? '真实数据' : dataQuality === 'public' ? '公开数据' : dataQuality === 'estimated' ? 'AI 估算' : '综合'
  const dataQualityColor = dataQuality === 'real' ? 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/30' : dataQuality === 'public' ? 'text-primary bg-primary/5' : 'text-muted-foreground bg-muted'

  return (
    <div className="space-y-6">
      {/* 数据质量标识 */}
      {dataQuality && (
        <div className="flex items-center gap-2 text-xs">
          <span className={`px-2 py-0.5 rounded-full font-medium ${dataQualityColor}`}>
            {dataQualityLabel}
          </span>
          {dataSources.length > 0 && (
            <span className="text-muted-foreground">
              数据来源：{dataSources.join('、')}
            </span>
          )}
        </div>
      )}

      {/* KPI 卡片 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiCards.map((card, i) => {
          const Icon = card.icon
          return (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => onNavigate(card.section)}
              className={`p-4 rounded-xl border cursor-pointer hover:shadow-md transition-all ${card.bg} ${card.border}`}
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={`w-4 h-4 ${card.color}`} />
                <span className="text-xs text-muted-foreground font-medium">{card.label}</span>
              </div>
              <p className={`text-xl font-bold ${card.color}`}>{card.value}</p>
              <p className="text-xs text-muted-foreground mt-1">{card.sub}</p>
            </motion.div>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 风险雷达图 */}
        {radarData.length > 0 && (
          <div className={`${cardStyle.base} lg:col-span-2`}>
            <h3 className={`${heading.section} mb-4`}>五维风险评估</h3>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData}>
                <PolarGrid strokeDasharray="3 3" />
                <PolarAngleAxis dataKey="dimension" tick={{ fontSize: 12 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar
                  name="风险评分"
                  dataKey="score"
                  stroke="hsl(var(--primary))"
                  fill="hsl(var(--primary))"
                  fillOpacity={0.2}
                  strokeWidth={2}
                />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* 最新预警 + 快速操作 */}
        <div className="space-y-4">
          <div className={cardStyle.base}>
            <h3 className={`${heading.section} mb-3`}>最新预警</h3>
            <div className="space-y-2">
              {alerts.slice(0, 4).map((alert, i) => (
                <div key={alert.id || i} className="flex items-start gap-2 p-2 rounded-lg bg-muted/30">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0 mt-0.5 ${
                    alert.severity === 'critical' ? statusBadge.error
                      : alert.severity === 'warning' ? statusBadge.warning
                      : statusBadge.info
                  }`}>
                    {alert.severity === 'critical' ? '严重' : alert.severity === 'warning' ? '警告' : '提示'}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium text-foreground line-clamp-1">{alert.title}</p>
                    <p className="text-[10px] text-muted-foreground">{alert.time}</p>
                  </div>
                </div>
              ))}
              {alerts.length === 0 && (
                <p className="text-xs text-muted-foreground text-center py-4">暂无预警信息</p>
              )}
            </div>
          </div>

          <div className={cardStyle.base}>
            <h3 className={`${heading.section} mb-3`}>快速操作</h3>
            <div className="space-y-2">
              <button onClick={onGenerateReport} className={`${buttonStyle.primary} w-full justify-center flex items-center gap-2`}>
                <icons.FileText className="w-4 h-4" />
                生成调查报告
              </button>
              <button onClick={() => onNavigate('simulation')} className={`${buttonStyle.secondary} w-full justify-center flex items-center gap-2`}>
                <icons.Cpu className="w-4 h-4" />
                风险推演分析
              </button>
              <button onClick={() => onNavigate('graph')} className={`${buttonStyle.ghost} w-full justify-center flex items-center gap-2`}>
                <icons.Network className="w-4 h-4" />
                查看关系图谱
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
