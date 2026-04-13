/**
 * 知识库管理 - 知识库CRUD + 文档管理 + 上传索引
 */
import { useState, useEffect, useCallback } from'react'
import { motion, AnimatePresence } from'framer-motion'
import { icons } from'@/lib/icons'
import { cardStyle, heading, buttonStyle } from'@/lib/design-tokens'
import { knowledgeApi, type KnowledgeBase, type KnowledgeDocument } from'@/lib/api'
import { toast } from'sonner'

const KB_TYPE_CONFIG: Record<string, { label: string; icon: any; color: string }> = {
 law: { label:'法律法规', icon: icons.Scale, color:'text-primary bg-primary/5' },
 regulation: { label:'部门规章', icon: icons.Building2, color:'text-primary bg-primary/5' },
 case: { label:'司法判例', icon: icons.Briefcase, color:'text-warning bg-warning/10' },
 interpretation: { label:'司法解释', icon: icons.BookOpen, color:'text-success bg-success/10' },
 template: { label:'合同模板', icon: icons.FileCode, color:'text-rose-600 bg-rose-50' },
 article: { label:'法律文章', icon: icons.FileText, color:'text-cyan-600 bg-cyan-50' },
 internal: { label:'内部知识', icon: icons.Archive, color:'text-muted-foreground bg-muted' },
 other: { label:'其他', icon: icons.Database, color:'text-muted-foreground bg-muted/50' },
}

