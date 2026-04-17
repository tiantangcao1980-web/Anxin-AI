/**
 * 智慧搜索 - 混合搜索 + RAG问答 + AI深度研究
 */
import { useState } from'react'
import { motion, AnimatePresence } from'framer-motion'
import { icons } from'@/lib/icons'
import { knowledgeApi } from'@/lib/api'
import { toast } from'sonner'
import ReactMarkdown from'react-markdown'

interface SearchResult {
 id: string
 title: string
 content: string
 source?: string
 score: number
 match_type?: string
 metadata?: any
}

export function SmartSearch() {
 const [searchQuery, setSearchQuery] = useState('')
 const [results, setResults] = useState<SearchResult[]>([])
 const [loading, setLoading] = useState(false)
 const [searchMode, setSearchMode] = useState<'hybrid' |'rag' |'research'>('hybrid')

 // 深度研究
 const [isResearching, setIsResearching] = useState(false)
 const [researchReport, setResearchReport] = useState<any | null>(null)
 const [showReport, setShowReport] = useState(false)

 // RAG 问答
 const [ragAnswer, setRagAnswer] = useState<{ answer: string; sources: any[] } | null>(null)
 const [isAsking, setIsAsking] = useState(false)

 const handleSearch = async () => {
 if (!searchQuery.trim()) return

 if (searchMode ==='research') {
 await handleDeepResearch()
 return
 }

 if (searchMode ==='rag') {
 await handleRAGQuery()
 return
 }

 setLoading(true)
 setRagAnswer(null)
 setShowReport(false)
 try {
 const data = await knowledgeApi.search(searchQuery)
 setResults(data)
 } catch (error: any) {
 toast.error(error.message ||'搜索失败')
 } finally {
 setLoading(false)
 }
 }

 const handleRAGQuery = async () => {
 if (!searchQuery.trim()) return
 setIsAsking(true)
 setResults([])
 setShowReport(false)
 try {
 const result = await knowledgeApi.ragQuery(searchQuery)
 setRagAnswer(result)
 } catch (error: any) {
 toast.error(error.message ||'RAG 问答失败')
 } finally {
 setIsAsking(false)
 }
 }

 const handleDeepResearch = async () => {
 if (!searchQuery.trim()) {
 toast.error('请先输入研究课题')
 return
 }
 setIsResearching(true)
 setShowReport(true)
 setResearchReport(null)
 setResults([])
 setRagAnswer(null)
 try {
 const result = await knowledgeApi.deepResearch(searchQuery)
 setResearchReport(result)
 toast.success('研究报告生成完成')
 } catch (error: any) {
 toast.error(error.message ||'研究失败')
 setShowReport(false)
 } finally {
 setIsResearching(false)
 }
 }

 const modeConfig = {
 hybrid: { label:'混合检索', icon: icons.Search, color:'bg-foreground text-background hover:bg-foreground/90' },
 rag: { label:'RAG问答', icon: icons.MessageSquare, color:'bg-success text-success-foreground hover:bg-success/20' },
 research: { label:'深度研究', icon: icons.Sparkles, color:'bg-primary text-primary-foreground hover:bg-primary/90' },
 }

 const currentMode = modeConfig[searchMode]

 return (
 <div className="h-full flex flex-col">
 {/* 搜索头部 */}
 <div className="p-6 bg-background border-b border-border">
 <div className="max-w-4xl mx-auto">
 <div className="flex items-center gap-3 mb-4">
 <div className="p-2.5 bg-primary rounded-xl shadow-lg shadow-primary/20">
 <icons.Search className="w-5 h-5 text-primary-foreground" />
 </div>
 <div>
 <h2 className="text-lg font-medium text-foreground">智慧搜索引擎</h2>
 <p className="text-xs text-muted-foreground">混合语义搜索 · RAG智能问答 · AI深度研究</p>
 </div>
 </div>

 {/* 搜索模式切换 */}
 <div className="flex gap-1.5 mb-3 p-1 bg-muted rounded-xl w-fit">
 {Object.entries(modeConfig).map(([key, config]) => (
 <button
 key={key}
 onClick={() => setSearchMode(key as any)}
 className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors ${
 searchMode === key
 ?'bg-background text-foreground shadow-sm'
 :'text-muted-foreground hover:text-foreground'
 }`}
 >
 <config.icon className="w-3.5 h-3.5" />
 {config.label}
 </button>
 ))}
 </div>

 {/* 搜索框 */}
 <div className="flex gap-2">
 <div className="relative flex-1">
 <icons.Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
 <input
 type="text"
 value={searchQuery}
 onChange={(e) => setSearchQuery(e.target.value)}
 onKeyDown={(e) => e.key ==='Enter' && handleSearch()}
 placeholder={
 searchMode ==='hybrid' ?'搜索法律条文、案例、合同模板...' :
 searchMode ==='rag' ?'输入法律问题，AI将结合知识库为您解答...' :
'输入法律研究课题，生成深度分析报告...'
 }
 className="w-full pl-10 pr-4 py-3 bg-muted/50 border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary text-sm text-foreground transition-colors"
 />
 </div>
 <button
 onClick={handleSearch}
 disabled={loading || isResearching || isAsking}
 className={`flex items-center gap-2 px-5 py-3 rounded-xl text-sm font-medium shadow-lg transition-transform active:scale-95 disabled:opacity-50 ${currentMode.color}`}
 >
 {(loading || isResearching || isAsking) ? (
 <icons.Loader2 className="w-4 h-4 animate-spin" />
 ) : (
 <currentMode.icon className="w-4 h-4" />
 )}
 {currentMode.label}
 </button>
 </div>
 </div>
 </div>

 {/* 结果区域 */}
 <div className="flex-1 overflow-y-auto p-6">
 <div className="max-w-4xl mx-auto space-y-4">
 {/* RAG 问答结果 */}
 <AnimatePresence>
 {ragAnswer && (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -10 }}
 className="bg-gradient-to-b from-success/10 to-white rounded-2xl border border-success/20 shadow-sm overflow-hidden"
 >
 <div className="px-6 py-4 border-b border-success/20 flex items-center justify-between bg-success/10">
 <div className="flex items-center gap-2">
 <icons.MessageSquare className="w-4 h-4 text-success" />
 <span className="font-medium text-success text-sm">RAG 智能回答</span>
 </div>
 <button onClick={() => setRagAnswer(null)} className="text-muted-foreground hover:text-foreground">
 <icons.X className="w-4 h-4" />
 </button>
 </div>
 <div className="p-6">
 <div className="prose prose-emerald max-w-none text-sm leading-relaxed">
 <ReactMarkdown>{ragAnswer.answer}</ReactMarkdown>
 </div>
 {ragAnswer.sources?.length > 0 && (
 <div className="mt-6 pt-4 border-t border-border">
 <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-caption mb-3">参考来源</h5>
 <div className="flex flex-wrap gap-2">
 {ragAnswer.sources.map((s: any, i: number) => (
 <span key={i} className="text-[11px] px-2 py-1 bg-muted text-muted-foreground rounded-md">
 {s.title || s.source || `来源 ${i+1}`}
 </span>
 ))}
 </div>
 </div>
 )}
 </div>
 </motion.div>
 )}
 </AnimatePresence>

 {/* RAG 加载中 */}
 {isAsking && (
 <div className="bg-success/10 rounded-2xl border border-success/20 p-6">
 <div className="flex items-center gap-3 text-success animate-pulse">
 <icons.Loader2 className="w-4 h-4 animate-spin" />
 <span className="text-sm font-medium">正在检索知识库并生成回答...</span>
 </div>
 <div className="mt-4 space-y-2">
 <div className="h-4 bg-success/10/50 rounded w-3/4" />
 <div className="h-4 bg-success/10/50 rounded w-full" />
 <div className="h-4 bg-success/10/50 rounded w-5/6" />
 </div>
 </div>
 )}

 {/* 深度研究报告 */}
 <AnimatePresence>
 {showReport && (
 <motion.div
 initial={{ opacity: 0, y: 20 }}
 animate={{ opacity: 1, y: 0 }}
 exit={{ opacity: 0, y: -10 }}
 className="bg-gradient-to-b from-primary/5 to-background rounded-2xl border border-primary/10 shadow-sm overflow-hidden"
 >
 <div className="px-6 py-4 border-b border-primary/10 flex items-center justify-between bg-primary/5">
 <div className="flex items-center gap-2">
 <icons.Sparkles className="w-4 h-4 text-primary" />
 <span className="font-medium text-foreground text-sm">AI 深度法律研究报告</span>
 </div>
 <button onClick={() => setShowReport(false)} className="text-muted-foreground hover:text-foreground">
 <icons.X className="w-4 h-4" />
 </button>
 </div>
 <div className="p-6">
 {isResearching ? (
 <div className="space-y-4 py-4">
 <div className="flex items-center gap-3 text-primary animate-pulse">
 <icons.Loader2 className="w-4 h-4 animate-spin" />
 <span className="text-sm font-medium">正在调取多维案例并生成深度分析...</span>
 </div>
 <div className="h-4 bg-primary/10 rounded w-3/4" />
 <div className="h-4 bg-primary/10 rounded w-full" />
 <div className="h-4 bg-primary/10 rounded w-5/6" />
 </div>
 ) : researchReport ? (
 <div className="prose prose-indigo max-w-none text-sm leading-relaxed">
 <ReactMarkdown>{researchReport.content}</ReactMarkdown>
 {researchReport.citations?.length > 0 && (
 <div className="mt-8 pt-6 border-t border-border">
 <h5 className="text-xs font-medium text-muted-foreground uppercase tracking-caption mb-4 flex items-center gap-2">
 <icons.BookMarked className="w-3.5 h-3.5" />
 研究引用库
 </h5>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
 {researchReport.citations.map((cite: any, i: number) => (
 <div key={i} className="flex items-center gap-2 p-2 rounded-lg bg-muted/50 border border-border text-[11px] text-muted-foreground">
 <icons.ChevronRight className="w-3 h-3 text-primary flex-shrink-0" />
 <span className="font-medium truncate">{cite.name || cite.case_number}</span>
 {cite.article && <span className="text-muted-foreground flex-shrink-0">第{cite.article}条</span>}
 </div>
 ))}
 </div>
 </div>
 )}
 </div>
 ) : null}
 </div>
 </motion.div>
 )}
 </AnimatePresence>

 {/* 搜索结果列表 */}
 <div className="space-y-3">
 {loading ? (
 Array.from({ length: 4 }).map((_, i) => (
 <div key={i} className="bg-background rounded-xl border border-border p-5 animate-pulse">
 <div className="h-4 bg-muted rounded w-1/4 mb-3" />
 <div className="h-3 bg-muted/50 rounded w-3/4 mb-2" />
 <div className="h-3 bg-muted/50 rounded w-1/2" />
 </div>
 ))
 ) : results.length > 0 ? (
 results.map((item, index) => (
 <motion.div
 key={item.id}
 initial={{ opacity: 0, y: 10 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: index * 0.03 }}
 className="group bg-background rounded-xl border border-border p-5 hover:border-primary/30 hover:shadow-md transition-[border-color,box-shadow] cursor-pointer relative overflow-hidden"
 >
 {item.metadata?.keyword_match && (
 <div className="absolute top-0 right-0 px-2 py-0.5 bg-primary text-[10px] text-primary-foreground font-medium rounded-bl-lg">
 精准匹配
 </div>
 )}
 <div className="flex items-start justify-between mb-2">
 <div className="flex-1">
 <div className="flex items-center gap-2 mb-1">
 <span className="text-[10px] font-medium text-primary uppercase tracking-tighter bg-primary/5 px-1.5 py-0.5 rounded">
 {item.match_type ==='hybrid' ?'混合检索' : item.match_type ==='vector' ?'语义关联' :'文本匹配'}
 </span>
 <h4 className="font-medium text-foreground text-sm group-hover:text-primary transition-colors">{item.title}</h4>
 </div>
 </div>
 <icons.ExternalLink className="w-4 h-4 text-muted-foreground/50 group-hover:text-primary/60 transition-colors flex-shrink-0 ml-2" />
 </div>
 <p className="text-xs text-muted-foreground leading-relaxed mb-3 line-clamp-3">{item.content}</p>
 <div className="flex items-center gap-3">
 <span className="text-[10px] text-muted-foreground">来源: {item.source ||'知识库'}</span>
 <span className="text-[10px] text-muted-foreground/50">|</span>
 <div className="flex items-center gap-1">
 <div className="h-1.5 w-16 bg-muted rounded-full overflow-hidden">
 <div className="h-full bg-primary rounded-full" style={{ width: `${(item.score * 100)}%` }} />
 </div>
 <span className="text-[10px] text-muted-foreground">{(item.score * 100).toFixed(0)}%</span>
 </div>
 </div>
 </motion.div>
 ))
 ) : !showReport && !ragAnswer && !isAsking && (
 <div className="py-24 text-center space-y-4">
 <div className="w-20 h-20 bg-muted rounded-2xl flex items-center justify-center mx-auto shadow-inner">
 <icons.Search className="w-10 h-10 text-muted-foreground/30" />
 </div>
 <div>
 <p className="text-muted-foreground font-medium">探索法律知识宇宙</p>
 <p className="text-xs text-muted-foreground/70 mt-1">输入问题或关键词，AI 将为您检索法律法规、判例、合同模板</p>
 </div>
 <div className="flex flex-wrap gap-2 justify-center mt-4">
 {['劳动合同解除条件','知识产权侵权认定','股权转让税务处理','公司章程修订'].map(tag => (
 <button
 key={tag}
 onClick={() => { setSearchQuery(tag); }}
 className="px-3 py-1.5 text-xs text-muted-foreground bg-muted rounded-lg hover:bg-primary/5 hover:text-primary transition-colors"
 >
 {tag}
 </button>
 ))}
 </div>
 </div>
 )}
 </div>
 </div>
 </div>
 </div>
 )
}
