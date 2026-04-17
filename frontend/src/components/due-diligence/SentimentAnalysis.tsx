/**
 * SentimentAnalysis - 风险分析面板（风险评估模块）
 *
 * 展示五维风险雷达图 + 风险要点/建议
 * 数据来源：调查数据中的 risk 维度
 */
import { motion } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, complianceScoreColors, heading } from '@/lib/design-tokens'
import {
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Cell,
} from 'recharts'

interface SentimentAnalysisProps {
  data?: {
    operation_risk?: number
    litigation_risk?: number
    credit_risk?: number
    [key: string]: any  // 支持 data_quality, data_sources 等扩展字段
    compliance_risk?: number
    relation_risk?: number
    overall_rating?: string
    risk_points?: string[]
    recommendations?: string[]
  }
}

export function SentimentAnalysis({ data }: SentimentAnalysisProps) {
  const riskDimensions = [
    { dimension: '经营风险', score: data?.operation_risk || 0, key: 'operation' },
    { dimension: '诉讼风险', score: data?.litigation_risk || 0, key: 'litigation' },
    { dimension: '信用风险', score: data?.credit_risk || 0, key: 'credit' },
    { dimension: '合规风险', score: data?.compliance_risk || 0, key: 'compliance' },
    { dimension: '关联风险', score: data?.relation_risk || 0, key: 'relation' },
  ]

  const avgRisk = riskDimensions.reduce((s, d) => s + d.score, 0) / 5
  const riskLabel = data?.overall_rating === 'low' ? '低风险' : data?.overall_rating === 'high' ? '高风险' : avgRisk > 60 ? '高风险' : avgRisk > 35 ? '中风险' : '低风险'
  const riskColor = avgRisk > 60 ? 'text-destructive' : avgRisk > 35 ? 'text-warning' : 'text-success'

  const barColor = (score: number) => score > 60 ? complianceScoreColors.poor : score > 35 ? complianceScoreColors.medium : complianceScoreColors.excellent

  const hasRiskData = riskDimensions.some(d => d.score > 0)

  const riskPoints = data?.risk_points || []
  const recommendations = data?.recommendations || []

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className={cardStyle.base}
    >
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <icons.ShieldAlert className="w-5 h-5 text-primary" />
          <div>
            <h3 className={heading.section}>五维风险分析</h3>
            <p className={heading.muted}>
              {data?.data_quality === 'real' ? '基于真实政府公开数据' : data?.data_quality === 'public' ? '基于公开工商数据' : '基于多维度风险评估模型'}
            </p>
          </div>
        </div>
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${
          avgRisk > 60 ? 'bg-destructive/10 text-destructive dark:bg-destructive/20'
            : avgRisk > 35 ? 'bg-warning/10 text-warning dark:bg-warning/20'
            : 'bg-success/10 text-success dark:bg-success/20'
        }`}>
          {riskLabel} · 均分 {Math.round(avgRisk)}
        </span>
      </div>

      {hasRiskData ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 雷达图 */}
          <div>
            <ResponsiveContainer width="100%" height={240}>
              <RadarChart data={riskDimensions}>
                <PolarGrid stroke="hsl(var(--border))" />
                <PolarAngleAxis dataKey="dimension" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 10 }} />
                <Radar name="风险评分" dataKey="score" stroke="hsl(var(--primary))" strokeWidth={2} fill="hsl(var(--primary))" fillOpacity={0.2} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* 柱状图 */}
          <div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={riskDimensions} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 10 }} stroke="hsl(var(--muted-foreground))" />
                <YAxis type="category" dataKey="dimension" tick={{ fontSize: 11 }} stroke="hsl(var(--muted-foreground))" width={70} />
                <Tooltip />
                <Bar dataKey="score" name="评分" radius={[0, 4, 4, 0]}>
                  {riskDimensions.map((d, i) => (
                    <Cell key={i} fill={barColor(d.score)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
          <icons.ShieldAlert className="w-10 h-10 mb-3 opacity-20" />
          <p className="text-sm">暂无风险评估数据</p>
        </div>
      )}

      {/* 风险要点 + 建议 */}
      {(riskPoints.length > 0 || recommendations.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-6">
          {riskPoints.length > 0 && (
            <div>
              <h4 className={`${heading.card} mb-3 flex items-center gap-1.5`}>
                <icons.AlertTriangle className="w-3.5 h-3.5 text-warning" />
                风险要点
              </h4>
              <div className="space-y-2">
                {riskPoints.map((point, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.08 }}
                    className="flex items-start gap-2 p-2.5 rounded-lg bg-warning/10 dark:bg-warning/20 border border-warning/20"
                  >
                    <span className="w-5 h-5 rounded-full bg-warning text-warning-foreground text-[10px] flex items-center justify-center shrink-0 mt-0.5 font-semibold">
                      {i + 1}
                    </span>
                    <p className="text-xs leading-relaxed text-foreground">{point}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          )}

          {recommendations.length > 0 && (
            <div>
              <h4 className={`${heading.card} mb-3 flex items-center gap-1.5`}>
                <icons.Sparkles className="w-3.5 h-3.5 text-primary" />
                应对建议
              </h4>
              <div className="space-y-2">
                {recommendations.map((rec, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.08 }}
                    className="flex items-start gap-2 p-2.5 rounded-lg bg-primary/5 border border-primary/10"
                  >
                    <span className="w-5 h-5 rounded-full bg-primary text-primary-foreground text-[10px] flex items-center justify-center shrink-0 mt-0.5 font-bold">
                      {i + 1}
                    </span>
                    <p className="text-xs leading-relaxed text-foreground">{rec}</p>
                  </motion.div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </motion.div>
  )
}