export function KnowledgeBaseManager() {
 const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
 const [loading, setLoading] = useState(true)
 const [selectedKb, setSelectedKb] = useState<KnowledgeBase | null>(null)
 const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
 const [docsLoading, setDocsLoading] = useState(false)
 const [showCreateModal, setShowCreateModal] = useState(false)
 const [filterType, setFilterType] = useState<string>('')

 // 创建知识库表单
 const [newKb, setNewKb] = useState({ name:'', knowledge_type:'law', description:'', is_public: false })
 const [creating, setCreating] = useState(false)

 // 上传
 const [uploading, setUploading] = useState(false)

 const loadKnowledgeBases = useCallback(async () => {
 setLoading(true)
 try {
 const data = await knowledgeApi.listBases({ knowledge_type: filterType || undefined })
 setKnowledgeBases(data.items || [])
 } catch (error: any) {
 toast.error(error.message ||'加载知识库列表失败')
 } finally {
 setLoading(false)
 }
 }, [filterType])

 useEffect(() => {
 loadKnowledgeBases()
 }, [loadKnowledgeBases])

 const loadDocuments = async (kb: KnowledgeBase) => {
 setSelectedKb(kb)
 setDocsLoading(true)
 try {
 const data = await knowledgeApi.listDocuments(kb.id)
 setDocuments(data.items || [])
 } catch (error: any) {
 toast.error(error.message ||'加载文档列表失败')
 } finally {
 setDocsLoading(false)
 }
 }

 const handleCreateKb = async () => {
 if (!newKb.name.trim()) {
 toast.error('请输入知识库名称')
 return
 }
 setCreating(true)
 try {
 await knowledgeApi.createBase(newKb)
 toast.success('知识库创建成功')
 setShowCreateModal(false)
 setNewKb({ name:'', knowledge_type:'law', description:'', is_public: false })
 await loadKnowledgeBases()
 } catch (error: any) {
 toast.error(error.message ||'创建失败')
 } finally {
 setCreating(false)
 }
 }

 const handleUploadFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
 const file = e.target.files?.[0]
 if (!file || !selectedKb) return

 setUploading(true)
 try {
 await knowledgeApi.uploadDocument(selectedKb.id, file)
 toast.success(`${file.name} 已上传并开始处理`)
 await loadDocuments(selectedKb)
 } catch (error: any) {
 toast.error(error.message ||'上传失败')
 } finally {
 setUploading(false)
 e.target.value =''
 }
 }

 const handleDeleteDoc = async (docId: string) => {
 try {
 await knowledgeApi.deleteDocument(docId)
 toast.success('文档已删除')
 if (selectedKb) await loadDocuments(selectedKb)
 } catch (error: any) {
 toast.error(error.message ||'删除失败')
 }
 }

 return (
 <div className="h-full flex">
 {/* 左侧知识库列表 */}
 <div className="w-80 border-r border-border flex flex-col bg-background">
 <div className="p-4 border-b border-border">
 <div className="flex items-center justify-between mb-3">
 <h3 className={heading.section}>知识库列表</h3>
 <button
 onClick={() => setShowCreateModal(true)}
 className={`flex items-center gap-1 ${buttonStyle.primary} text-xs shadow-sm`}
 >
 <icons.Plus className="w-3.5 h-3.5" />
 新建
 </button>
 </div>

 {/* 类型筛选 */}
 <div className="flex gap-1 flex-wrap">
 <button
 onClick={() => setFilterType('')}
 className={`px-2 py-1 text-[10px] rounded-md transition-colors ${
 !filterType ?'bg-primary/10 text-primary font-bold' :'bg-muted/50 text-muted-foreground hover:bg-muted'
 }`}
 >
 全部
 </button>
 {Object.entries(KB_TYPE_CONFIG).slice(0, 5).map(([key, config]) => (
 <button
 key={key}
 onClick={() => setFilterType(key === filterType ?'' : key)}
 className={`px-2 py-1 text-[10px] rounded-md transition-colors ${
 filterType === key ?'bg-primary/10 text-primary font-bold' :'bg-muted/50 text-muted-foreground hover:bg-muted'
 }`}
 >
 {config.label}
 </button>
 ))}
 </div>
 </div>

 <div className="flex-1 overflow-y-auto p-2 space-y-1">
 {loading ? (
 Array.from({ length: 5 }).map((_, i) => (
 <div key={i} className="p-3 rounded-xl animate-pulse">
 <div className="h-4 bg-muted rounded w-3/4 mb-2" />
 <div className="h-3 bg-muted/50 rounded w-1/2" />
 </div>
 ))
 ) : knowledgeBases.length > 0 ? (
 knowledgeBases.map((kb) => {
 const typeConfig = KB_TYPE_CONFIG[kb.knowledge_type] || KB_TYPE_CONFIG.other
 const TypeIcon = typeConfig.icon
 const isSelected = selectedKb?.id === kb.id
 return (
 <motion.button
 key={kb.id}
 onClick={() => loadDocuments(kb)}
 className={`w-full text-left p-3 rounded-xl transition-all ${
 isSelected
 ?'bg-primary/5 border border-primary/20 shadow-sm'
 :'hover:bg-muted/50 border border-transparent'
 }`}
 whileTap={{ scale: 0.98 }}
 >
 <div className="flex items-start gap-2.5">
 <div className={`p-1.5 rounded-lg flex-shrink-0 ${typeConfig.color}`}>
 <TypeIcon className="w-3.5 h-3.5" />
 </div>
 <div className="flex-1 min-w-0">
 <div className="font-medium text-sm text-foreground truncate">{kb.name}</div>
 <div className="flex items-center gap-2 mt-0.5">
 <span className="text-[10px] text-muted-foreground">{typeConfig.label}</span>
 <span className="text-[10px] text-muted-foreground/50">·</span>
 <span className="text-[10px] text-muted-foreground">{kb.doc_count} 篇文档</span>
 </div>
 {kb.description && (
 <p className="text-[10px] text-muted-foreground mt-1 line-clamp-1">{kb.description}</p>
 )}
 </div>
 <icons.ChevronRight className={`w-4 h-4 transition-transform flex-shrink-0 mt-0.5 ${
 isSelected ?'text-primary rotate-90' :'text-muted-foreground/50'
 }`} />
 </div>
 </motion.button>
 )
 })
 ) : (
 <div className="py-12 text-center">
 <icons.FolderOpen className="w-10 h-10 text-muted-foreground/30 mx-auto mb-3" />
 <p className="text-sm text-muted-foreground">暂无知识库</p>
 <p className="text-xs text-muted-foreground/50 mt-1">点击上方"新建"按钮创建</p>
 </div>
 )}
 </div>
 </div>

 {/* 右侧文档详情 */}
 <div className="flex-1 flex flex-col bg-muted/30">
 {selectedKb ? (
 <>
 {/* 知识库信息头部 */}
 <div className="p-6 bg-background border-b border-border">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 {(() => {
 const config = KB_TYPE_CONFIG[selectedKb.knowledge_type] || KB_TYPE_CONFIG.other
 const Icon = config.icon
 return (
 <div className={`p-2.5 rounded-xl ${config.color}`}>
 <Icon className="w-5 h-5" />
 </div>
 )
 })()}
 <div>
 <h3 className={heading.section}>{selectedKb.name}</h3>
 <p className="text-xs text-muted-foreground mt-0.5">
 {selectedKb.doc_count} 篇文档 · 创建于 {new Date(selectedKb.created_at).toLocaleDateString('zh-CN')}
 </p>
 </div>
 </div>
 <div className="flex items-center gap-2">
 <label className={`flex items-center gap-2 cursor-pointer ${
 uploading ? buttonStyle.secondary : `${buttonStyle.primary} shadow-sm`
 }`}>
 {uploading ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : <icons.Upload className="w-4 h-4" />}
 {uploading ?'上传中...' :'上传文件'}
 <input
 type="file"
 className="hidden"
 accept=".pdf,.doc,.docx,.txt,.md"
 onChange={handleUploadFile}
 disabled={uploading}
 />
 </label>
 <button
 onClick={() => loadDocuments(selectedKb)}
 className={buttonStyle.icon}
 >
 <icons.RefreshCw className="w-4 h-4" />
 </button>
 </div>
 </div>
 {selectedKb.description && (
 <p className="text-sm text-muted-foreground mt-3 bg-muted/50 p-3 rounded-lg">{selectedKb.description}</p>
 )}
 </div>

 {/* 文档列表 */}
 <div className="flex-1 overflow-y-auto p-6">
 {docsLoading ? (
 <div className="space-y-3">
 {Array.from({ length: 4 }).map((_, i) => (
 <div key={i} className={`${cardStyle.compact} animate-pulse`}>
 <div className="h-4 bg-muted rounded w-1/3 mb-2" />
 <div className="h-3 bg-muted/50 rounded w-2/3" />
 </div>
 ))}
 </div>
 ) : documents.length > 0 ? (
 <div className="space-y-2">
 {documents.map((doc, i) => (
 <motion.div
 key={doc.id}
 initial={{ opacity: 0, y: 5 }}
 animate={{ opacity: 1, y: 0 }}
 transition={{ delay: i * 0.02 }}
 className={`group ${cardStyle.interactive}`}
 >
 <div className="flex items-start justify-between">
 <div className="flex items-start gap-3 flex-1 min-w-0">
 <div className="p-2 bg-muted/50 rounded-lg flex-shrink-0">
 <icons.FileText className="w-4 h-4 text-muted-foreground" />
 </div>
 <div className="flex-1 min-w-0">
 <h4 className={`${heading.card} truncate`}>{doc.title}</h4>
 <div className="flex items-center gap-2 mt-1">
 {doc.source && (
 <span className="text-[10px] text-muted-foreground">来源: {doc.source}</span>
 )}
 <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
 doc.is_processed
 ?'bg-success/10 text-success'
 :'bg-warning/10 text-warning'
 }`}>
 {doc.is_processed ?'已索引' :'待索引'}
 </span>
 <span className="text-[10px] text-muted-foreground">
 {new Date(doc.created_at).toLocaleDateString('zh-CN')}
 </span>
 </div>
 {doc.summary && (
 <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">{doc.summary}</p>
 )}
 {doc.tags && doc.tags.length > 0 && (
 <div className="flex gap-1 mt-2 flex-wrap">
 {doc.tags.map((tag, ti) => (
 <span key={ti} className="text-[10px] px-1.5 py-0.5 bg-muted text-muted-foreground rounded">
 {tag}
 </span>
 ))}
 </div>
 )}
 </div>
 </div>
 <button
 onClick={() => handleDeleteDoc(doc.id)}
 className="p-1.5 text-muted-foreground/50 hover:text-destructive hover:bg-destructive/5 rounded-lg transition-all opacity-0 group-hover:opacity-100"
 title="删除文档"
 >
 <icons.Trash2 className="w-3.5 h-3.5" />
 </button>
 </div>
 </motion.div>
 ))}
 </div>
 ) : (
 <div className="py-20 text-center">
 <icons.FileText className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
 <p className="text-sm text-muted-foreground">该知识库暂无文档</p>
 <p className="text-xs text-muted-foreground/50 mt-1">上传 PDF、Word、TXT 等文件开始构建知识库</p>
 </div>
 )}
 </div>
 </>
 ) : (
 <div className="flex-1 flex items-center justify-center">
 <div className="text-center space-y-4">
 <div className="w-20 h-20 bg-primary/5 rounded-2xl flex items-center justify-center mx-auto">
 <icons.Database className="w-10 h-10 text-primary/30" />
 </div>
 <div>
 <p className="text-muted-foreground font-medium">选择一个知识库</p>
 <p className="text-xs text-muted-foreground/70 mt-1">从左侧列表选择知识库，管理文档和索引</p>
 </div>
 </div>
 </div>
 )}
 </div>

 {/* 创建知识库弹窗 */}
 <AnimatePresence>
 {showCreateModal && (
 <motion.div
 initial={{ opacity: 0 }}
 animate={{ opacity: 1 }}
 exit={{ opacity: 0 }}
 className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
 onClick={() => setShowCreateModal(false)}
 >
 <motion.div
 initial={{ scale: 0.95, opacity: 0 }}
 animate={{ scale: 1, opacity: 1 }}
 exit={{ scale: 0.95, opacity: 0 }}
 onClick={(e) => e.stopPropagation()}
 className="bg-background rounded-2xl shadow-2xl w-[480px] max-w-[90vw] overflow-hidden"
 >
 <div className="px-6 py-4 border-b border-border flex items-center justify-between">
 <h3 className={heading.section}>创建知识库</h3>
 <button onClick={() => setShowCreateModal(false)} className="text-muted-foreground hover:text-foreground">
 <icons.X className="w-5 h-5" />
 </button>
 </div>
 <div className="p-6 space-y-4">
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">知识库名称 *</label>
 <input
 type="text"
 value={newKb.name}
 onChange={(e) => setNewKb({ ...newKb, name: e.target.value })}
 placeholder="例如：劳动法法规库"
 className="w-full px-3 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
 />
 </div>
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">知识类型</label>
 <div className="grid grid-cols-4 gap-1.5">
 {Object.entries(KB_TYPE_CONFIG).map(([key, config]) => {
 const Icon = config.icon
 return (
 <button
 key={key}
 onClick={() => setNewKb({ ...newKb, knowledge_type: key })}
 className={`flex flex-col items-center gap-1 p-2.5 rounded-xl text-[10px] font-medium transition-all border ${
 newKb.knowledge_type === key
 ?'border-primary/30 bg-primary/5 text-primary'
 :'border-border bg-muted/50 text-muted-foreground hover:border-border'
 }`}
 >
 <Icon className="w-4 h-4" />
 {config.label}
 </button>
 )
 })}
 </div>
 </div>
 <div>
 <label className="block text-sm font-medium text-foreground mb-1.5">描述（可选）</label>
 <textarea
 value={newKb.description}
 onChange={(e) => setNewKb({ ...newKb, description: e.target.value })}
 placeholder="简要描述该知识库的用途..."
 className="w-full px-3 py-2.5 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary resize-none h-20"
 />
 </div>
 <label className="flex items-center gap-2 cursor-pointer">
 <input
 type="checkbox"
 checked={newKb.is_public}
 onChange={(e) => setNewKb({ ...newKb, is_public: e.target.checked })}
 className="w-4 h-4 rounded border-border text-primary focus:ring-primary"
 />
 <span className="text-sm text-muted-foreground">设为公开知识库</span>
 </label>
 </div>
 <div className="px-6 py-4 border-t border-border flex justify-end gap-2">
 <button
 onClick={() => setShowCreateModal(false)}
 className={buttonStyle.ghost}
 >
 取消
 </button>
 <button
 onClick={handleCreateKb}
 disabled={creating || !newKb.name.trim()}
 className={`flex items-center gap-2 ${buttonStyle.primary} disabled:opacity-50 shadow-sm`}
 >
 {creating ? <icons.Loader2 className="w-4 h-4 animate-spin" /> : <icons.Check className="w-4 h-4" />}
 创建
 </button>
 </div>
 </motion.div>
 </motion.div>
 )}
 </AnimatePresence>
 </div>
 )
}
