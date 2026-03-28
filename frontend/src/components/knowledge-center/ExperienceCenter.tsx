/**
 * 经验与进化中心 - 经验记忆浏览/评分 + 自进化引擎控制
 */
import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { icons } from '@/lib/icons'
import { cardStyle, heading, statusBadge } from '@/lib/design-tokens'
import { knowledgeCenterApi, licApi, type MemoryItem, type EvolutionStatus } from '@/lib/api'
import { toast } from 'sonner'

/** 经验记忆模块 - 独立导出 */
export function ExperienceMemory() {
  const [searchQuery, setSearchQuery] = useState('')
  const [memories, setMemories] = useState<MemoryItem[]>([])
  const [loading, setLoading] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [selectedMemory, setSelectedMemory] = useState<MemoryItem | null>(null)
  const [feedbackRating, setFeedbackRating] = useState(0)
  const [feedbackComment, setFeedbackComment] = useState('')
  const [submittingFeedback, setSubmittingFeedback] = useState(false)

  const loadRecentMemories = useCallback(async () => {
    try {
      const data = await knowledgeCenterApi.getRecentMemories(30)
      setMemories(data.items || [])
    } catch (error: any) {
      // 静默处理，不影响页面
    } finally {
      setInitialLoading(false)
    }
  }, [])

  useEffect(() => {
    loadRecentMemories()
  }, [loadRecentMemories])

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      await loadRecentMemories()
      return
    }
    setLoading(true)
    try {
      const data = await knowledgeCenterApi.searchMemories(searchQuery, 20, 0.3)
      setMemories(data.items || [])
    } catch (error: any) {
      toast.error(error.message || '搜索失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmitFeedback = async () => {
    if (!selectedMemory?.memory_id || feedbackRating === 0) return
    setSubmittingFeedback(true)
    try {
      await knowledgeCenterApi.updateMemoryFeedback(
        selectedMemory.memory_id,
        feedbackRating,
        feedbackComment
      )
      toast.success('评价已提交，将用于优化系统表现')
      setSelectedMemory(null)
      setFeedbackRating(0)
      setFeedbackComment('')
      await loadRecentMemories()
    } catch (error: any) {
      toast.error(error.message || '提交失败')
    } finally {
      setSubmittingFeedback(false)
    }
  }

  const getRatingColor = (rating: number) => {
    if (rating >= 4) return 'text-emerald-500'
    if (rating >= 3) return 'text-amber-500'
    if (rating >= 1) return 'text-red-500'
    return 'text-muted-foreground/50'
  }

  const getRatingLabel = (rating: number) => {
    if (rating >= 5) return '优秀'
    if (rating >= 4) return '良好'
    if (rating >= 3) return '一般'
    if (rating >= 2) return '较差'
    if (rating >= 1) return '很差'
    return '未评价'
  }

  return (
    <div className="h-full flex flex-col">
      {/* 搜索栏 */}
      <div className="p-4 bg-background border-b border-border">
        <div className="flex gap-2 max-w-2xl">
          <div className="relative flex-1">
            <icons.Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="搜索历史经验：输入案件类型、法律问题等..."
              className="w-full pl-9 pr-3 py-2.5 bg-muted/50 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-500/20 focus:border-amber-500 text-sm"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading}
            className="px-4 py-2.5 bg-amber-500 text-white rounded-xl text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-all shadow-sm"
          >
            {loading ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : '检索'}
          </button>
        </div>
      </div>

      {/* 经验列表 */}
      <div className="flex-1 overflow-y-auto p-4">
        {initialLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className={`${cardStyle.compact} animate-pulse`}>
                <div className="h-4 bg-muted rounded w-2/3 mb-2" />
                <div className="h-3 bg-muted/50 rounded w-full mb-1" />
                <div className="h-3 bg-muted/50 rounded w-1/3" />
              </div>
            ))}
          </div>
        ) : memories.length > 0 ? (
          <div className="space-y-2 max-w-4xl">
            {memories.map((memory, index) => (
              <motion.div
                key={memory.memory_id || index}
                initial={{ opacity: 0, y: 5 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.02 }}
                className={`group ${cardStyle.interactive}`}
                onClick={() => {
                  setSelectedMemory(memory)
                  setFeedbackRating(memory.rating || 0)
                }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <icons.Brain className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                      <h4 className={`${heading.card} truncate`}>{memory.task}</h4>
                    </div>
                    {memory.result_summary && (
                      <p className="text-xs text-muted-foreground line-clamp-2 ml-5.5 pl-0.5">{memory.result_summary}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2 ml-5.5 pl-0.5">
                      {memory.timestamp && (
                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                          <icons.Clock className="w-3 h-3" />
                          {new Date(memory.timestamp).toLocaleDateString('zh-CN')}
                        </span>
                      )}
                      {memory.similarity_score !== undefined && memory.similarity_score > 0 && (
                        <span className="text-[10px] text-muted-foreground">
                          相似度: {(memory.similarity_score * 100).toFixed(0)}%
                        </span>
                      )}
                      {memory.plan?.length > 0 && (
                        <span className="text-[10px] text-muted-foreground">
                          {memory.plan.length} 步执行计划
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-1 flex-shrink-0 ml-3">
                    {/* 评分显示 */}
                    <div className="flex items-center gap-0.5">
                      {[1, 2, 3, 4, 5].map(star => (
                        <icons.Star
                          key={star}
                          className={`w-3.5 h-3.5 ${
                            star <= (memory.rating || 0)
                              ? getRatingColor(memory.rating || 0)
                              : 'text-muted-foreground/30'
                          }`}
                          fill={star <= (memory.rating || 0) ? 'currentColor' : 'none'}
                        />
                      ))}
                    </div>
                    <span className={`text-[10px] font-medium ml-1 ${getRatingColor(memory.rating || 0)}`}>
                      {getRatingLabel(memory.rating || 0)}
                    </span>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>
        ) : (
          <div className="py-20 text-center">
            <div className="w-16 h-16 bg-amber-50 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <icons.Brain className="w-8 h-8 text-amber-300" />
            </div>
            <p className="text-muted-foreground font-semibold">暂无经验记忆</p>
            <p className="text-xs text-muted-foreground/70 mt-1">系统将自动记录对话和任务处理经验</p>
          </div>
        )}
      </div>

      {/* 评价弹窗 */}
      <AnimatePresence>
        {selectedMemory && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
            onClick={() => setSelectedMemory(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="bg-background rounded-2xl shadow-2xl w-[520px] max-w-[90vw] overflow-hidden"
            >
              <div className="px-6 py-4 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <icons.Brain className="w-4 h-4 text-amber-500" />
                  <h3 className={heading.section}>经验详情与评价</h3>
                </div>
                <button onClick={() => setSelectedMemory(null)} className="text-muted-foreground hover:text-foreground">
                  <icons.X className="w-5 h-5" />
                </button>
              </div>
              <div className="p-6 space-y-4">
                {/* 任务描述 */}
                <div>
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">任务描述</label>
                  <p className="text-sm text-foreground mt-1">{selectedMemory.task}</p>
                </div>

                {/* 结果摘要 */}
                {selectedMemory.result_summary && (
                  <div>
                    <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">结果摘要</label>
                    <p className="text-sm text-muted-foreground mt-1 bg-muted/50 p-3 rounded-lg line-clamp-5">
                      {selectedMemory.result_summary}
                    </p>
                  </div>
                )}

                {/* 执行计划 */}
                {selectedMemory.plan?.length > 0 && (
                  <div>
                    <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                      执行计划 ({selectedMemory.plan.length} 步)
                    </label>
                    <div className="mt-1 space-y-1 max-h-32 overflow-y-auto">
                      {selectedMemory.plan.map((step: any, i: number) => (
                        <div key={i} className="flex items-center gap-2 text-xs text-muted-foreground py-1">
                          <span className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-100 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 flex items-center justify-center text-[10px] font-bold">
                            {i + 1}
                          </span>
                          <span>{typeof step === 'string' ? step : step.description || step.step || JSON.stringify(step)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 评分 */}
                <div>
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-2 block">
                    你的评价 (对系统处理质量打分)
                  </label>
                  <div className="flex items-center gap-1">
                    {[1, 2, 3, 4, 5].map(star => (
                      <button
                        key={star}
                        onClick={() => setFeedbackRating(star)}
                        className="p-1 hover:scale-110 transition-transform"
                      >
                        <icons.Star
                          className={`w-7 h-7 ${
                            star <= feedbackRating ? 'text-amber-400' : 'text-muted-foreground/30'
                          }`}
                          fill={star <= feedbackRating ? 'currentColor' : 'none'}
                        />
                      </button>
                    ))}
                    <span className="text-sm text-muted-foreground ml-2">
                      {getRatingLabel(feedbackRating)}
                    </span>
                  </div>
                </div>

                {/* 评论 */}
                <div>
                  <label className="text-xs font-bold text-muted-foreground uppercase tracking-wider mb-1 block">
                    评价内容（可选）
                  </label>
                  <textarea
                    value={feedbackComment}
                    onChange={(e) => setFeedbackComment(e.target.value)}
                    placeholder="对本次处理有什么建议或反馈..."
                    className="w-full px-3 py-2 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-amber-500/20 resize-none h-20"
                  />
                </div>
              </div>
              <div className="px-6 py-4 border-t border-border flex justify-end gap-2">
                <button
                  onClick={() => setSelectedMemory(null)}
                  className="px-4 py-2 text-sm text-muted-foreground hover:bg-muted rounded-xl transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleSubmitFeedback}
                  disabled={submittingFeedback || feedbackRating === 0}
                  className="flex items-center gap-2 px-5 py-2 bg-amber-500 text-white rounded-xl text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition-all shadow-sm"
                >
                  {submittingFeedback ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : <icons.ThumbsUp className="w-4 h-4" />}
                  提交评价
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

/** 自进化引擎模块 - 独立导出 */
export function EvolutionEngine() {
  const [status, setStatus] = useState<EvolutionStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [evolving, setEvolving] = useState(false)

  const loadStatus = useCallback(async () => {
    try {
      const data = await knowledgeCenterApi.getEvolutionStatus()
      setStatus(data)
    } catch {
      // 静默处理
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  const handleTriggerEvolution = async () => {
    setEvolving(true)
    try {
      await licApi.evolve()
      toast.success('自进化任务已启动，正在后台更新法规库...')
      setTimeout(loadStatus, 3000)
    } catch (error: any) {
      toast.error(error.message || '启动失败')
    } finally {
      setEvolving(false)
    }
  }

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className={`${cardStyle.base} animate-pulse`}>
            <div className="h-5 bg-muted rounded w-1/4 mb-3" />
            <div className="h-8 bg-muted/50 rounded w-1/3" />
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="p-6 overflow-y-auto h-full">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* 核心指标卡片 */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            icon={icons.Brain}
            label="经验总量"
            value={status?.total_memories || 0}
            color="text-amber-600 bg-amber-50"
          />
          <MetricCard
            icon={icons.Star}
            label="平均评分"
            value={status?.avg_rating?.toFixed(1) || '0'}
            suffix="/5"
            color="text-emerald-600 bg-emerald-50"
          />
          <MetricCard
            icon={icons.ThumbsUp}
            label="优质经验"
            value={status?.high_rated_count || 0}
            suffix="条"
            color="text-primary bg-primary/5"
          />
          <MetricCard
            icon={icons.Activity}
            label="进化任务"
            value={status?.evolution_tasks_total || 0}
            suffix="次"
            color="text-primary bg-primary/5"
          />
        </div>

        {/* 自进化控制面板 */}
        <div className="bg-gradient-to-br from-emerald-50 via-white to-teal-50 rounded-2xl border border-emerald-100 overflow-hidden">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-emerald-500 rounded-xl shadow-lg shadow-emerald-500/20">
                  <icons.Zap className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className={heading.section}>自进化引擎</h3>
                  <p className="text-xs text-muted-foreground">自动爬取最新法律法规，持续更新知识库</p>
                </div>
              </div>
              <button
                onClick={handleTriggerEvolution}
                disabled={evolving}
                className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 text-white rounded-xl text-sm font-medium hover:bg-emerald-700 disabled:opacity-50 transition-all shadow-lg shadow-emerald-600/20 active:scale-95"
              >
                {evolving ? (
                  <icons.Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <icons.Sparkles className="w-4 h-4" />
                )}
                {evolving ? '进化中...' : '触发进化'}
              </button>
            </div>

            {/* 进化流程展示 */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              {[
                { icon: icons.Search, label: '扫描法规源', desc: '监控政府法规网站', status: 'ready' },
                { icon: icons.RefreshCw, label: '数据抓取', desc: '自动爬取新增法规', status: 'ready' },
                { icon: icons.Lightbulb, label: 'AI清洗', desc: '结构化解析与分类', status: 'ready' },
                { icon: icons.Target, label: '知识入库', desc: '向量化索引与图谱', status: 'ready' },
              ].map((step, i) => (
                <div key={i} className="bg-background/70 backdrop-blur-sm rounded-xl border border-emerald-100 p-4 relative">
                  {i < 3 && (
                    <div className="hidden md:block absolute top-1/2 -right-2 w-4 text-emerald-300">
                      <icons.ChevronRight className="w-4 h-4" />
                    </div>
                  )}
                  <step.icon className="w-5 h-5 text-emerald-500 mb-2" />
                  <div className="font-semibold text-sm text-foreground">{step.label}</div>
                  <div className="text-[10px] text-muted-foreground mt-0.5">{step.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RLHF-Lite 学习闭环 */}
        <div className={cardStyle.base}>
          <div className="flex items-center gap-2 mb-4">
            <icons.TrendingUp className="w-5 h-5 text-primary" />
            <h3 className={heading.section}>RLHF-Lite 学习闭环</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-primary/5 rounded-xl p-4 border border-primary/10">
              <div className="flex items-center gap-2 mb-2">
                <icons.MessageSquare className="w-4 h-4 text-primary" />
                <span className="font-semibold text-sm text-primary">用户反馈采集</span>
              </div>
              <p className="text-xs text-primary/80">
                每次AI处理完法律任务后，用户可以对结果进行1-5星评价，系统自动记录到经验记忆库。
              </p>
              <div className="mt-3 flex items-center gap-1.5">
                <icons.CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md ${statusBadge.success}`}>已激活</span>
              </div>
            </div>
            <div className="bg-amber-50 dark:bg-amber-950/30 rounded-xl p-4 border border-amber-100 dark:border-amber-800">
              <div className="flex items-center gap-2 mb-2">
                <icons.BarChart3 className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                <span className="font-semibold text-sm text-amber-900 dark:text-amber-300">经验加权排序</span>
              </div>
              <p className="text-xs text-amber-700 dark:text-amber-400">
                高评分经验(4-5星)在检索时优先推荐，低评分(1-2星)自动降权过滤，实现经验质量优胜劣汰。
              </p>
              <div className="mt-3 flex items-center gap-1.5">
                <icons.CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md ${statusBadge.success}`}>已激活</span>
              </div>
            </div>
            <div className="bg-primary/5 rounded-xl p-4 border border-primary/10">
              <div className="flex items-center gap-2 mb-2">
                <icons.Sparkles className="w-4 h-4 text-primary" />
                <span className="font-semibold text-sm text-primary">决策优化</span>
              </div>
              <p className="text-xs text-primary/80">
                系统在处理新任务时，自动检索相似的优质经验，将其作为参考上下文注入AI决策过程。
              </p>
              <div className="mt-3 flex items-center gap-1.5">
                <icons.CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-md ${statusBadge.success}`}>已激活</span>
              </div>
            </div>
          </div>
        </div>

        {/* 评分分布 */}
        {status && (
          <div className={cardStyle.base}>
            <h3 className={`${heading.section} mb-4 flex items-center gap-2`}>
              <icons.BarChart3 className="w-4 h-4 text-muted-foreground" />
              经验评分分布
            </h3>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-4 bg-emerald-50 rounded-xl border border-emerald-100">
                <div className="text-2xl font-bold text-emerald-600">{status.high_rated_count}</div>
                <div className="text-xs text-emerald-600 mt-1 font-medium">优质 (4-5星)</div>
                <div className="flex justify-center mt-1.5">
                  {[1,2,3,4,5].map(s => (
                    <icons.Star key={s} className="w-3 h-3 text-emerald-400" fill={s <= 4 ? 'currentColor' : 'none'} />
                  ))}
                </div>
              </div>
              <div className="text-center p-4 bg-muted/50 rounded-xl border border-border">
                <div className="text-2xl font-bold text-muted-foreground">{status.unrated_count}</div>
                <div className="text-xs text-muted-foreground mt-1 font-medium">未评价</div>
                <div className="flex justify-center mt-1.5">
                  {[1,2,3,4,5].map(s => (
                    <icons.Star key={s} className="w-3 h-3 text-muted-foreground/30" />
                  ))}
                </div>
              </div>
              <div className="text-center p-4 bg-destructive/5 rounded-xl border border-destructive/10">
                <div className="text-2xl font-bold text-destructive">{status.low_rated_count}</div>
                <div className="text-xs text-destructive mt-1 font-medium">待改进 (1-2星)</div>
                <div className="flex justify-center mt-1.5">
                  {[1,2,3,4,5].map(s => (
                    <icons.Star key={s} className="w-3 h-3 text-destructive/60" fill={s <= 1 ? 'currentColor' : 'none'} />
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/** 指标卡片组件 */
function MetricCard({ icon: Icon, label, value, suffix, color }: {
  icon: any; label: string; value: number | string; suffix?: string; color: string
}) {
  return (
    <div className={cardStyle.compact}>
      <div className="flex items-center gap-2 mb-2">
        <div className={`p-1.5 rounded-lg ${color}`}>
          <Icon className="w-3.5 h-3.5" />
        </div>
        <span className={heading.micro}>{label}</span>
      </div>
      <div className="flex items-baseline gap-1">
        <span className="text-2xl font-bold text-foreground">{value}</span>
        {suffix && <span className="text-sm text-muted-foreground">{suffix}</span>}
      </div>
    </div>
  )
}
