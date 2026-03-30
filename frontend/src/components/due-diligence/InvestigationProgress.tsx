/**
 * InvestigationProgress - 多阶段调查进度可视化
 *
 * 三个阶段：数据采集 → 交叉验证 → 综合分析
 * 包含超时自动 fallback、手动跳过、耗时计时等机制
 */
import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, heading, iconSize, buttonStyle } from '@/lib/design-tokens'
import { CrawlProgressBar } from '../lic/CrawlProgressBar'

export interface InvestigationStage {
  id: 'collection' | 'verification' | 'synthesis'
  label: string
  status: 'pending' | 'active' | 'done' | 'error'
  agents?: AgentStatus[]
}

export interface AgentStatus {
  name: string
  label: string
  status: 'pending' | 'loading' | 'done' | 'error'
  data?: any
}

export interface ConflictInfo {
  description: string
  agents: string[]
}

interface InvestigationProgressProps {
  companyName: string
  stages: InvestigationStage[]
  conflicts: ConflictInfo[]
  consensus?: { risk_level: string; confidence: number; debate_summary: string }
  licTaskId?: string
  /** 手动跳过调查，触发 fallback */
  onSkip?: () => void
  /** 取消调查 */
  onCancel?: () => void
  /** 调查开始的时间戳 */
  startTime?: number
}

const stageIcons = {
  collection: icons.Database,
  verification: icons.CheckCheck,
  synthesis: icons.Sparkles,
}

const AGENT_DESCRIPTIONS: Record<string, string> = {
  due_diligence: '正在检索工商登记、股权结构等基础信息...',
  risk_assessor: '正在分析经营异常、行政处罚等风险信号...',
  compliance: '正在核验信用评级、合规记录...',
}

const SKIP_THRESHOLD_SEC = 15

