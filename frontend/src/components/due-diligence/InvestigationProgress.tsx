/**
 * InvestigationProgress v2 - 六阶段调查进度可视化
 *
 * 阶段：数据采集 → 深度研究 → 多专家论坛 → 交叉验证 → 综合分析 → 报告生成
 * 包含超时自动 fallback、手动跳过、耗时计时等机制
 *
 * 新增：
 * - 深度研究进度（搜索轮次、反思、关键词优化）
 * - 多专家论坛辩论过程（专家发言、冲突、共识）
 * - 报告生成进度（逐章生成）
 */
import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, heading, iconSize, buttonStyle } from '@/lib/design-tokens'
import { CrawlProgressBar } from '../lic/CrawlProgressBar'

export interface InvestigationStage {
  id: 'collection' | 'deep_research' | 'forum' | 'verification' | 'synthesis' | 'report'
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
  resolved?: boolean
  resolution?: string
}

export interface ResearchProgress {
  currentRound: number
  maxRounds: number
  totalResults: number
  confidence: number
  gaps: string[]
  latestQueries: string[]
  summary: string
}

export interface ForumProgress {
  totalAgents: number
  speechesCompleted: number
  currentSpeaker?: string
  currentRole?: string
  debateRound: number
  conflictsFound: number
  conflictsResolved: number
  speeches: Array<{
    agent: string
    role: string
    riskLevel: string
    confidence: number
    keyFindings: string[]
  }>
}

export interface ReportProgress {
  templateName: string
  totalChapters: number
  completedChapters: number
  currentChapter?: string
}

interface InvestigationProgressProps {
  companyName: string
  stages: InvestigationStage[]
  conflicts: ConflictInfo[]
  consensus?: {
    risk_level: string
    confidence: number
    debate_summary: string
    key_conclusions?: string[]
    action_items?: string[]
    research_rounds?: number
  }
  licTaskId?: string
  onSkip?: () => void
  onCancel?: () => void
  startTime?: number
  // v2 新增
  researchProgress?: ResearchProgress
  forumProgress?: ForumProgress
  reportProgress?: ReportProgress
}

const stageIcons: Record<string, any> = {
  collection: icons.Database,
  deep_research: icons.Search,
  forum: icons.Users,
  verification: icons.CheckCheck,
  synthesis: icons.Sparkles,
  report: icons.FileText,
}

