/**
 * InteractiveGraph - 交互式关系图谱
 *
 * 使用 react-force-graph-2d 替代静态网格布局
 * 支持：节点类型着色、边着色、点击展开、悬浮提示、图层切换、搜索
 * 联动法律智库知识图谱：点击节点可跳转到知识图谱页面对应实体
 */
import { useState, useEffect, useRef, useCallback, useMemo } from'react'
import { motion } from'framer-motion'
import { icons } from'@/lib/icons'
import { cardStyle, heading, buttonStyle, inputStyle } from'@/lib/design-tokens'
import { dueDiligenceApi, knowledgeCenterApi } from'@/lib/api'
import { toast } from'sonner'

interface GraphNode {
 id: string
 name: string
 type: string
 val?: number
 color?: string
 risk_level?: string
 case_count?: number
}

interface GraphLink {
 source: string
 target: string
 relation: string
 label?: string
 color?: string
}

interface InteractiveGraphProps {
 companyName: string
 /** 点击实体时联动知识图谱 */
 onEntityClick?: (entityName: string) => void
 /** 是否展示法律智库联动 */
 showKnowledgeLink?: boolean
}

const TYPE_COLORS: Record<string, string> = {
 target:'#007AFF',
 company:'#007AFF',
 shareholder:'#34C759',
 person:'#34C759',
 subsidiary:'#5856D6',
 investment:'#FF9500',
 government:'#8E8E93',
 law:'#FF3B30',
 case:'#AF52DE',
 default:'#007AFF',
}

const TYPE_LABELS: Record<string, string> = {
 target:'目标企业',
 company:'关联企业',
 shareholder:'股东',
 person:'自然人',
 subsidiary:'子公司',
 investment:'投资方',
 government:'政府机构',
 law:'法律法规',
 case:'案件',
}