export function InvestigationProgress({
  companyName,
  stages,
  conflicts,
  consensus,
  licTaskId,
  onSkip,
  onCancel,
  startTime,
}: InvestigationProgressProps) {
  const currentStage = stages.find(s => s.status === 'active') || stages[0]
  const completedCount = stages.filter(s => s.status === 'done').length

  // 耗时计时
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval>>()
  const effectiveStart = startTime || Date.now()

  useEffect(() => {
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - effectiveStart) / 1000))
    }, 1000)
    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [effectiveStart])

  const showSkip = elapsed >= SKIP_THRESHOLD_SEC && onSkip
  const isLongWait = elapsed >= 30

  const formatElapsed = (s: number) => {
    const min = Math.floor(s / 60)
    const sec = s % 60
    return min > 0 ? `${min}:${sec.toString().padStart(2, '0')}` : `${sec}s`
  }

  return (
    <div className="flex items-center justify-center py-6 lg:py-10">
      <div className="w-full max-w-2xl space-y-6">
        {/* 标题 */}
        <div className="text-center">
          <div className="w-16 h-16 mx-auto bg-primary/5 rounded-full flex items-center justify-center mb-4">
            <icons.Building2 className={`${iconSize.xl} text-primary animate-pulse`} />
          </div>
          <h3 className={`${heading.section} text-lg`}>正在调查: {companyName}</h3>
          <p className="text-xs text-muted-foreground mt-1">
            多 Agent 协同调查引擎 · {completedCount}/{stages.length} 阶段完成
            <span className="ml-2 text-muted-foreground/60">已耗时 {formatElapsed(elapsed)}</span>
          </p>
        </div>

        {/* 阶段进度条 */}
        <div className="flex items-center gap-2 px-4">
          {stages.map((stage, i) => {
            const StageIcon = stageIcons[stage.id]
            return (
              <div key={stage.id} className="flex items-center flex-1">
                <div className={`flex items-center gap-2 px-3 py-2 rounded-lg flex-1 transition-all ${
                  stage.status === 'done' ? 'bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800'
                    : stage.status === 'active' ? 'bg-primary/5 border border-primary/20'
                    : stage.status === 'error' ? 'bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800'
                    : 'bg-muted/50 border border-transparent'
                }`}>
                  {stage.status === 'done' ? (
                    <icons.CheckCircle className="w-4 h-4 text-emerald-500 shrink-0" />
                  ) : stage.status === 'active' ? (
                    <icons.Loader2 className="w-4 h-4 text-primary animate-spin shrink-0" />
                  ) : stage.status === 'error' ? (
                    <icons.XCircle className="w-4 h-4 text-red-500 shrink-0" />
                  ) : (
                    <StageIcon className="w-4 h-4 text-muted-foreground shrink-0" />
                  )}
                  <span className={`text-xs font-medium truncate ${
                    stage.status === 'done' ? 'text-emerald-600 dark:text-emerald-400'
                      : stage.status === 'active' ? 'text-primary'
                      : 'text-muted-foreground'
                  }`}>
                    {stage.label}
                  </span>
                </div>
                {i < stages.length - 1 && (
                  <icons.ChevronRight className="w-4 h-4 text-muted-foreground mx-1 shrink-0" />
                )}
              </div>
            )
          })}
        </div>

        {/* LIC 爬取进度 */}
        {licTaskId && (
          <CrawlProgressBar taskId={licTaskId} />
        )}

        {/* 当前阶段 Agent 详情 */}
        <AnimatePresence mode="wait">
          {currentStage?.agents && currentStage.agents.length > 0 && (
            <motion.div
              key={currentStage.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`${cardStyle.base} rounded-2xl space-y-3`}
            >
              <p className="text-xs text-muted-foreground font-medium">
                {currentStage.id === 'collection' ? 'Agent 并行数据采集' :
                 currentStage.id === 'verification' ? 'Agent 交叉验证中' :
                 '共识辩论综合中'}
              </p>
              {currentStage.agents.map((agent, index) => (
                <motion.div
                  key={agent.name}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.08 }}
                  className="flex items-center gap-3"
                >
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center ${
                    agent.status === 'done' ? 'bg-emerald-50 dark:bg-emerald-950/30' :
                    agent.status === 'error' ? 'bg-red-50 dark:bg-red-950/30' :
                    agent.status === 'loading' ? 'bg-primary/5' :
                    'bg-muted'
                  }`}>
                    {agent.status === 'loading' ? (
                      <icons.Loader2 className="w-4 h-4 text-primary animate-spin" />
                    ) : agent.status === 'done' ? (
                      <icons.CheckCircle className="w-4 h-4 text-emerald-500" />
                    ) : agent.status === 'error' ? (
                      <icons.XCircle className="w-4 h-4 text-red-500" />
                    ) : (
                      <span className="w-2 h-2 bg-muted-foreground rounded-full" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium ${
                      agent.status === 'done' ? 'text-emerald-600 dark:text-emerald-400' :
                      agent.status === 'error' ? 'text-red-500' :
                      agent.status === 'loading' ? 'text-primary' :
                      'text-muted-foreground'
                    }`}>
                      {agent.label}
                    </p>
                    {agent.status === 'loading' && (
                      <p className="text-[10px] text-muted-foreground">
                        {AGENT_DESCRIPTIONS[agent.name] || '正在分析数据...'}
                      </p>
                    )}
                    {agent.status === 'done' && (
                      <p className="text-[10px] text-emerald-500">分析完成</p>
                    )}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* 长时间等待提示 + 跳过 / 取消按钮 */}
        <AnimatePresence>
          {showSkip && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="bg-muted/50 border border-border rounded-xl p-4"
            >
              <div className="flex items-start gap-3">
                <icons.Clock className="w-4 h-4 text-muted-foreground mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0 space-y-2">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {isLongWait
                      ? 'AI 调查耗时较长，可能是 LLM 服务响应较慢。您可以跳过流式查询，改用快速查询模式获取结果。'
                      : '等待中... 如果长时间无响应，可以切换为快速查询模式。'}
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={onSkip}
                      className={`${buttonStyle.primary} text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5`}
                    >
                      <icons.Zap className="w-3 h-3" />
                      快速查询模式
                    </button>
                    {onCancel && (
                      <button
                        onClick={onCancel}
                        className={`${buttonStyle.ghost} text-xs px-3 py-1.5 rounded-lg`}
                      >
                        取消调查
                      </button>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* 冲突发现 */}
        {conflicts.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl p-4 space-y-2"
          >
            <div className="flex items-center gap-2">
              <icons.AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">发现 {conflicts.length} 处分析冲突</span>
            </div>
            {conflicts.map((c, i) => (
              <p key={i} className="text-xs text-amber-700 dark:text-amber-300 ml-6">
                {c.description}（{c.agents.join(' vs ')})
              </p>
            ))}
          </motion.div>
        )}

        {/* 共识结果 */}
        {consensus && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-primary/5 border border-primary/20 rounded-xl p-4"
          >
            <div className="flex items-center gap-2 mb-2">
              <icons.Sparkles className="w-4 h-4 text-primary" />
              <span className="text-xs font-semibold text-primary">共识结论（置信度 {(consensus.confidence * 100).toFixed(0)}%）</span>
            </div>
            <p className="text-sm text-foreground leading-relaxed">{consensus.debate_summary}</p>
          </motion.div>
        )}
      </div>
    </div>
  )
}
