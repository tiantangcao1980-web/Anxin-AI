import { useState, useEffect, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, buttonStyle, heading, statusColor } from '@/lib/design-tokens'
import { knowledgeApi, type KnowledgeBase as KB, type KnowledgeDocument } from '@/lib/api'
import { toast } from 'sonner'

export default function KnowledgeBase() {
  const [bases, setBases] = useState<KB[]>([])
  const [selectedBase, setSelectedBase] = useState<KB | null>(null)
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [loading, setLoading] = useState(false)
  const [docLoading, setDocLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newBase, setNewBase] = useState({ name: '', description: '', knowledge_type: 'general' })

  const loadBases = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await knowledgeApi.listBases()
      setBases(data.items || [])
    } catch {
      // @mock-data FALLBACK
      toast.warning('API 不可用，使用演示数据')
      setBases([
        { id: '1', name: '法规库', knowledge_type: 'regulation', description: '最新法律法规汇编', document_count: 156, is_public: true, created_at: '2024-01-15' },
        { id: '2', name: '判例库', knowledge_type: 'case_law', description: '经典判例与裁判文书', document_count: 89, is_public: true, created_at: '2024-02-20' },
        { id: '3', name: '合同模板库', knowledge_type: 'template', description: '标准合同模板与条款', document_count: 42, is_public: false, created_at: '2024-03-10' },
        { id: '4', name: '内部知识', knowledge_type: 'internal', description: '团队沉淀的内部知识', document_count: 23, is_public: false, created_at: '2024-04-05' },
      ] as any[])
    } finally {
      setLoading(false)
    }
  }, [])

  const loadDocuments = useCallback(async (kbId: string) => {
    setDocLoading(true)
    try {
      const data = await knowledgeApi.listDocuments(kbId)
      setDocuments(data.items || [])
    } catch {
      // @mock-data FALLBACK
      toast.warning('API 不可用，使用演示数据')
      setDocuments([
        { id: 'd1', title: '民法典总则编解读', source: '法律出版社', summary: '对民法典总则编的逐条解读与实务分析', is_processed: true, tags: ['民法典', '总则'], created_at: '2024-01-20' },
        { id: 'd2', title: '劳动合同法实务指南', source: '内部整理', summary: '劳动合同签订、变更、解除的法律要点', is_processed: true, tags: ['劳动法', '合同'], created_at: '2024-02-15' },
        { id: 'd3', title: '知识产权保护案例集', source: '最高法公报', summary: '近年来知识产权典型案例汇编', is_processed: false, tags: ['知识产权', '案例'], created_at: '2024-03-01' },
      ] as any[])
    } finally {
      setDocLoading(false)
    }
  }, [])

  useEffect(() => { loadBases() }, [loadBases])

  useEffect(() => {
    if (selectedBase) loadDocuments(selectedBase.id)
  }, [selectedBase, loadDocuments])

  const handleCreateBase = async () => {
    if (!newBase.name.trim()) { toast.error('请输入知识库名称'); return }
    try {
      await knowledgeApi.createBase(newBase)
      toast.success('知识库创建成功')
      setShowCreate(false)
      setNewBase({ name: '', description: '', knowledge_type: 'general' })
      loadBases()
    } catch (err: any) {
      toast.error('创建失败: ' + (err.message || '未知错误'))
    }
  }

  const kbTypeLabel: Record<string, string> = {
    regulation: '法规', case_law: '判例', template: '模板', internal: '内部', general: '通用',
  }

  const kbTypeColor: Record<string, string> = {
    regulation: statusColor.info, case_law: statusColor.success, template: statusColor.warning,
    internal: statusColor.neutral, general: statusColor.neutral,
  }

  // 文档详情视图
  if (selectedBase) {
    return (
      <div className="h-full flex flex-col">
        <div className="border-b border-border px-6 py-4 flex items-center gap-3">
          <button onClick={() => { setSelectedBase(null); setDocuments([]) }} className="p-1 rounded hover:bg-muted">
            <icons.ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <h1 className={heading.page}>{selectedBase.name}</h1>
            <p className="text-xs text-muted-foreground">{selectedBase.description}</p>
          </div>
          <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${kbTypeColor[selectedBase.knowledge_type || 'general']}`}>
            {kbTypeLabel[selectedBase.knowledge_type || 'general'] || '通用'}
          </span>
        </div>

        <div className="flex-1 overflow-y-auto px-6 py-4">
          {docLoading ? (
            <div className="flex items-center justify-center py-20">
              <icons.Refresh className="w-5 h-5 animate-spin text-primary" />
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
              <icons.FileText className="w-12 h-12 mb-3 opacity-30" />
              <p className="text-sm">暂无文档</p>
            </div>
          ) : (
            <div className="space-y-3">
              {documents.map(doc => (
                <div key={doc.id} className={cardStyle.interactive}>
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <icons.FileText className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                        <h3 className={heading.card}>{doc.title}</h3>
                      </div>
                      {doc.summary && <p className="text-xs text-muted-foreground ml-6 line-clamp-2">{doc.summary}</p>}
                      <div className="flex items-center gap-3 mt-2 ml-6">
                        {doc.source && <span className="text-xs text-muted-foreground">{doc.source}</span>}
                        {doc.tags?.map(tag => (
                          <span key={tag} className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{tag}</span>
                        ))}
                      </div>
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded-full flex-shrink-0 ${doc.is_processed ? statusColor.success : statusColor.warning}`}>
                      {doc.is_processed ? '已索引' : '处理中'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    )
  }

  // 知识库列表视图
  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border px-6 py-5 flex items-center justify-between">
        <h1 className={heading.page}>
          <icons.KnowledgeBase className="w-5 h-5 inline-block mr-2 -mt-0.5" />
          司法智库
        </h1>
        <button onClick={() => setShowCreate(!showCreate)} className={buttonStyle.primary}>
          <icons.Plus className="w-4 h-4 inline-block mr-1" />
          新建知识库
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-6 py-4">
        {showCreate && (
          <div className={cardStyle.highlight + ' mb-6'}>
            <h3 className={heading.section + ' mb-3'}>新建知识库</h3>
            <div className="space-y-3">
              <input type="text" value={newBase.name} onChange={e => setNewBase({ ...newBase, name: e.target.value })}
                placeholder="知识库名称" className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
              <input type="text" value={newBase.description} onChange={e => setNewBase({ ...newBase, description: e.target.value })}
                placeholder="描述（可选）" className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20" />
              <select value={newBase.knowledge_type} onChange={e => setNewBase({ ...newBase, knowledge_type: e.target.value })}
                className="w-full px-3 py-2 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20">
                <option value="general">通用</option>
                <option value="regulation">法规</option>
                <option value="case_law">判例</option>
                <option value="template">模板</option>
                <option value="internal">内部知识</option>
              </select>
              <div className="flex gap-2 justify-end">
                <button onClick={() => setShowCreate(false)} className={buttonStyle.ghost}>取消</button>
                <button onClick={handleCreateBase} className={buttonStyle.primary}>创建</button>
              </div>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20">
            <icons.Refresh className="w-6 h-6 animate-spin text-primary" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <icons.AlertTriangle className="w-12 h-12 mb-3 opacity-30" />
            <p className="text-sm mb-3">{error}</p>
            <button onClick={loadBases} className={buttonStyle.primary}>
              <icons.Refresh className="w-4 h-4 inline-block mr-1" />
              重试
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {bases.map(kb => (
              <div key={kb.id} onClick={() => setSelectedBase(kb)} className={cardStyle.interactive}>
                <div className="flex items-start justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <icons.BookOpen className="w-5 h-5 text-primary" />
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${kbTypeColor[kb.knowledge_type || 'general']}`}>
                    {kbTypeLabel[kb.knowledge_type || 'general'] || '通用'}
                  </span>
                </div>
                <h3 className={heading.card + ' mb-1'}>{kb.name}</h3>
                <p className="text-xs text-muted-foreground line-clamp-2 mb-3">{kb.description || '暂无描述'}</p>
                <div className="flex items-center justify-between text-xs text-muted-foreground">
                  <span>{(kb as any).document_count || 0} 篇文档</span>
                  <span>{kb.is_public ? '公开' : '私有'}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
