/**
 * AIAssistantPanel - AI 旁听助手侧边面板
 *
 * 在 IM 对话中显示 AI 实时法律分析结果、纪要和待办事项。
 * 通过 WebSocket 接收 ai_insight 消息实时更新。
 */

import { useState, useEffect, useCallback } from'react'
import { motion, AnimatePresence } from'framer-motion'
import { toast } from'sonner'
import { icons } from'@/lib/icons'
import { assistantApi } from'@/lib/api'

interface InsightPoint {
 type: string
 title: string
 detail: string
 risk_level?: string
 related_law?: string
}

interface Insight {
 id: string
 timestamp: string
 points: InsightPoint[]
}

interface Props {
 conversationId: string
 conversationType?: string
 onClose: () => void
}

const RISK_COLORS: Record<string, string> = {
 high:'text-destructive bg-destructive/10',
 medium:'text-warning bg-warning/10',
 low:'text-success bg-success/10',
}

const TYPE_LABELS: Record<string, string> = {
 risk:'风险点',
 legal_issue:'法律问题',
 fact:'事实陈述',
 decision:'决策事项',
}

export default function AIAssistantPanel({ conversationId, conversationType ='im', onClose }: Props) {
 const [listening, setListening] = useState(false)
 const [loading, setLoading] = useState(false)
 const [insights, setInsights] = useState<Insight[]>([])
 const [summary, setSummary] = useState<any>(null)
 const [tab, setTab] = useState<'insights' |'summary'>('insights')

 // 查询初始状态
 useEffect(() => {
 assistantApi.getStatus(conversationId).then((data) => {
 setListening(data.listening)
 if (data.listening) {
 assistantApi.getInsights(conversationId).then((d) => setInsights(d.insights || []))
 }
 }).catch(() => {})
 }, [conversationId])

 const handleStart = async () => {
 setLoading(true)
 try {
 await assistantApi.start({ conversation_id: conversationId, conversation_type: conversationType })
 setListening(true)
 setInsights([])
 setSummary(null)
 toast.success('AI 旁听已开启')
 } catch (err: any) {
 toast.error(err.message ||'开启失败')
 } finally {
 setLoading(false)
 }
 }

 const handleStop = async () => {
 setLoading(true)
 try {
 const resp = await assistantApi.stop(conversationId)
 setListening(false)
 setSummary(resp.summary)
 setTab('summary')
 toast.success('纪要已生成')
 } catch (err: any) {
 toast.error(err.message ||'停止失败')
 } finally {
 setLoading(false)
 }
 }

 // 接收 WebSocket 推送的 AI insight（由父组件通过 props 或全局 store 传入）
 const addInsight = useCallback((insight: Insight) => {
 setInsights((prev) => [...prev, insight])
 }, [])

 // 暴露给父组件
 ;(window as any).__aiAssistantAddInsight = addInsight

 return (
 <div className="flex flex-col h-full bg-background border-l border-border w-80">
 {/* 头部 */}
 <div className="flex items-center justify-between px-4 py-3 border-b border-border">
 <div className="flex items-center gap-2">
 <icons.Bot className="w-4 h-4 text-primary" />
 <span className="text-sm font-medium">AI 法律助手</span>
 {listening && (
 <span className="flex items-center gap-1 text-xs text-success">
 <span className="w-1.5 h-1.5 bg-success rounded-full animate-pulse" />
 旁听中
 </span>
 )}
 </div>
 <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
 <icons.X className="w-4 h-4" />
 </button>
 </div>

 {/* 开关按钮 */}
 <div className="px-4 py-3 border-b border-border">
 {!listening ? (
 <button
 onClick={handleStart}
 disabled={loading}
 className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50"
 >
 <icons.Play className="w-4 h-4" />
 {loading ?'启动中...' :'开启 AI 旁听'}
 </button>
 ) : (
 <button
 onClick={handleStop}
 disabled={loading}
 className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-destructive/10 text-destructive border border-destructive/20 rounded-lg text-sm font-medium hover:bg-destructive/20 disabled:opacity-50"
 >
 <icons.Square className="w-4 h-4" />
 {loading ?'生成纪要中...' :'停止旁听并生成纪要'}
 </button>
 )}
 </div>

 {/* Tab 切换 */}
 <div className="flex border-b border-border">
 <button
 onClick={() => setTab('insights')}
 className={`flex-1 py-2 text-xs font-medium text-center transition-colors ${
 tab ==='insights' ?'text-primary border-b-2 border-primary' :'text-muted-foreground'
 }`}
 >
 实时分析 {insights.length > 0 && `(${insights.length})`}
 </button>
 <button
 onClick={() => setTab('summary')}
 className={`flex-1 py-2 text-xs font-medium text-center transition-colors ${
 tab ==='summary' ?'text-primary border-b-2 border-primary' :'text-muted-foreground'
 }`}
 >
 纪要
 </button>
 </div>

 {/* 内容区 */}
 <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
 <AnimatePresence mode="wait">
 {tab ==='insights' ? (
 <motion.div key="insights" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
 {insights.length === 0 ? (
 <div className="text-center py-8 text-muted-foreground">
 <icons.MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
 <p className="text-xs">{listening ?'等待对话内容分析...' :'开启旁听后将实时显示法律分析'}</p>
 </div>
 ) : (
 insights.map((insight) => (
 <div key={insight.id} className="space-y-2 mb-4">
 <div className="text-[10px] text-muted-foreground">
 {new Date(insight.timestamp).toLocaleTimeString('zh-CN')}
 </div>
 {insight.points.map((p, i) => (
 <div key={i} className="p-2.5 rounded-lg border border-border bg-card">
 <div className="flex items-center gap-2 mb-1">
 <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground">
 {TYPE_LABELS[p.type] || p.type}
 </span>
 {p.risk_level && (
 <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${RISK_COLORS[p.risk_level] ||''}`}>
 {p.risk_level ==='high' ?'高风险' : p.risk_level ==='medium' ?'中风险' :'低风险'}
 </span>
 )}
 </div>
 <div className="text-sm font-medium text-foreground">{p.title}</div>
 <div className="text-xs text-muted-foreground mt-0.5">{p.detail}</div>
 {p.related_law && (
 <div className="text-[10px] text-primary mt-1 flex items-center gap-1">
 <icons.BookOpen className="w-3 h-3" />
 {p.related_law}
 </div>
 )}
 </div>
 ))}
 </div>
 ))
 )}
 </motion.div>
 ) : (
 <motion.div key="summary" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
 {!summary ? (
 <div className="text-center py-8 text-muted-foreground">
 <icons.FileText className="w-8 h-8 mx-auto mb-2 opacity-30" />
 <p className="text-xs">停止旁听后将自动生成纪要</p>
 </div>
 ) : (
 <div className="space-y-4">
 {summary.title && (
 <h3 className="text-sm font-medium">{summary.title}</h3>
 )}
 {summary.abstract && (
 <div>
 <div className="text-[10px] font-medium text-muted-foreground mb-1">摘要</div>
 <p className="text-xs text-foreground leading-relaxed">{summary.abstract}</p>
 </div>
 )}
 {summary.risk_assessment && (
 <div>
 <div className="text-[10px] font-medium text-muted-foreground mb-1">风险评估</div>
 <span className={`text-xs px-2 py-0.5 rounded ${RISK_COLORS[summary.risk_assessment.level] ||''}`}>
 {summary.risk_assessment.level ==='high' ?'高风险' : summary.risk_assessment.level ==='medium' ?'中等风险' :'低风险'}
 </span>
 {summary.risk_assessment.risks?.map((r: string, i: number) => (
 <p key={i} className="text-xs text-muted-foreground mt-1">- {r}</p>
 ))}
 </div>
 )}
 {summary.recommendations?.length > 0 && (
 <div>
 <div className="text-[10px] font-medium text-muted-foreground mb-1">建议</div>
 {summary.recommendations.map((r: string, i: number) => (
 <p key={i} className="text-xs text-foreground">- {r}</p>
 ))}
 </div>
 )}
 {summary.action_items?.length > 0 && (
 <div>
 <div className="text-[10px] font-medium text-muted-foreground mb-1">待办事项</div>
 {summary.action_items.map((item: any, i: number) => (
 <div key={i} className="flex items-start gap-2 py-1">
 <input type="checkbox" className="mt-0.5 rounded border-border" />
 <span className="text-xs text-foreground">{item.task || item}</span>
 </div>
 ))}
 </div>
 )}
 </div>
 )}
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 </div>
 )
}