const stageLabels: Record<string, string> = {
  collection: 'Agent 并行数据采集',
  deep_research: '迭代式深度研究',
  forum: '多专家论坛辩论',
  verification: 'Agent 交叉验证',
  synthesis: '共识综合分析',
  report: '调查报告生成',
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
  researchProgress,
  forumProgress,
  reportProgress,
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
        <div className="flex items-center gap-1.5 px-2 overflow-x-auto scrollbar-hide">
          {stages.map((stage, i) => {
            const StageIcon = stageIcons[stage.id] || icons.Circle
            return (
              <div key={stage.id} className="flex items-center flex-1 min-w-0">
                <div className={`flex items-center gap-1.5 px-2.5 py-2 rounded-lg flex-1 transition-all ${
                  stage.status === 'done' ? 'bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800'
                    : stage.status === 'active' ? 'bg-primary/5 border border-primary/20'
                    : stage.status === 'error' ? 'bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800'
                    : 'bg-muted/50 border border-transparent'
                }`}>
                  {stage.status === 'done' ? (
                    <icons.CheckCircle className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                  ) : stage.status === 'active' ? (
                    <icons.Loader2 className="w-3.5 h-3.5 text-primary animate-spin shrink-0" />
                  ) : stage.status === 'error' ? (
                    <icons.XCircle className="w-3.5 h-3.5 text-red-500 shrink-0" />
                  ) : (
                    <StageIcon className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
                  )}
                  <span className={`text-[11px] font-medium truncate ${
                    stage.status === 'done' ? 'text-emerald-600 dark:text-emerald-400'
                      : stage.status === 'active' ? 'text-primary'
                      : 'text-muted-foreground'
                  }`}>
                    {stage.label}
                  </span>
                </div>
                {i < stages.length - 1 && (
                  <icons.ChevronRight className="w-3 h-3 text-muted-foreground mx-0.5 shrink-0" />
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
                {stageLabels[currentStage.id] || currentStage.label}
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

        {/* 深度研究进度 */}
        <AnimatePresence>
          {currentStage?.id === 'deep_research' && researchProgress && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`${cardStyle.base} rounded-2xl space-y-4`}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground font-medium flex items-center gap-2">
                  <icons.Search className="w-3.5 h-3.5" />
                  迭代式深度研究
                </p>
                <span className="text-[10px] text-muted-foreground">
                  第 {researchProgress.currentRound}/{researchProgress.maxRounds} 轮
                </span>
              </div>

              {/* 搜索轮次进度 */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-muted-foreground">搜索结果</span>
                  <span className="font-medium">{researchProgress.totalResults} 条</span>
                </div>
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-muted-foreground">研究信心</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
                      <motion.div
                        className={`h-full rounded-full ${
                          researchProgress.confidence > 0.8 ? 'bg-emerald-500' :
                          researchProgress.confidence > 0.5 ? 'bg-amber-500' : 'bg-red-400'
                        }`}
                        initial={{ width: 0 }}
                        animate={{ width: `${researchProgress.confidence * 100}%` }}
                        transition={{ duration: 0.5 }}
                      />
                    </div>
                    <span className="font-medium">{(researchProgress.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>

              {/* 当前搜索查询 */}
              {researchProgress.latestQueries.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[10px] text-muted-foreground">当前搜索关键词</p>
                  <div className="flex flex-wrap gap-1.5">
                    {researchProgress.latestQueries.map((q, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 bg-primary/5 text-primary rounded-full border border-primary/10">
                        {q}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* 信息缺口 */}
              {researchProgress.gaps.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[10px] text-muted-foreground">待补充信息</p>
                  {researchProgress.gaps.slice(0, 3).map((gap, i) => (
                    <p key={i} className="text-[10px] text-amber-600 dark:text-amber-400 flex items-start gap-1">
                      <icons.AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                      {gap}
                    </p>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* 多专家论坛进度 */}
        <AnimatePresence>
          {currentStage?.id === 'forum' && forumProgress && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`${cardStyle.base} rounded-2xl space-y-4`}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground font-medium flex items-center gap-2">
                  <icons.Users className="w-3.5 h-3.5" />
                  多专家论坛
                </p>
                <span className="text-[10px] text-muted-foreground">
                  {forumProgress.speechesCompleted}/{forumProgress.totalAgents} 位专家已发言
                </span>
              </div>

              {/* 当前发言人 */}
              {forumProgress.currentSpeaker && (
                <div className="flex items-center gap-2 bg-primary/5 rounded-lg px-3 py-2">
                  <icons.Loader2 className="w-3.5 h-3.5 text-primary animate-spin" />
                  <span className="text-xs text-primary font-medium">
                    {forumProgress.currentRole || forumProgress.currentSpeaker} 正在发言...
                  </span>
                </div>
              )}

              {/* 已完成的发言 */}
              {forumProgress.speeches.length > 0 && (
                <div className="space-y-2">
                  {forumProgress.speeches.map((speech, i) => (
                    <motion.div
                      key={speech.agent}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.05 }}
                      className="flex items-start gap-2.5 text-xs"
                    >
                      <div className="w-7 h-7 rounded-full bg-emerald-50 dark:bg-emerald-950/30 flex items-center justify-center shrink-0">
                        <icons.CheckCircle className="w-3.5 h-3.5 text-emerald-500" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-foreground">{speech.role}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                            speech.riskLevel === 'high' ? 'bg-red-50 text-red-600 dark:bg-red-950/30 dark:text-red-400' :
                            speech.riskLevel === 'medium' ? 'bg-amber-50 text-amber-600 dark:bg-amber-950/30 dark:text-amber-400' :
                            'bg-emerald-50 text-emerald-600 dark:bg-emerald-950/30 dark:text-emerald-400'
                          }`}>
                            {speech.riskLevel === 'high' ? '高风险' : speech.riskLevel === 'medium' ? '中风险' : '低风险'}
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            信心 {(speech.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        {speech.keyFindings.length > 0 && (
                          <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">
                            {speech.keyFindings.join(' · ')}
                          </p>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              )}

              {/* 辩论状态 */}
              {forumProgress.debateRound > 0 && (
                <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
                  <icons.MessageSquare className="w-3.5 h-3.5" />
                  <span>辩论第 {forumProgress.debateRound} 轮 · {forumProgress.conflictsResolved}/{forumProgress.conflictsFound} 分歧已解决</span>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* 报告生成进度 */}
        <AnimatePresence>
          {currentStage?.id === 'report' && reportProgress && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`${cardStyle.base} rounded-2xl space-y-3`}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground font-medium flex items-center gap-2">
                  <icons.FileText className="w-3.5 h-3.5" />
                  {reportProgress.templateName}
                </p>
                <span className="text-[10px] text-muted-foreground">
                  {reportProgress.completedChapters}/{reportProgress.totalChapters} 章
                </span>
              </div>
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-primary rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${(reportProgress.completedChapters / reportProgress.totalChapters) * 100}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              {reportProgress.currentChapter && (
                <p className="text-[10px] text-muted-foreground flex items-center gap-1.5">
                  <icons.Loader2 className="w-3 h-3 animate-spin" />
                  正在撰写：{reportProgress.currentChapter}
                </p>
              )}
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
              <span className="text-xs font-semibold text-amber-700 dark:text-amber-300">
                发现 {conflicts.length} 处分析冲突
              </span>
            </div>
            {conflicts.map((c, i) => (
              <div key={i} className="ml-6 space-y-0.5">
                <p className="text-xs text-amber-700 dark:text-amber-300">
                  {c.description}
                  {c.agents.length > 0 && <span className="opacity-60">（{c.agents.join(' vs ')}）</span>}
                </p>
                {c.resolved && c.resolution && (
                  <p className="text-[10px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                    <icons.CheckCircle className="w-3 h-3" />
                    裁决：{c.resolution}
                  </p>
                )}
              </div>
            ))}
          </motion.div>
        )}

        {/* 共识结果 */}
        {consensus && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="bg-primary/5 border border-primary/20 rounded-xl p-4 space-y-3"
          >
            <div className="flex items-center gap-2 mb-2">
              <icons.Sparkles className="w-4 h-4 text-primary" />
              <span className="text-xs font-semibold text-primary">
                共识结论（置信度 {(consensus.confidence * 100).toFixed(0)}%）
              </span>
              {consensus.research_rounds && (
                <span className="text-[10px] text-muted-foreground">
                  · {consensus.research_rounds} 轮深度研究
                </span>
              )}
            </div>
            <p className="text-sm text-foreground leading-relaxed">{consensus.debate_summary}</p>

            {/* 核心结论 */}
            {consensus.key_conclusions && consensus.key_conclusions.length > 0 && (
              <div className="space-y-1 pt-2 border-t border-primary/10">
                <p className="text-[10px] text-muted-foreground font-medium">核心结论</p>
                {consensus.key_conclusions.slice(0, 3).map((c, i) => (
                  <p key={i} className="text-xs text-foreground flex items-start gap-1.5">
                    <span className="text-primary mt-0.5">•</span>
                    {c}
                  </p>
                ))}
              </div>
            )}

            {/* 行动建议 */}
            {consensus.action_items && consensus.action_items.length > 0 && (
              <div className="space-y-1 pt-2 border-t border-primary/10">
                <p className="text-[10px] text-muted-foreground font-medium">行动建议</p>
                {consensus.action_items.slice(0, 3).map((a, i) => (
                  <p key={i} className="text-xs text-foreground flex items-start gap-1.5">
                    <icons.ArrowRight className="w-3 h-3 text-primary mt-0.5 shrink-0" />
                    {a}
                  </p>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  )
}