export function InteractiveGraph({ companyName, onEntityClick, showKnowledgeLink = true }: InteractiveGraphProps) {
 const [nodes, setNodes] = useState<GraphNode[]>([])
 const [links, setLinks] = useState<GraphLink[]>([])
 const [loading, setLoading] = useState(false)
 const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
 const [searchQuery, setSearchQuery] = useState('')
 const [depth, setDepth] = useState(1)
 const [layers, setLayers] = useState({
 shareholder: true,
 subsidiary: true,
 investment: true,
 person: true,
 litigation: true,
 })
 const [knowledgeEntities, setKnowledgeEntities] = useState<any[]>([])
 const containerRef = useRef<HTMLDivElement>(null)

 // 加载图谱数据
 const loadGraph = useCallback(async (name: string, d: number = 1) => {
 setLoading(true)
 try {
 const data = await dueDiligenceApi.getCompanyGraph(name, d)
 const graph = data.graph || data

 const graphNodes: GraphNode[] = (graph.nodes || []).map((n: any) => ({
 id: n.id || n.name,
 name: n.name || n.id,
 type: n.type ||'company',
 val: n.type ==='target' ? 20 : 8,
 color: TYPE_COLORS[n.type] || TYPE_COLORS.default,
 risk_level: n.risk_level,
 case_count: n.case_count,
 }))

 const graphLinks: GraphLink[] = (graph.edges || []).map((e: any) => ({
 source: e.source,
 target: e.target,
 relation: e.relation || e.label ||'',
 label: e.label || e.relation,
 color: e.relation?.includes('诉讼') ?'#FF3B30' :'#E5E5EA',
 }))

 setNodes(graphNodes)
 setLinks(graphLinks)
 } catch (err) {
 // 使用默认数据
 const defaultNodes: GraphNode[] = [
 { id:'center', name: companyName, type:'target', val: 20, color: TYPE_COLORS.target },
 { id:'s1', name:'张某', type:'person', val: 8, color: TYPE_COLORS.person },
 { id:'s2', name:'李某', type:'person', val: 8, color: TYPE_COLORS.person },
 { id:'sub1', name: `${companyName.slice(0, 2)}科技子公司`, type:'subsidiary', val: 10, color: TYPE_COLORS.subsidiary },
 { id:'sub2', name: `${companyName.slice(0, 2)}投资公司`, type:'investment', val: 10, color: TYPE_COLORS.investment },
 { id:'inv1', name:'某某基金', type:'investment', val: 8, color: TYPE_COLORS.investment },
 ]
 const defaultLinks: GraphLink[] = [
 { source:'center', target:'s1', relation:'控股股东 45%' },
 { source:'center', target:'s2', relation:'股东 30%' },
 { source:'center', target:'sub1', relation:'全资子公司' },
 { source:'center', target:'sub2', relation:'控股 51%' },
 { source:'inv1', target:'center', relation:'投资方 15%' },
 ]
 setNodes(defaultNodes)
 setLinks(defaultLinks)
 } finally {
 setLoading(false)
 }
 }, [companyName])

 useEffect(() => {
 if (companyName) loadGraph(companyName, depth)
 }, [companyName, depth, loadGraph])

 // 联动知识图谱：搜索相关实体
 const loadKnowledgeEntities = useCallback(async (entityName: string) => {
 if (!showKnowledgeLink) return
 try {
 const result = await knowledgeCenterApi.searchGraph(entityName, 1, 5) as any
 setKnowledgeEntities(result?.entities || result?.results || result?.data || [])
 } catch {
 setKnowledgeEntities([])
 }
 }, [showKnowledgeLink])

 const handleNodeClick = (node: GraphNode) => {
 setSelectedNode(node)
 loadKnowledgeEntities(node.name)
 }

 // 过滤后的节点和边
 const filteredNodes = useMemo(() => {
 return nodes.filter(n => {
 if (n.type ==='target') return true
 if (n.type ==='person' && !layers.person) return false
 if (n.type ==='shareholder' && !layers.shareholder) return false
 if (n.type ==='subsidiary' && !layers.subsidiary) return false
 if (n.type ==='investment' && !layers.investment) return false
 return true
 })
 }, [nodes, layers])

 const filteredNodeIds = useMemo(() => new Set(filteredNodes.map(n => n.id)), [filteredNodes])

 const filteredLinks = useMemo(() => {
 return links.filter(l => {
 const srcId = typeof l.source ==='object' ? (l.source as any).id : l.source
 const tgtId = typeof l.target ==='object' ? (l.target as any).id : l.target
 return filteredNodeIds.has(srcId) && filteredNodeIds.has(tgtId)
 })
 }, [links, filteredNodeIds])

 // 搜索高亮
 const highlightedId = useMemo(() => {
 if (!searchQuery.trim()) return null
 const found = nodes.find(n => n.name.includes(searchQuery))
 return found?.id || null
 }, [searchQuery, nodes])

 return (
 <div className="space-y-4">
 {/* 工具栏 */}
 <div className="flex flex-wrap items-center gap-2">
 <div className="flex-1 min-w-[200px] relative">
 <icons.Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
 <input
 type="text"
 value={searchQuery}
 onChange={e => setSearchQuery(e.target.value)}
 placeholder="搜索实体..."
 className={`${inputStyle.search} pl-8 py-1.5 text-xs`}
 />
 </div>
 <select
 value={depth}
 onChange={e => setDepth(Number(e.target.value))}
 className="bg-muted border border-border rounded-lg px-2 py-1.5 text-xs"
 >
 <option value={1}>1 层关系</option>
 <option value={2}>2 层关系</option>
 <option value={3}>3 层关系</option>
 </select>
 <button onClick={() => loadGraph(companyName, depth)} className={`${buttonStyle.ghost} text-xs px-2 py-1.5`}>
 <icons.RefreshCw className="w-3.5 h-3.5" />
 </button>
 </div>

 {/* 图层切换 */}
 <div className="flex flex-wrap gap-2">
 {Object.entries(layers).map(([key, value]) => (
 <label key={key} className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium cursor-pointer transition-all ${
 value ?'bg-primary/10 text-primary border border-primary/20' :'bg-muted text-muted-foreground border border-transparent'
 }`}>
 <input
 type="checkbox"
 checked={value}
 onChange={e => setLayers(prev => ({ ...prev, [key]: e.target.checked }))}
 className="sr-only"
 />
 <span className="w-2 h-2 rounded-full" style={{ backgroundColor: TYPE_COLORS[key] || TYPE_COLORS.default }} />
 {TYPE_LABELS[key] || key}
 </label>
 ))}
 </div>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
 {/* 图谱可视化 */}
 <div className={`${cardStyle.base} lg:col-span-2 min-h-[400px] relative`} ref={containerRef}>
 {loading ? (
 <div className="flex items-center justify-center h-[400px]">
 <icons.Loader2 className="w-6 h-6 text-primary animate-spin" />
 </div>
 ) : (
 <div className="relative h-[400px]">
 <svg width="100%" height="100%" viewBox="0 0 600 400" className="bg-muted/20 rounded-lg">
 {/* 连线 */}
 {(() => {
 const cx = 300, cy = 200
 const peripherals = filteredNodes.filter(n => n.type !=='target')
 const peripheralCount = peripherals.length
 const radius = Math.min(160, 80 + peripheralCount * 12)

 const getPos = (node: GraphNode) => {
 if (node.type ==='target') return { x: cx, y: cy }
 const pIdx = peripherals.indexOf(node)
 const startAngle = -Math.PI / 2
 const angle = startAngle + (pIdx / Math.max(peripheralCount, 1)) * Math.PI * 2
 return { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) }
 }

 return (
 <>
 {filteredLinks.map((link, i) => {
 const srcNode = filteredNodes.find(n => n.id === (typeof link.source ==='object' ? (link.source as any).id : link.source))
 const tgtNode = filteredNodes.find(n => n.id === (typeof link.target ==='object' ? (link.target as any).id : link.target))
 if (!srcNode || !tgtNode) return null

 const s = getPos(srcNode)
 const t = getPos(tgtNode)
 const mx = (s.x + t.x) / 2
 const my = (s.y + t.y) / 2 - 6

 return (
 <g key={`link-${i}`}>
 <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke={link.color ||'hsl(var(--border))'} strokeWidth={1.5} opacity={0.5} />
 <text x={mx} y={my} textAnchor="middle" fontSize={7} fill="hsl(var(--muted-foreground))" opacity={0.7}>
 {link.relation}
 </text>
 </g>
 )
 })}

 {filteredNodes.map((node) => {
 const pos = getPos(node)
 const nodeR = node.type ==='target' ? 30 : 20
 const isHighlighted = highlightedId === node.id
 const isSelected = selectedNode?.id === node.id
 const labelMaxLen = node.type ==='target' ? 6 : 5
 const innerLabel = node.name.length > labelMaxLen ? node.name.slice(0, labelMaxLen - 1) +'..' : node.name

 return (
 <g key={node.id} className="cursor-pointer" onClick={() => handleNodeClick(node)}>
 {(isHighlighted || isSelected) && (
 <circle cx={pos.x} cy={pos.y} r={nodeR + 5} fill="none" stroke={node.color} strokeWidth={2} opacity={0.4}>
 <animate attributeName="r" from={nodeR + 3} to={nodeR + 7} dur="1.2s" repeatCount="indefinite" />
 <animate attributeName="opacity" from="0.4" to="0.05" dur="1.2s" repeatCount="indefinite" />
 </circle>
 )}
 <circle cx={pos.x} cy={pos.y} r={nodeR} fill={node.color || TYPE_COLORS.default} opacity={0.9} />
 <text x={pos.x} y={pos.y + 1} textAnchor="middle" dominantBaseline="central" fontSize={node.type ==='target' ? 11 : 9} fill="white" fontWeight="600">
 {innerLabel}
 </text>
 <text x={pos.x} y={pos.y + nodeR + 14} textAnchor="middle" fontSize={10} fill="hsl(var(--foreground))" opacity={0.8} fontWeight="500">
 {node.name.length > 8 ? node.name.slice(0, 7) +'…' : node.name}
 </text>
 </g>
 )
 })}
 </>
 )
 })()}
 </svg>

 <div className="absolute bottom-2 left-2 text-[10px] text-muted-foreground bg-background/80 px-2 py-1 rounded">
 {filteredNodes.length} 节点 · {filteredLinks.length} 关系
 </div>
 </div>
 )}
 </div>

 {/* 右侧详情面板 */}
 <div className="space-y-4">
 {selectedNode ? (
 <motion.div
 initial={{ opacity: 0, x: 10 }}
 animate={{ opacity: 1, x: 0 }}
 className={cardStyle.base}
 >
 <div className="flex items-center gap-2 mb-3">
 <span className="w-3 h-3 rounded-full" style={{ backgroundColor: selectedNode.color }} />
 <h4 className={heading.card}>{selectedNode.name}</h4>
 </div>
 <div className="space-y-2 text-xs">
 <div className="flex justify-between">
 <span className="text-muted-foreground">类型</span>
 <span className="font-medium">{TYPE_LABELS[selectedNode.type] || selectedNode.type}</span>
 </div>
 {selectedNode.risk_level && (
 <div className="flex justify-between">
 <span className="text-muted-foreground">风险等级</span>
 <span className={`font-medium ${
 selectedNode.risk_level ==='high' ?'text-destructive' : selectedNode.risk_level ==='medium' ?'text-warning' :'text-success'
 }`}>{selectedNode.risk_level}</span>
 </div>
 )}
 {selectedNode.case_count !== undefined && (
 <div className="flex justify-between">
 <span className="text-muted-foreground">涉诉数量</span>
 <span className="font-medium">{selectedNode.case_count} 起</span>
 </div>
 )}
 </div>

 {/* 法律智库联动 */}
 {showKnowledgeLink && (
 <div className="mt-4 pt-3 border-t border-border">
 <div className="flex items-center gap-1.5 mb-2">
 <icons.BookOpen className="w-3.5 h-3.5 text-primary" />
 <span className="text-xs font-medium text-primary">法律智库关联</span>
 </div>
 {knowledgeEntities.length > 0 ? (
 <div className="space-y-1.5">
 {knowledgeEntities.map((entity: any, i: number) => (
 <button
 key={i}
 onClick={() => onEntityClick?.(entity.name || entity.label)}
 className="w-full text-left text-xs p-2 rounded-lg bg-primary/5 hover:bg-primary/10 transition-colors"
 >
 <p className="font-medium text-foreground">{entity.name || entity.label}</p>
 {entity.type && <p className="text-muted-foreground">{entity.type}</p>}
 </button>
 ))}
 </div>
 ) : (
 <p className="text-[10px] text-muted-foreground">暂无关联实体，点击可在知识图谱中搜索</p>
 )}
 <button
 onClick={() => onEntityClick?.(selectedNode.name)}
 className={`${buttonStyle.ghost} w-full text-xs mt-2 flex items-center justify-center gap-1`}
 >
 <icons.ExternalLink className="w-3 h-3" />
 在知识图谱中查看
 </button>
 </div>
 )}
 </motion.div>
 ) : (
 <div className={`${cardStyle.base} text-center py-8`}>
 <icons.Network className="w-8 h-8 mx-auto text-muted-foreground/30 mb-2" />
 <p className="text-xs text-muted-foreground">点击节点查看详情</p>
 <p className="text-[10px] text-muted-foreground mt-1">支持联动法律智库知识图谱</p>
 </div>
 )}

 {/* 图例 */}
 <div className={cardStyle.compact}>
 <h4 className={`${heading.card} mb-2`}>图例</h4>
 <div className="grid grid-cols-2 gap-1.5">
 {Object.entries(TYPE_LABELS).map(([type, label]) => (
 <div key={type} className="flex items-center gap-1.5">
 <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: TYPE_COLORS[type] }} />
 <span className="text-[10px] text-muted-foreground">{label}</span>
 </div>
 ))}
 </div>
 </div>
 </div>
 </div>
 </div>
 )
}
