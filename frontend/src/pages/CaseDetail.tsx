import { useState, useEffect } from'react'
import { useParams, Link } from'react-router-dom'
import ReactMarkdown from'react-markdown'
import { icons } from'@/lib/icons'
import { toast } from'sonner'
import { casesApi, Case } from'@/lib/api'
import { PageContainer } from'@/components/ui/PageContainer'
import { cardStyle, heading, buttonStyle, iconSize, statusBadge, radius, spacing } from'@/lib/design-tokens'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
 pending: { label:'待处理', color: statusBadge.warning },
 in_progress: { label:'进行中', color: statusBadge.info },
 under_review: { label:'审核中', color: statusBadge.info },
 completed: { label:'已完成', color: statusBadge.success },
 closed: { label:'已关闭', color: statusBadge.neutral },
}

const PRIORITY_MAP: Record<string, { label: string; color: string }> = {
 low: { label:'低', color:'bg-success/10 text-success' },
 medium: { label:'中', color:'bg-warning dark:bg-warning/30 text-warning' },
 high: { label:'高', color:'bg-orange-100 dark:bg-orange-950/30 text-orange-700 dark:text-orange-400' },
 urgent: { label:'紧急', color:'bg-destructive/10 text-destructive' },
}

export default function CaseDetail() {
 const { id } = useParams<{ id: string }>()
 const [case_, setCase] = useState<Case | null>(null)
 const [loading, setLoading] = useState(true)
 const [timeline, setTimeline] = useState<any[]>([])
 const [analyzing, setAnalyzing] = useState(false)
 const [analysis, setAnalysis] = useState<any>(null)
 const [showRawAnalysis, setShowRawAnalysis] = useState(false)

 useEffect(() => {
 if (id) {
 loadCase()
 loadTimeline()
 }
 }, [id])

 const loadCase = async () => {
 try {
 const data = await casesApi.get(id!)
 setCase(data)
 // 如果案件已经有了分析结果，可以尝试从后端拉取
 // 这里假设 analyze 接口返回的是最新的分析，或者后端在 case 对象里存了分析摘要
 } catch (error: any) {
 toast.error(error.message ||'加载案件失败')
 } finally {
 setLoading(false)
 }
 }

 const loadTimeline = async () => {
 try {
 const events = await casesApi.getTimeline(id!)
 setTimeline(events)
 } catch (error) {
 console.error('加载时间线失败', error)
 }
 }

 const handleAnalyze = async () => {
 setAnalyzing(true)
 try {
 const result = await casesApi.analyze(id!)
 setAnalysis(result)
 toast.success('分析完成')
 loadTimeline()
 loadCase() // 重新加载案件状态
 } catch (error: any) {
 toast.error(error.message ||'分析失败')
 } finally {
 setAnalyzing(false)
 }
 }

 if (loading) {
 return (
 <div className="flex items-center justify-center h-full">
 <icons.Loader2 className={`${iconSize.xl} animate-spin text-muted-foreground`} />
 </div>
 )
 }

 if (!case_) {
 return (
 <div className="p-6 text-center">
 <p className="text-muted-foreground">案件不存在</p>
 <Link to="/cases" className="text-primary hover:underline mt-2 inline-block">
 返回案件列表
 </Link>
 </div>
 )
 }

 const status = STATUS_MAP[case_.status] || STATUS_MAP.pending
 const priority = PRIORITY_MAP[case_.priority] || PRIORITY_MAP.medium

 // 提取分析报告
 const report = analysis?.final_result?.report || analysis?.report || null
 const summary = analysis?.final_result?.summary || analysis?.summary || null

 return (
 <PageContainer scrollable={true} showHeader={false}>
 {/* 返回链接 */}
 <Link
 to="/cases"
 className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
 >
 <icons.ArrowLeft className={iconSize.sm} />
 返回案件列表
 </Link>

 {/* 案件头部 */}
 <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
 <div>
 <div className="flex items-center gap-3">
 <h1 className={heading.page}>{case_.title}</h1>
 <span className={`px-2 py-1 ${radius.badge} text-xs ${status.color}`}>
 {status.label}
 </span>
 <span className={`px-2 py-1 ${radius.badge} text-xs ${priority.color}`}>
 {priority.label}优先
 </span>
 </div>
 <p className={`${heading.muted} mt-1`}>
 案件编号: {case_.case_number ||'-'}
 </p>
 </div>

 <button
 onClick={handleAnalyze}
 disabled={analyzing}
 className={`flex items-center gap-2 ${buttonStyle.primary} disabled:opacity-50 shadow-sm`}
 >
 {analyzing ? (
 <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
 ) : (
 <icons.Sparkles className={iconSize.sm} />
 )}
 {analyzing ?'智能分析中...' :'AI 深度分析'}
 </button>
 </div>

 <div className="grid gap-6 lg:grid-cols-3">
 {/* 案件信息 */}
 <div className="lg:col-span-2 space-y-6">
 {/* 基本信息 */}
 <div className={`${cardStyle.base} !p-0 overflow-hidden`}>
 <div className="px-6 py-4 border-b bg-muted/30">
 <h2 className={heading.section}>案件基本描述</h2>
 </div>
 <div className="p-6">
 <p className="text-foreground leading-relaxed whitespace-pre-wrap">
 {case_.description ||'暂无详细描述'}
 </p>
 </div>
 </div>

 {/* AI分析结果 */}
 {(analysis || analyzing) && (
 <div className="rounded-xl border border-primary/10 bg-primary/[0.02] shadow-sm overflow-hidden">
 <div className="px-6 py-4 border-b border-primary/10 flex items-center justify-between bg-primary/5">
 <div className="flex items-center gap-2">
 <icons.Sparkles className={`${iconSize.md} text-primary`} />
 <h2 className={heading.section}>AI 智能分析报告</h2>
 </div>
 {analyzing && (
 <span className="flex items-center gap-2 text-sm text-primary animate-pulse font-medium">
 <icons.Loader2 className={`${iconSize.xs} animate-spin`} />
 正在构建决策树...
 </span>
 )}
 </div>
 
 <div className="p-6">
 {analyzing ? (
 <div className="space-y-4">
 <div className="h-4 bg-primary/10 rounded animate-pulse w-3/4"></div>
 <div className="h-4 bg-primary/10 rounded animate-pulse w-full"></div>
 <div className="h-4 bg-primary/10 rounded animate-pulse w-5/6"></div>
 </div>
 ) : (
 <div className="space-y-6">
 {/* 摘要展示 */}
 {summary && (
 <div className="bg-background p-4 rounded-lg border border-primary/10 shadow-sm italic text-foreground border-l-4 border-l-primary">
 {summary}
 </div>
 )}
 
 {/* 详细报告 (Markdown) */}
 <div className="prose prose-primary max-w-none text-sm leading-relaxed">
 {report ? (
 <ReactMarkdown>{report}</ReactMarkdown>
 ) : (
 <div className="text-muted-foreground py-4 text-center border-2 border-dashed rounded-lg">
 分析完成，但未生成结构化报告。请查看原始数据。
 </div>
 )}
 </div>

 {/* 调试信息: 原始结果 */}
 <div className="mt-8 pt-4 border-t">
 <button 
 onClick={() => setShowRawAnalysis(!showRawAnalysis)}
 className="text-xs text-muted-foreground flex items-center gap-1 hover:text-primary transition-colors"
 >
 {showRawAnalysis ? <icons.ChevronUp className={iconSize.xs} /> : <icons.ChevronDown className={iconSize.xs} />}
 {showRawAnalysis ?'隐藏原始分析数据' :'查看原始分析数据'}
 </button>
 {showRawAnalysis && (
 <pre className="mt-2 p-3 bg-muted rounded-md text-[10px] overflow-auto max-h-60">
 {JSON.stringify(analysis, null, 2)}
 </pre>
 )}
 </div>
 </div>
 )}
 </div>
 </div>
 )}

 {/* 时间线 */}
 <div className={`${cardStyle.base} !p-0 overflow-hidden`}>
 <div className="px-6 py-4 border-b bg-muted/30">
 <h2 className={heading.section}>案件动态时间线</h2>
 </div>
 <div className="p-6">
 {timeline.length === 0 ? (
 <div className="text-center py-8">
 <icons.Clock className={`${iconSize['2xl']} text-muted-foreground/30 mx-auto mb-3`} />
 <p className="text-muted-foreground">暂无事件记录</p>
 </div>
 ) : (
 <div className="relative space-y-6 before:absolute before:inset-0 before:ml-4 before:-translate-x-px before:h-full before:w-0.5 before:bg-border">
 {timeline.map((event, index) => (
 <div key={event.id || index} className="relative flex items-start gap-6 pl-10">
 <div className="absolute left-0 mt-1.5 h-8 w-8 -translate-x-1/2 rounded-full border-4 border-background bg-primary shadow-sm flex items-center justify-center">
 <div className="h-2 w-2 rounded-full bg-background" />
 </div>
 <div className="flex-1 bg-muted/20 p-4 rounded-lg border border-transparent hover:border-primary/10 hover:bg-background transition-all shadow-sm group">
 <div className="flex justify-between items-start mb-1">
 <p className="font-medium text-foreground group-hover:text-primary transition-colors">
 {event.title}
 </p>
 <span className="text-[10px] bg-muted px-2 py-0.5 rounded text-muted-foreground uppercase font-mono">
 {new Date(event.event_time).toLocaleTimeString([], { hour:'2-digit', minute:'2-digit' })}
 </span>
 </div>
 <p className="text-sm text-muted-foreground leading-relaxed">
 {event.description}
 </p>
 <p className="text-[10px] text-muted-foreground/60 mt-2 flex items-center gap-1">
 <icons.Calendar className={iconSize.xs} />
 {new Date(event.event_time).toLocaleDateString()}
 </p>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 </div>
 </div>

 {/* 侧边栏 */}
 <div className="space-y-6">
 {/* 案件画像 */}
 <div className={`${cardStyle.base} !p-0 overflow-hidden`}>
 <div className="px-6 py-4 border-b bg-muted/30">
 <h3 className="font-medium">案件画像</h3>
 </div>
 <div className="p-6 space-y-5">
 <div className="flex items-center gap-4">
 <div className="h-10 w-10 rounded-full bg-primary/5 flex items-center justify-center text-primary">
 <icons.Calendar className={iconSize.md} />
 </div>
 <div className="flex-1">
 <p className={`${heading.micro} font-medium uppercase tracking-caption`}>创建时间</p>
 <p className="text-sm font-medium">{new Date(case_.created_at).toLocaleDateString()} {new Date(case_.created_at).toLocaleTimeString()}</p>
 </div>
 </div>
 
 <div className="flex items-center gap-4">
 <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center text-muted-foreground">
 <icons.Clock className={iconSize.md} />
 </div>
 <div className="flex-1">
 <p className={`${heading.micro} font-medium uppercase tracking-caption`}>最后更新</p>
 <p className="text-sm font-medium">{new Date(case_.updated_at).toLocaleDateString()} {new Date(case_.updated_at).toLocaleTimeString()}</p>
 </div>
 </div>

 {case_.risk_score !== null && case_.risk_score !== undefined && (
 <div className="pt-4 border-t">
 <div className="flex justify-between items-end mb-2">
 <p className={`${heading.micro} font-medium uppercase tracking-caption`}>AI 风险评分</p>
 <p className={`text-lg font-bold ${case_.risk_score > 0.7 ?'text-destructive' : case_.risk_score > 0.4 ?'text-warning' :'text-success'}`}>
 {(case_.risk_score * 100).toFixed(0)}/100
 </p>
 </div>
 <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
 <div 
 className={`h-full transition-all duration-1000 ${case_.risk_score > 0.7 ?'bg-destructive' : case_.risk_score > 0.4 ?'bg-warning' :'bg-success'}`}
 style={{ width: `${case_.risk_score * 100}%` }}
 />
 </div>
 </div>
 )}
 </div>
 </div>

 {/* 快捷操作 */}
 <div className={`${cardStyle.base} !p-0 overflow-hidden`}>
 <div className="px-6 py-4 border-b bg-muted/30">
 <h3 className="font-medium">快捷法律工具</h3>
 </div>
 <div className="p-4 space-y-2">
 <button className={`w-full flex items-center gap-3 ${buttonStyle.ghost} hover:text-primary`}>
 <icons.FileText className={iconSize.sm} />
 关联案件证据
 </button>
 <button className={`w-full flex items-center gap-3 ${buttonStyle.ghost} hover:text-primary`}>
 <icons.MessageSquare className={iconSize.sm} />
 发起法律研讨
 </button>
 <button className={`w-full flex items-center gap-3 ${buttonStyle.ghost} hover:text-primary`}>
 <icons.User className={iconSize.sm} />
 指派承办律师
 </button>
 </div>
 </div>
 </div>
 </div>
 </PageContainer>
 )
}

