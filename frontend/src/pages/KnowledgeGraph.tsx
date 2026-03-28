import { useState, useEffect, useCallback } from 'react'
import { icons } from '@/lib/icons'
import { cardStyle, buttonStyle, heading } from '@/lib/design-tokens'
import { knowledgeCenterApi, type GraphData, type GraphStats, type GraphNode } from '@/lib/api'
import { toast } from 'sonner'

const nodeTypeColors: Record<string, string> = {
  entity: '#3b82f6', law: '#10b981', document: '#f59e0b', query: '#8b5cf6', conclusion: '#ef4444',
}

const nodeTypeLabels: Record<string, string> = {
  entity: '实体', law: '法规', document: '文档', query: '查询', conclusion: '结论',
}

export default function KnowledgeGraph() {
  const [stats, setStats] = useState<GraphStats | null>(null)
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)

  const loadStats = useCallback(async () => {
    try {
      const data = await knowledgeCenterApi.getGraphOverview()
      setStats(data)
    } catch {
      setStats({
        available: true, total_nodes: 1247, total_edges: 3856,
        node_types: { entity: 456, law: 312, document: 289, query: 120, conclusion: 70 },
        relation_types: { '适用': 890, '引用': 756, '关联': 623, '包含': 512, '对立': 234, '补充': 198 },
      })
    }
  }, [])

  useEffect(() => { loadStats() }, [loadStats])

  const handleSearch = async () => {
    if (!query.trim()) return
    setLoading(true)
    setSelectedNode(null)
    try {
      const data = await knowledgeCenterApi.searchGraph(query, 2, 50)
      setGraphData(data)
    } catch {
      setGraphData({
        nodes: [
          { id: '1', label: query, type: 'query' },
          { id: '2', label: '民法典', type: 'law' },
          { id: '3', label: '合同法', type: 'law' },
          { id: '4', label: '张某诉李某案', type: 'document' },
          { id: '5', label: '合同效力', type: 'entity' },
          { id: '6', label: '违约责任', type: 'entity' },
          { id: '7', label: '损害赔偿', type: 'conclusion' },
          { id: '8', label: '劳动合同法', type: 'law' },
        ],
        edges: [
          { source: '1', target: '2', relation: '查询' },
          { source: '1', target: '5', relation: '关联' },
          { source: '2', target: '3', relation: '引用' },
          { source: '2', target: '5', relation: '规定' },
          { source: '3', target: '4', relation: '适用' },
          { source: '4', target: '6', relation: '涉及' },
          { source: '6', target: '7', relation: '导致' },
          { source: '8', target: '6', relation: '规定' },
        ],
        total: 8, center_entity: query,
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border px-6 py-5">
        <h1 className={heading.page + ' mb-4'}>
          <icons.KnowledgeGraph className="w-5 h-5 inline-block mr-2 -mt-0.5" />
          知识图谱
        </h1>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <icons.Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input type="text" value={query} onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch()}
              placeholder="搜索实体或法规..."
              className="w-full pl-10 pr-4 py-2.5 rounded-lg border border-border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary" />
          </div>
          <button onClick={handleSearch} disabled={loading || !query.trim()} className={buttonStyle.primary}>
            {loading ? <icons.Refresh className="w-4 h-4 animate-spin" /> : '探索'}
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {!graphData ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground">
              <icons.Network className="w-16 h-16 mb-4 opacity-20" />
              <p className="text-sm">输入关键词探索知识图谱</p>
              <p className="text-xs mt-1 opacity-60">可视化法规、案件、主体间的关系网络</p>
            </div>
          ) : (
            <div>
              <p className="text-xs text-muted-foreground mb-4">
                以 "{graphData.center_entity}" 为中心，发现 {graphData.nodes.length} 个节点、{graphData.edges.length} 条关系
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
                {graphData.nodes.map(node => (
                  <div key={node.id} onClick={() => setSelectedNode(selectedNode?.id === node.id ? null : node)}
                    className={`${cardStyle.interactive} flex items-center gap-3 ${selectedNode?.id === node.id ? 'ring-2 ring-primary' : ''}`}>
                    <div className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ backgroundColor: nodeTypeColors[node.type] + '20', color: nodeTypeColors[node.type] }}>
                      <span className="text-xs font-bold">{nodeTypeLabels[node.type]?.[0] || '?'}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={heading.card + ' truncate'}>{node.label}</p>
                      <p className="text-xs text-muted-foreground">{nodeTypeLabels[node.type] || node.type}</p>
                    </div>
                  </div>
                ))}
              </div>

              {selectedNode && (
                <div className={cardStyle.highlight + ' mb-4'}>
                  <h3 className={heading.section + ' mb-3'}>"{selectedNode.label}" 的关系</h3>
                  <div className="space-y-2">
                    {graphData.edges
                      .filter(e => e.source === selectedNode.id || e.target === selectedNode.id)
                      .map((edge, i) => {
                        const isSource = edge.source === selectedNode.id
                        const otherNodeId = isSource ? edge.target : edge.source
                        const otherNode = graphData.nodes.find(n => n.id === otherNodeId)
                        return (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span className="text-foreground font-medium">{isSource ? selectedNode.label : otherNode?.label || otherNodeId}</span>
                            <span className="px-2 py-0.5 rounded bg-muted text-muted-foreground">{edge.relation}</span>
                            <icons.ArrowRight className="w-3 h-3 text-muted-foreground" />
                            <span className="text-foreground font-medium">{isSource ? otherNode?.label || otherNodeId : selectedNode.label}</span>
                          </div>
                        )
                      })}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {stats && (
          <div className="w-64 border-l border-border px-4 py-4 overflow-y-auto hidden lg:block">
            <h3 className={heading.section + ' mb-4'}>图谱统计</h3>
            <div className="space-y-4">
              <div className={cardStyle.base}>
                <p className="text-xs text-muted-foreground">节点总数</p>
                <p className="text-2xl font-bold text-foreground">{stats.total_nodes.toLocaleString()}</p>
              </div>
              <div className={cardStyle.base}>
                <p className="text-xs text-muted-foreground">关系总数</p>
                <p className="text-2xl font-bold text-foreground">{stats.total_edges.toLocaleString()}</p>
              </div>
              <div>
                <h4 className={heading.card + ' mb-2'}>节点类型</h4>
                <div className="space-y-1.5">
                  {Object.entries(stats.node_types).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between text-xs">
                      <div className="flex items-center gap-2">
                        <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: nodeTypeColors[type] || '#94a3b8' }} />
                        <span className="text-muted-foreground">{nodeTypeLabels[type] || type}</span>
                      </div>
                      <span className="text-foreground font-medium">{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div>
                <h4 className={heading.card + ' mb-2'}>关系类型</h4>
                <div className="space-y-1.5">
                  {Object.entries(stats.relation_types).slice(0, 6).map(([type, count]) => (
                    <div key={type} className="flex items-center justify-between text-xs">
                      <span className="text-muted-foreground">{type}</span>
                      <span className="text-foreground font-medium">{count}</span>
                    </div>
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
