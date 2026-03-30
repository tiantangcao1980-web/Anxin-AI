// -*- coding: utf-8 -*-
/**
 * KnowledgeGraph.tsx - 商业级交互式知识图谱页面
 *
 * 功能：
 * - react-force-graph 2D/3D 图谱可视化（ForceGraphCanvas 组件）
 * - 搜索、过滤、路径查询
 * - 实体详情抽屉（GraphDetailDrawer）
 * - 浮动工具栏 + 图例
 * - 统计面板（recharts PieChart）
 * - 实体/关系 CRUD、导入导出、AI 抽取
 */

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import {
  cardStyle,
  buttonStyle,
  heading,
  inputStyle,
  statusBadge,
  iconSize,
  chartColors,
} from '@/lib/design-tokens'
import { PageContainer } from '@/components/ui/PageContainer'
import { knowledgeCenterApi, type GraphData, type GraphEdge } from '@/lib/api'
import { toast } from 'sonner'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import {
  ForceGraphCanvas,
  GraphLegend,
  GraphToolbar,
  GraphDetailDrawer,
} from '@/components/knowledge-graph'
import type { ForceGraphNode, ForceGraphEdge } from '@/components/knowledge-graph'

// ============================================================
// 类型定义
// ============================================================

/** 页面内部节点（兼容 ForceGraphNode，无物理字段） */
interface ForceNode {
  id: string
  name: string
  type: string
  relationCount: number
  properties?: Record<string, string>
}

/** 页面内部边（同 ForceGraphEdge） */
interface ForceEdge {
  source: string
  target: string
  label: string
}

interface EntityDetail {
  name: string
  type: string
  properties: Record<string, string>
  outEdges: { target: string; label: string }[]
  inEdges: { source: string; label: string }[]
  documents?: { id: string; title: string }[]
}

interface GraphOverviewStats {
  available: boolean
  total_nodes: number
  total_edges: number
  node_types: Record<string, number>
  relation_types: Record<string, number>
}

interface SearchResult {
  id: string
  name: string
  type: string
}

// ============================================================
// 常量
// ============================================================

const NODE_TYPE_COLORS: Record<string, string> = {
  '法规': '#22c55e',
  '案例': '#3b82f6',
  '当事人': '#f59e0b',
  '机构': '#8b5cf6',
  '律师': '#ec4899',
  '其他': '#6b7280',
  // API 旧字段兼容
  law: '#22c55e',
  entity: '#3b82f6',
  document: '#f59e0b',
  query: '#8b5cf6',
  conclusion: '#ec4899',
}

const NODE_TYPE_LABELS: Record<string, string> = {
  '法规': '法规',
  '案例': '案例',
  '当事人': '当事人',
  '机构': '机构',
  '律师': '律师',
  '其他': '其他',
  law: '法规',
  entity: '实体',
  document: '文档',
  query: '查询',
  conclusion: '结论',
}

const MAX_VISIBLE_NODES = 200
const DEBOUNCE_MS = 300

// ============================================================
// Mock 数据 (API fallback)
// ============================================================

// @mock-data FALLBACK
const MOCK_STATS: GraphOverviewStats = {
  available: true,
  total_nodes: 1247,
  total_edges: 3856,
  node_types: { '法规': 312, '案例': 456, '当事人': 189, '机构': 120, '律师': 100, '其他': 70 },
  relation_types: { '适用': 890, '引用': 756, '关联': 623, '包含': 512, '对立': 234, '补充': 198 },
}

// @mock-data FALLBACK
function generateMockSearchResults(keyword: string): SearchResult[] {
  return [
    { id: 'm1', name: `${keyword}相关法规`, type: '法规' },
    { id: 'm2', name: `${keyword}典型案例`, type: '案例' },
    { id: 'm3', name: `${keyword}当事人甲`, type: '当事人' },
    { id: 'm4', name: `${keyword}代理律师`, type: '律师' },
    { id: 'm5', name: `${keyword}审理机构`, type: '机构' },
  ]
}

// @mock-data FALLBACK
function generateMockSubgraph(centerName: string): { nodes: ForceNode[]; edges: ForceEdge[] } {
  const center: ForceNode = {
    id: 'c0', name: centerName, type: '案例', relationCount: 7,
  }
  const satellites: ForceNode[] = [
    { id: 's1', name: '民法典', type: '法规', relationCount: 5 },
    { id: 's2', name: '合同法', type: '法规', relationCount: 4 },
    { id: 's3', name: '张某', type: '当事人', relationCount: 3 },
    { id: 's4', name: '李某', type: '当事人', relationCount: 2 },
    { id: 's5', name: '北京市高级人民法院', type: '机构', relationCount: 6 },
    { id: 's6', name: '王律师', type: '律师', relationCount: 3 },
    { id: 's7', name: '侵权责任法', type: '法规', relationCount: 4 },
    { id: 's8', name: '合同效力争议', type: '案例', relationCount: 2 },
    { id: 's9', name: '刘律师', type: '律师', relationCount: 1 },
    { id: 's10', name: '赵某', type: '当事人', relationCount: 2 },
    { id: 's11', name: '损害赔偿', type: '其他', relationCount: 3 },
    { id: 's12', name: '违约金', type: '其他', relationCount: 2 },
  ]
  const edges: ForceEdge[] = [
    { source: 'c0', target: 's1', label: '适用' },
    { source: 'c0', target: 's3', label: '原告' },
    { source: 'c0', target: 's4', label: '被告' },
    { source: 'c0', target: 's5', label: '审理' },
    { source: 'c0', target: 's6', label: '代理' },
    { source: 'c0', target: 's11', label: '判决' },
    { source: 's1', target: 's2', label: '引用' },
    { source: 's2', target: 's8', label: '适用' },
    { source: 's3', target: 's10', label: '关联' },
    { source: 's7', target: 'c0', label: '适用' },
    { source: 's6', target: 's3', label: '代理' },
    { source: 's9', target: 's4', label: '代理' },
    { source: 's11', target: 's12', label: '包含' },
    { source: 's5', target: 's8', label: '审理' },
  ]
  return { nodes: [center, ...satellites], edges }
}

// @mock-data FALLBACK
function generateMockPath(from: string, to: string): { nodes: ForceNode[]; edges: ForceEdge[] } {
  const nodes: ForceNode[] = [
    { id: 'p0', name: from, type: '案例', relationCount: 3 },
    { id: 'p1', name: '合同法', type: '法规', relationCount: 5 },
    { id: 'p2', name: '民法典', type: '法规', relationCount: 8 },
    { id: 'p3', name: to, type: '当事人', relationCount: 2 },
  ]
  const edges: ForceEdge[] = [
    { source: 'p0', target: 'p1', label: '适用' },
    { source: 'p1', target: 'p2', label: '引用' },
    { source: 'p2', target: 'p3', label: '关联' },
  ]
  return { nodes, edges }
}

// @mock-data FALLBACK
function generateMockEntityDetail(name: string, type: string): EntityDetail {
  return {
    name,
    type,
    properties: {
      '编号': `ID-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
      '状态': '有效',
      '创建时间': '2024-06-15',
      '更新时间': '2025-01-20',
      '来源': '司法数据库',
    },
    outEdges: [
      { target: '民法典', label: '适用' },
      { target: '合同效力', label: '涉及' },
      { target: '违约责任', label: '判决' },
    ],
    inEdges: [
      { source: '北京高院', label: '审理' },
      { source: '张某', label: '起诉' },
    ],
    documents: [
      { id: 'd1', title: '判决书全文' },
      { id: 'd2', title: '相关法规汇编' },
    ],
  }
}

// @mock-data FALLBACK
function generateMockTypes(): string[] {
  return ['法规', '案例', '当事人', '机构', '律师', '其他']
}

// ============================================================
// 工具函数
// ============================================================

function getNodeColor(type: string): string {
  return NODE_TYPE_COLORS[type] || '#6b7280'
}

function getNodeLabel(type: string): string {
  return NODE_TYPE_LABELS[type] || type
}

function convertApiData(data: GraphData): { nodes: ForceNode[]; edges: ForceEdge[] } {
  const edgeCountMap: Record<string, number> = {}
  data.edges.forEach((e) => {
    edgeCountMap[e.source] = (edgeCountMap[e.source] || 0) + 1
    edgeCountMap[e.target] = (edgeCountMap[e.target] || 0) + 1
  })
  const nodes: ForceNode[] = data.nodes.map((n) => ({
    id: n.id,
    name: n.label,
    type: n.type,
    relationCount: edgeCountMap[n.id] || 1,
  }))
  const edges: ForceEdge[] = data.edges.map((e) => ({
    source: e.source,
    target: e.target,
    label: e.relation || e.label || '',
  }))
  return { nodes, edges }
}

// ============================================================
// Hooks
// ============================================================

/** 防抖 Hook */
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

// ============================================================
// 子组件
// ============================================================

/** Skeleton 占位 */
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-muted rounded ${className}`} />
}

/** 类型 Badge */
function TypeBadge({ type, size = 'sm' }: { type: string; size?: 'sm' | 'md' }) {
  const color = getNodeColor(type)
  const label = getNodeLabel(type)
  const cls =
    size === 'sm'
      ? 'text-[10px] px-1.5 py-0.5 rounded'
      : 'text-xs px-2 py-0.5 rounded-md font-medium'
  return (
    <span
      className={cls}
      style={{ backgroundColor: color + '18', color, border: `1px solid ${color}40` }}
    >
      {label}
    </span>
  )
}

// ============================================================
// 左侧工具栏
// ============================================================

interface LeftPanelProps {
  searchQuery: string
  setSearchQuery: (v: string) => void
  searchResults: SearchResult[]
  searchLoading: boolean
  onSelectResult: (r: SearchResult) => void
  entityTypes: string[]
  activeTypes: Set<string>
  onToggleType: (t: string) => void
  pathFrom: string
  setPathFrom: (v: string) => void
  pathTo: string
  setPathTo: (v: string) => void
  onQueryPath: () => void
  pathLoading: boolean
  stats: GraphOverviewStats | null
  statsLoading: boolean
}

function LeftPanel({
  searchQuery,
  setSearchQuery,
  searchResults,
  searchLoading,
  onSelectResult,
  entityTypes,
  activeTypes,
  onToggleType,
  pathFrom,
  setPathFrom,
  pathTo,
  setPathTo,
  onQueryPath,
  pathLoading,
  stats,
  statsLoading,
}: LeftPanelProps) {
  const navigate = useNavigate()

  const pieData = useMemo(() => {
    if (!stats) return []
    return Object.entries(stats.node_types).map(([name, value]) => ({
      name: getNodeLabel(name),
      value,
      color: getNodeColor(name),
    }))
  }, [stats])

  return (
    <div className="hidden lg:flex w-64 border-r border-border flex-col h-full overflow-hidden shrink-0">
      {/* 搜索 */}
      <div className="p-4 border-b border-border space-y-3 shrink-0">
        <h3 className={heading.section}>搜索</h3>
        <div className="relative">
          <icons.Search className={`${iconSize.sm} absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground`} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索实体名称..."
            className={`${inputStyle.search} pl-8`}
          />
        </div>
        {searchLoading && (
          <div className="space-y-2">
            <Skeleton className="h-8 w-full" />
            <Skeleton className="h-8 w-full" />
          </div>
        )}
        {!searchLoading && searchResults.length > 0 && (
          <div className="max-h-40 overflow-y-auto space-y-1">
            {searchResults.map((r) => (
              <button
                key={r.id}
                onClick={() => onSelectResult(r)}
                className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-md hover:bg-muted transition-colors text-sm"
              >
                <div
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{ backgroundColor: getNodeColor(r.type) }}
                />
                <span className="truncate flex-1 text-foreground">{r.name}</span>
                <TypeBadge type={r.type} />
              </button>
            ))}
          </div>
        )}
        {!searchLoading && searchQuery.trim() && searchResults.length === 0 && (
          <p className="text-xs text-muted-foreground text-center py-2">无匹配结果</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {/* 类型过滤 */}
        <div className="p-4 border-b border-border space-y-2">
          <h3 className={heading.card}>实体类型</h3>
          <div className="space-y-1">
            {entityTypes.map((t) => (
              <label
                key={t}
                className="flex items-center gap-2 cursor-pointer text-sm py-0.5 hover:bg-muted/50 px-1 rounded"
              >
                <input
                  type="checkbox"
                  checked={activeTypes.has(t)}
                  onChange={() => onToggleType(t)}
                  className="rounded border-border accent-primary w-3.5 h-3.5"
                />
                <div
                  className="w-2.5 h-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: getNodeColor(t) }}
                />
                <span className="text-foreground">{getNodeLabel(t)}</span>
              </label>
            ))}
          </div>
        </div>

        {/* 路径查询 */}
        <div className="p-4 border-b border-border space-y-2">
          <h3 className={heading.card}>路径查询</h3>
          <input
            type="text"
            value={pathFrom}
            onChange={(e) => setPathFrom(e.target.value)}
            placeholder="从..."
            className={inputStyle.search}
          />
          <div className="flex items-center justify-center">
            <icons.ArrowRight className={`${iconSize.sm} text-muted-foreground`} />
          </div>
          <input
            type="text"
            value={pathTo}
            onChange={(e) => setPathTo(e.target.value)}
            placeholder="到..."
            className={inputStyle.search}
          />
          <button
            onClick={onQueryPath}
            disabled={pathLoading || !pathFrom.trim() || !pathTo.trim()}
            className={`${buttonStyle.primary} w-full justify-center flex items-center gap-1.5`}
          >
            {pathLoading ? (
              <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
            ) : (
              <icons.Search className={iconSize.sm} />
            )}
            查询路径
          </button>
        </div>

        {/* 统计面板 */}
        <div className="p-4 border-b border-border space-y-3">
          <h3 className={heading.card}>图谱统计</h3>
          {statsLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : stats ? (
            <>
              <div className="grid grid-cols-2 gap-2">
                <div className={`${cardStyle.compact} text-center`}>
                  <p className="text-xs text-muted-foreground">节点</p>
                  <p className="text-lg font-bold text-foreground">
                    {stats.total_nodes.toLocaleString()}
                  </p>
                </div>
                <div className={`${cardStyle.compact} text-center`}>
                  <p className="text-xs text-muted-foreground">关系</p>
                  <p className="text-lg font-bold text-foreground">
                    {stats.total_edges.toLocaleString()}
                  </p>
                </div>
              </div>
              {pieData.length > 0 && (
                <div className="h-32">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={pieData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={25}
                        outerRadius={50}
                        paddingAngle={2}
                        strokeWidth={0}
                      >
                        {pieData.map((entry, idx) => (
                          <Cell key={idx} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          borderRadius: 8,
                          fontSize: 12,
                          border: '1px solid var(--border)',
                          background: 'var(--background)',
                        }}
                        formatter={(value: number, name: string) => [`${value}`, name]}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
              <div className="space-y-1">
                {pieData.map((d) => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: d.color }}
                      />
                      <span className="text-muted-foreground">{d.name}</span>
                    </div>
                    <span className="text-foreground font-medium">{d.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>

        {/* 快捷链接 */}
        <div className="p-4 space-y-2">
          <button
            onClick={() => navigate('/due-diligence')}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-primary hover:bg-primary/5 transition-colors border border-primary/20"
          >
            <icons.Search className={iconSize.sm} />
            <span>智能调查</span>
            <icons.ArrowRight className={`${iconSize.xs} ml-auto`} />
          </button>
          <button
            onClick={() => navigate('/knowledge-base')}
            className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:bg-muted/50 transition-colors border border-border"
          >
            <icons.BookOpen className={iconSize.sm} />
            <span>司法智库</span>
            <icons.ArrowRight className={`${iconSize.xs} ml-auto`} />
          </button>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// 主组件
// ============================================================

export default function KnowledgeGraph() {
  const navigate = useNavigate()
  // --- 数据状态 ---
  const [stats, setStats] = useState<GraphOverviewStats | null>(null)
  const [statsLoading, setStatsLoading] = useState(false)
  const [entityTypes, setEntityTypes] = useState<string[]>([])
  const [activeTypes, setActiveTypes] = useState<Set<string>>(new Set())

  const [graphNodes, setGraphNodes] = useState<ForceNode[]>([])
  const [graphEdges, setGraphEdges] = useState<ForceEdge[]>([])

  const [searchQuery, setSearchQuery] = useState('')
  const debouncedQuery = useDebounce(searchQuery, DEBOUNCE_MS)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchLoading, setSearchLoading] = useState(false)

  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [entityDetail, setEntityDetail] = useState<EntityDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const [pathFrom, setPathFrom] = useState('')
  const [pathTo, setPathTo] = useState('')
  const [pathLoading, setPathLoading] = useState(false)

  const [graphLoading, setGraphLoading] = useState(false)
  const [graphError, setGraphError] = useState<string | null>(null)

  // --- 视图控制 ---
  const [viewMode, setViewMode] = useState<'2d' | '3d'>('2d')
  const [showLabels, setShowLabels] = useState(true)
  const [autoRotate, setAutoRotate] = useState(false)
  const graphRef = useRef<any>(null)

  // --- 弹窗状态 ---
  const [showAddEntity, setShowAddEntity] = useState(false)
  const [showAddRelation, setShowAddRelation] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [showExport, setShowExport] = useState(false)
  const [showAIExtract, setShowAIExtract] = useState(false)

  // --- 添加实体表单 ---
  const [newEntityName, setNewEntityName] = useState('')
  const [newEntityType, setNewEntityType] = useState('Entity')
  const [newEntityProps, setNewEntityProps] = useState<{ key: string; value: string }[]>([])

  // --- 添加关系表单 ---
  const [newRelSubject, setNewRelSubject] = useState('')
  const [newRelPredicate, setNewRelPredicate] = useState('INVOLVED_IN')
  const [newRelObject, setNewRelObject] = useState('')

  // --- 导入/导出 ---
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importPreview, setImportPreview] = useState<{ subject: string; predicate: string; object: string }[]>([])
  const [exportLoading, setExportLoading] = useState(false)
  const [importLoading, setImportLoading] = useState(false)

  // --- AI 抽取 ---
  const [extractText, setExtractText] = useState('')
  const [extractLoading, setExtractLoading] = useState(false)
  const [extractResult, setExtractResult] = useState<{ entities: any[]; relations: any[] } | null>(null)

  // --- 初始化 ---
  useEffect(() => {
    loadStats()
    loadTypes()
    loadInitialDemoGraph()
  }, [])

  // --- 搜索防抖 ---
  useEffect(() => {
    if (!debouncedQuery.trim()) {
      setSearchResults([])
      return
    }
    handleSearch(debouncedQuery)
  }, [debouncedQuery])

  // --- 选中节点时加载详情 ---
  useEffect(() => {
    if (!selectedNodeId) {
      setEntityDetail(null)
      return
    }
    const node = graphNodes.find((n) => n.id === selectedNodeId)
    if (node) {
      loadEntityDetail(node.name, node.type)
    }
  }, [selectedNodeId])

  // ============================================================
  // API 调用
  // ============================================================

  /** 初始加载：尝试从 API 获取图谱，失败则加载 Mock 演示数据 */
  async function loadInitialDemoGraph() {
    try {
      const data = await knowledgeCenterApi.searchGraph('法', 1, 50)
      if (data && data.nodes && data.nodes.length > 0) {
        const { nodes: n, edges: e } = convertApiData(data)
        mergeGraph(n, e)
        return
      }
    } catch {
      // API 不可用，使用演示数据
    }
    // @mock-data FALLBACK — 构建一个丰富的法律知识图谱演示
    const demoNodes: ForceNode[] = [
      // 案例
      { id: 'demo_c1', name: '劳动合同纠纷案', type: '案例', relationCount: 6 },
      { id: 'demo_c2', name: '工伤赔偿案', type: '案例', relationCount: 4 },
      { id: 'demo_c3', name: '知识产权侵权案', type: '案例', relationCount: 5 },
      // 法规
      { id: 'demo_l1', name: '民法典', type: '法规', relationCount: 8 },
      { id: 'demo_l2', name: '劳动合同法', type: '法规', relationCount: 6 },
      { id: 'demo_l3', name: '劳动法', type: '法规', relationCount: 4 },
      { id: 'demo_l4', name: '工伤保险条例', type: '法规', relationCount: 3 },
      { id: 'demo_l5', name: '著作权法', type: '法规', relationCount: 3 },
      { id: 'demo_l6', name: '公司法', type: '法规', relationCount: 2 },
      // 当事人
      { id: 'demo_p1', name: '张三', type: '当事人', relationCount: 3 },
      { id: 'demo_p2', name: '李四', type: '当事人', relationCount: 3 },
      { id: 'demo_p3', name: '王五', type: '当事人', relationCount: 2 },
      { id: 'demo_p4', name: '某科技有限公司', type: '当事人', relationCount: 4 },
      // 机构
      { id: 'demo_o1', name: '北京市第一中级人民法院', type: '机构', relationCount: 4 },
      { id: 'demo_o2', name: '朝阳区劳动仲裁委员会', type: '机构', relationCount: 3 },
      // 律师
      { id: 'demo_a1', name: '陈律师', type: '律师', relationCount: 3 },
      { id: 'demo_a2', name: '刘律师', type: '律师', relationCount: 2 },
      // 其他
      { id: 'demo_x1', name: '经济补偿金', type: '其他', relationCount: 2 },
      { id: 'demo_x2', name: '违约责任', type: '其他', relationCount: 2 },
    ]
    const demoEdges: ForceEdge[] = [
      // 劳动合同纠纷案
      { source: 'demo_c1', target: 'demo_l2', label: '适用' },
      { source: 'demo_c1', target: 'demo_l3', label: '适用' },
      { source: 'demo_p1', target: 'demo_c1', label: '原告' },
      { source: 'demo_p4', target: 'demo_c1', label: '被告' },
      { source: 'demo_o1', target: 'demo_c1', label: '审理' },
      { source: 'demo_a1', target: 'demo_p1', label: '代理' },
      { source: 'demo_c1', target: 'demo_x1', label: '判决' },
      // 工伤赔偿案
      { source: 'demo_c2', target: 'demo_l4', label: '适用' },
      { source: 'demo_c2', target: 'demo_l3', label: '适用' },
      { source: 'demo_p2', target: 'demo_c2', label: '原告' },
      { source: 'demo_p4', target: 'demo_c2', label: '被告' },
      { source: 'demo_o2', target: 'demo_c2', label: '仲裁' },
      // 知识产权侵权案
      { source: 'demo_c3', target: 'demo_l5', label: '适用' },
      { source: 'demo_c3', target: 'demo_l1', label: '适用' },
      { source: 'demo_p3', target: 'demo_c3', label: '原告' },
      { source: 'demo_p4', target: 'demo_c3', label: '被告' },
      { source: 'demo_o1', target: 'demo_c3', label: '审理' },
      { source: 'demo_a2', target: 'demo_p3', label: '代理' },
      { source: 'demo_c3', target: 'demo_x2', label: '判决' },
      // 法规间引用
      { source: 'demo_l2', target: 'demo_l3', label: '引用' },
      { source: 'demo_l1', target: 'demo_l6', label: '引用' },
      { source: 'demo_l1', target: 'demo_l2', label: '引用' },
      { source: 'demo_l4', target: 'demo_l3', label: '依据' },
      // 公司关联
      { source: 'demo_p4', target: 'demo_l6', label: '适用' },
    ]
    setGraphNodes(demoNodes)
    setGraphEdges(demoEdges)
    toast.info('已加载演示数据，可搜索探索更多')
  }

  async function loadStats() {
    setStatsLoading(true)
    try {
      const data = await knowledgeCenterApi.getGraphOverview()
      setStats(data as unknown as GraphOverviewStats)
    } catch {
      // @mock-data FALLBACK
      setStats(MOCK_STATS)
    } finally {
      setStatsLoading(false)
    }
  }

  async function loadTypes() {
    try {
      const data = await knowledgeCenterApi.getEntityTypes()
      const types = Array.isArray(data)
        ? data.map((item: any) => item.type).filter(Boolean)
        : []
      if (types.length > 0) {
        setEntityTypes(types)
        setActiveTypes(new Set(types))
        return
      }
    } catch {
      // fallback
    }
    // @mock-data FALLBACK
    const types = generateMockTypes()
    setEntityTypes(types)
    setActiveTypes(new Set(types))
  }

  async function handleSearch(keyword: string) {
    setSearchLoading(true)
    try {
      const data = await knowledgeCenterApi.searchGraph(keyword, 1, 50)
      const results: SearchResult[] = (data.nodes || []).map((n: any) => ({
        id: n.id || n.name,
        name: n.name || n.label,
        type: n.type,
      }))
      setSearchResults(results)
      return
    } catch {
      // fallback
    }
    // @mock-data FALLBACK
    setSearchResults(generateMockSearchResults(keyword))
    setSearchLoading(false)
  }

  async function loadSubgraph(name: string, depth = 2) {
    setGraphLoading(true)
    setGraphError(null)
    try {
      const data = await knowledgeCenterApi.getSubgraph(name, depth, 100)
      const { nodes: n, edges: e } = convertApiData(data)
      mergeGraph(n, e)
      return
    } catch {
      // @mock-data FALLBACK
      const { nodes: n, edges: e } = generateMockSubgraph(name)
      mergeGraph(n, e)
    } finally {
      setGraphLoading(false)
    }
  }

  async function loadEntityDetail(name: string, type: string) {
    setDetailLoading(true)
    try {
      const data = await knowledgeCenterApi.getEntityDetail(name)
      setEntityDetail(data)
      return
    } catch {
      // fallback
    }
    // @mock-data FALLBACK
    setEntityDetail(generateMockEntityDetail(name, type))
    setDetailLoading(false)
  }

  async function handlePathQuery() {
    if (!pathFrom.trim() || !pathTo.trim()) return
    setPathLoading(true)
    setGraphError(null)
    try {
      const data = await knowledgeCenterApi.getShortestPath(pathFrom, pathTo)
      const { nodes: n, edges: e } = convertApiData({
        nodes: data.nodes || [],
        edges: (data.relationships || []).map((rel: any) => ({
          source: rel.source,
          target: rel.target,
          relation: rel.relation || rel.label || '',
          label: rel.label,
        })),
      })
      setGraphNodes(n)
      setGraphEdges(e)
      setSelectedNodeId(null)
      toast.success(`找到从 "${pathFrom}" 到 "${pathTo}" 的路径`)
      return
    } catch {
      // fallback
    }
    // @mock-data FALLBACK
    const { nodes: n, edges: e } = generateMockPath(pathFrom, pathTo)
    setGraphNodes(n)
    setGraphEdges(e)
    setSelectedNodeId(null)
    toast.success(`找到从 "${pathFrom}" 到 "${pathTo}" 的路径（演示数据）`)
    setPathLoading(false)
  }

  // ============================================================
  // 图数据合并
  // ============================================================

  function mergeGraph(newNodes: ForceNode[], newEdges: ForceEdge[]) {
    setGraphNodes((prev) => {
      const existing = new Map(prev.map((n) => [n.id, n]))
      for (const n of newNodes) {
        if (!existing.has(n.id)) {
          existing.set(n.id, n)
        }
      }
      return Array.from(existing.values())
    })
    setGraphEdges((prev) => {
      const existingKeys = new Set(prev.map((e) => `${e.source}-${e.target}-${e.label}`))
      const merged = [...prev]
      for (const e of newEdges) {
        const key = `${e.source}-${e.target}-${e.label}`
        if (!existingKeys.has(key)) {
          merged.push(e)
          existingKeys.add(key)
        }
      }
      return merged
    })
    // 确保新类型也被激活
    setActiveTypes((prev) => {
      const updated = new Set(prev)
      for (const n of newNodes) {
        updated.add(n.type)
      }
      return updated
    })
    setEntityTypes((prev) => {
      const set = new Set(prev)
      for (const n of newNodes) {
        set.add(n.type)
      }
      return Array.from(set)
    })
  }

  // ============================================================
  // 交互处理
  // ============================================================

  function handleSelectSearchResult(result: SearchResult) {
    loadSubgraph(result.name)
    // 尝试定位到节点
    const existing = graphNodes.find((n) => n.name === result.name)
    if (existing) {
      setSelectedNodeId(existing.id)
    }
  }

  function handleToggleType(type: string) {
    setActiveTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }

  function handleDoubleClickNode(id: string) {
    const node = graphNodes.find((n) => n.id === id)
    if (node) {
      loadSubgraph(node.name, 1)
      toast.info(`展开 "${node.name}" 的子图`)
    }
  }

  function handleClickRelation(name: string) {
    // 尝试选中已有节点
    const existing = graphNodes.find((n) => n.name === name)
    if (existing) {
      setSelectedNodeId(existing.id)
    } else {
      // 加载子图
      loadSubgraph(name, 1)
    }
  }

  function handleExpandInGraph() {
    if (entityDetail) {
      loadSubgraph(entityDetail.name, 2)
    }
  }

  function handleRetry() {
    setGraphError(null)
    if (graphNodes.length === 0) {
      loadStats()
    }
  }

  function handleQuickSearch(keyword: string) {
    setSearchQuery(keyword)
    loadSubgraph(keyword, 2)
  }

  // ============================================================
  // 管理操作：实体/关系 CRUD、导入导出、AI抽取
  // ============================================================

  async function handleCreateEntity() {
    if (!newEntityName.trim()) {
      toast.error('请输入实体名称')
      return
    }
    try {
      const properties: Record<string, any> = {}
      newEntityProps.forEach((p) => {
        if (p.key.trim()) properties[p.key.trim()] = p.value
      })
      await knowledgeCenterApi.createEntity({
        name: newEntityName.trim(),
        entity_type: newEntityType,
        properties,
      })
      toast.success(`实体 "${newEntityName}" 创建成功`)
      setShowAddEntity(false)
      setNewEntityName('')
      setNewEntityType('Entity')
      setNewEntityProps([])
      // 刷新图谱
      loadSubgraph(newEntityName.trim(), 1)
      loadStats()
    } catch (err: any) {
      toast.error(`创建实体失败: ${err?.message || '未知错误'}`)
    }
  }

  async function handleDeleteEntity(name: string) {
    if (!confirm(`确认删除实体 "${name}" 及其所有关系？此操作不可撤销。`)) return
    try {
      await knowledgeCenterApi.deleteEntity(name)
      toast.success(`实体 "${name}" 已删除`)
      // 从图谱中移除
      setGraphNodes((prev) => prev.filter((n) => n.name !== name))
      setGraphEdges((prev) => prev.filter((e) => e.source !== name && e.target !== name))
      setSelectedNodeId(null)
      setEntityDetail(null)
      loadStats()
    } catch (err: any) {
      toast.error(`删除失败: ${err?.message || '未知错误'}`)
    }
  }

  async function handleCreateRelation() {
    if (!newRelSubject.trim() || !newRelObject.trim()) {
      toast.error('请输入主体和客体名称')
      return
    }
    try {
      await knowledgeCenterApi.createRelation({
        subject: newRelSubject.trim(),
        predicate: newRelPredicate,
        object: newRelObject.trim(),
      })
      toast.success('关系创建成功')
      setShowAddRelation(false)
      setNewRelSubject('')
      setNewRelPredicate('INVOLVED_IN')
      setNewRelObject('')
      // 刷新
      loadSubgraph(newRelSubject.trim(), 1)
      loadStats()
    } catch (err: any) {
      toast.error(`创建关系失败: ${err?.message || '未知错误'}`)
    }
  }

  async function handleExportGraph() {
    setExportLoading(true)
    try {
      const data = await knowledgeCenterApi.exportGraph()
      // 将三元组数据转为 CSV
      const triples = data.triples || []
      const header = 'subject,predicate,object'
      const rows = triples.map((t: any) => `"${t.subject || t[0]}","${t.predicate || t[1]}","${t.object || t[2]}"`)
      const csv = [header, ...rows].join('\n')
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `knowledge_graph_export_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
      toast.success(`导出成功，共 ${triples.length} 条三元组`)
    } catch (err: any) {
      toast.error(`导出失败: ${err?.message || '未知错误'}`)
    } finally {
      setExportLoading(false)
    }
  }

  function handleImportFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setImportFile(file)
    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target?.result as string
      const lines = text.split('\n').filter((l) => l.trim())
      // 跳过表头
      const dataLines = lines[0]?.toLowerCase().includes('subject') ? lines.slice(1) : lines
      const parsed = dataLines.map((line) => {
        // 支持带引号和不带引号的CSV
        const match = line.match(/^"?([^",]*)"?,\s*"?([^",]*)"?,\s*"?([^",]*)"?$/)
        if (match) return { subject: match[1], predicate: match[2], object: match[3] }
        const parts = line.split(',').map((s) => s.trim().replace(/^"|"$/g, ''))
        return { subject: parts[0] || '', predicate: parts[1] || '', object: parts[2] || '' }
      }).filter((t) => t.subject && t.predicate && t.object)
      setImportPreview(parsed)
    }
    reader.readAsText(file)
  }

  async function handleImportConfirm() {
    if (importPreview.length === 0) {
      toast.error('没有可导入的数据')
      return
    }
    setImportLoading(true)
    let successCount = 0
    let failCount = 0
    try {
      for (const triple of importPreview) {
        try {
          await knowledgeCenterApi.createRelation({
            subject: triple.subject,
            predicate: triple.predicate,
            object: triple.object,
          })
          successCount++
        } catch {
          failCount++
        }
      }
      toast.success(`导入完成：成功 ${successCount} 条${failCount > 0 ? `，失败 ${failCount} 条` : ''}`)
      setShowImport(false)
      setImportFile(null)
      setImportPreview([])
      loadStats()
    } catch (err: any) {
      toast.error(`导入失败: ${err?.message || '未知错误'}`)
    } finally {
      setImportLoading(false)
    }
  }

  async function handleAIExtract() {
    if (!extractText.trim()) {
      toast.error('请输入要抽取的文本')
      return
    }
    setExtractLoading(true)
    setExtractResult(null)
    try {
      const result = await knowledgeCenterApi.extractEntities(extractText, false)
      setExtractResult({ entities: result.entities || [], relations: result.relations || [] })
      toast.success(`抽取完成：${result.entities?.length || 0} 个实体，${result.relations?.length || 0} 条关系`)
    } catch (err: any) {
      toast.error(`AI抽取失败: ${err?.message || '未知错误'}`)
    } finally {
      setExtractLoading(false)
    }
  }

  async function handleAIExtractImport() {
    if (!extractText.trim()) return
    setExtractLoading(true)
    try {
      const result = await knowledgeCenterApi.extractEntities(extractText, true)
      toast.success(
        `已导入 ${result.imported_entities || 0} 个实体，${result.imported_relations || 0} 条关系`
      )
      setShowAIExtract(false)
      setExtractText('')
      setExtractResult(null)
      loadStats()
    } catch (err: any) {
      toast.error(`导入失败: ${err?.message || '未知错误'}`)
    } finally {
      setExtractLoading(false)
    }
  }

  // ============================================================
  // 快捷搜索标签
  // ============================================================

  const quickTags = ['合同法', '知识产权', '劳动争议', '民法典', '公司法', '刑法']

  // ============================================================
  // 渲染
  // ============================================================

  return (
    <div className="h-full flex flex-col">
      {/* 图谱全屏画布 */}
      <div className="flex-1 relative min-h-0">
          {/* 加载覆盖层 */}
          {graphLoading && (
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm z-30 flex items-center justify-center">
              <div className="flex items-center gap-3 bg-background border border-border rounded-xl px-5 py-3 shadow-lg">
                <icons.Loader2 className={`${iconSize.md} animate-spin text-primary`} />
                <span className="text-sm text-foreground">加载图谱数据...</span>
              </div>
            </div>
          )}

          {/* ====== 浮动搜索栏 (顶部居中) ====== */}
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 w-full max-w-xl px-4">
            <div className="flex items-center gap-2 bg-background/90 backdrop-blur-md border border-border rounded-xl shadow-lg px-3 py-2">
              <icons.Search className="w-4 h-4 text-muted-foreground shrink-0" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="搜索实体：法律法规、案件、企业、当事人..."
                className="flex-1 bg-transparent border-none text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="p-0.5 rounded text-muted-foreground hover:text-foreground">
                  <icons.X className="w-3.5 h-3.5" />
                </button>
              )}
              {/* 操作按钮 */}
              <div className="flex items-center gap-0.5 border-l border-border pl-2 ml-1">
                <button onClick={() => setShowAddEntity(true)} className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors" title="添加实体">
                  <icons.Plus className="w-4 h-4" />
                </button>
                <button onClick={() => setShowAddRelation(true)} className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors" title="添加关系">
                  <icons.Link className="w-4 h-4" />
                </button>
                <button onClick={() => setShowImport(true)} className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors" title="导入">
                  <icons.Upload className="w-4 h-4" />
                </button>
                <button onClick={() => setShowExport(true)} className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors" title="导出">
                  <icons.Download className="w-4 h-4" />
                </button>
                <button onClick={() => setShowAIExtract(true)} className="p-1.5 rounded-lg text-muted-foreground hover:text-primary hover:bg-primary/5 transition-colors" title="AI 智能抽取">
                  <icons.Sparkles className="w-4 h-4" />
                </button>
                {graphNodes.length > 0 && (
                  <button onClick={() => { setGraphNodes([]); setGraphEdges([]); setSelectedNodeId(null); setEntityDetail(null) }}
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/20 transition-colors" title="清除图谱">
                    <icons.Trash2 className="w-4 h-4" />
                  </button>
                )}
              </div>
            </div>
            {/* 搜索结果下拉 */}
            {(searchLoading || (searchResults.length > 0 && searchQuery.trim())) && (
              <div className="mt-1.5 bg-background/95 backdrop-blur-md border border-border rounded-xl shadow-lg overflow-hidden max-h-60 overflow-y-auto">
                {searchLoading ? (
                  <div className="p-3 flex items-center gap-2 text-xs text-muted-foreground">
                    <icons.Loader2 className="w-3.5 h-3.5 animate-spin" /> 搜索中...
                  </div>
                ) : (
                  searchResults.map((r) => (
                    <button
                      key={r.id}
                      onClick={() => { handleSelectSearchResult(r); setSearchQuery('') }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-muted/50 transition-colors text-left border-b border-border/50 last:border-b-0"
                    >
                      <div className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: getNodeColor(r.type) }} />
                      <span className="truncate flex-1 text-foreground">{r.name}</span>
                      <TypeBadge type={r.type} />
                    </button>
                  ))
                )}
                {!searchLoading && searchQuery.trim() && searchResults.length === 0 && (
                  <div className="p-3 text-xs text-muted-foreground text-center">无匹配结果</div>
                )}
              </div>
            )}
          </div>

          {/* 错误状态 */}
          {graphError ? (
            <div className="flex-1 h-full flex items-center justify-center">
              <div className="text-center">
                <icons.AlertCircle className={`${iconSize.xl} mx-auto mb-3 text-destructive`} />
                <p className="text-sm text-foreground mb-3">{graphError}</p>
                <button onClick={handleRetry} className={buttonStyle.primary}>
                  重试
                </button>
              </div>
            </div>
          ) : graphNodes.length === 0 ? (
            /* 空状态 */
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md px-6">
                <icons.Network className="w-16 h-16 mx-auto mb-5 text-muted-foreground/20" />
                <h3 className="text-lg font-semibold text-foreground mb-2">探索知识图谱</h3>
                <p className="text-sm text-muted-foreground mb-6">
                  输入关键词搜索，可视化法规、案件、主体间的关系网络
                </p>
                {/* 快捷搜索标签 */}
                <div className="flex flex-wrap justify-center gap-2 mb-6">
                  {quickTags.map((tag) => (
                    <button
                      key={tag}
                      onClick={() => handleQuickSearch(tag)}
                      className="px-3 py-1.5 rounded-full text-xs font-medium bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary transition-colors border border-transparent hover:border-primary/20"
                    >
                      {tag}
                    </button>
                  ))}
                </div>
                {/* 统计摘要 */}
                {stats && (
                  <div className="flex items-center justify-center gap-6 text-xs text-muted-foreground">
                    <span>
                      <span className="text-foreground font-semibold">{stats.total_nodes.toLocaleString()}</span> 个节点
                    </span>
                    <span>
                      <span className="text-foreground font-semibold">{stats.total_edges.toLocaleString()}</span> 条关系
                    </span>
                    <span>
                      <span className="text-foreground font-semibold">{Object.keys(stats.node_types).length}</span> 种类型
                    </span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* 图谱画布 + 浮动控件 */
            <>
              <ForceGraphCanvas
                nodes={graphNodes as ForceGraphNode[]}
                edges={graphEdges as ForceGraphEdge[]}
                activeTypes={activeTypes}
                selectedNodeId={selectedNodeId}
                onSelectNode={setSelectedNodeId}
                onDoubleClickNode={handleDoubleClickNode}
                viewMode={viewMode}
                showLabels={showLabels}
              />

              {/* 浮动工具栏 */}
              <div className="absolute top-4 left-4 z-10">
                <GraphToolbar
                  viewMode={viewMode}
                  onViewModeChange={setViewMode}
                  showLabels={showLabels}
                  onToggleLabels={() => setShowLabels((v) => !v)}
                  autoRotate={autoRotate}
                  onToggleAutoRotate={() => setAutoRotate((v) => !v)}
                  onResetView={() => {
                    // GraphCanvas handles this internally via ref if needed
                  }}
                  onZoomToFit={() => {
                    // GraphCanvas handles this internally via ref if needed
                  }}
                />
              </div>

              {/* 浮动图例 */}
              <div className="absolute bottom-4 left-4 z-10">
                <GraphLegend
                  nodeCount={graphNodes.length}
                  edgeCount={graphEdges.length}
                  viewMode={viewMode}
                />
              </div>

              {/* 节点数量警告 */}
              {graphNodes.length > MAX_VISIBLE_NODES && (
                <div className="absolute top-4 right-4 z-10 bg-amber-500/10 border border-amber-500/30 text-amber-600 rounded-lg px-3 py-2 text-xs flex items-center gap-2">
                  <icons.AlertTriangle className={iconSize.sm} />
                  节点数量较多（{graphNodes.length}），建议使用过滤器
                </div>
              )}
            </>
          )}

          {/* 详情抽屉 */}
          <GraphDetailDrawer
            detail={entityDetail}
            loading={detailLoading}
            onClose={() => {
              setSelectedNodeId(null)
              setEntityDetail(null)
            }}
            onClickRelation={handleClickRelation}
            onExpandInGraph={handleExpandInGraph}
            onEditEntity={() => {
              if (entityDetail) {
                setNewEntityName(entityDetail.name)
                setNewEntityType(entityDetail.type || 'Entity')
                setNewEntityProps(
                  entityDetail.properties
                    ? Object.entries(entityDetail.properties).map(([key, value]) => ({ key, value }))
                    : []
                )
                setShowAddEntity(true)
              }
            }}
            onInvestigate={(entityName) => {
              navigate(`/due-diligence?company=${encodeURIComponent(entityName)}`)
            }}
            onDeleteEntity={() => {
              if (entityDetail) {
                handleDeleteEntity(entityDetail.name)
              }
            }}
          />
        </div>

      {/* ============================================================ */}
      {/* 弹窗：添加实体 */}
      {/* ============================================================ */}
      {showAddEntity && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-md mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className={heading.section}>添加实体</h3>
              <button onClick={() => setShowAddEntity(false)} className={buttonStyle.icon}>
                <icons.X className={iconSize.sm} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              {/* 名称 */}
              <div>
                <label className="text-xs font-medium text-foreground mb-1.5 block">
                  名称 <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={newEntityName}
                  onChange={(e) => setNewEntityName(e.target.value)}
                  placeholder="输入实体名称"
                  className={`${inputStyle.search} w-full`}
                />
              </div>
              {/* 类型 */}
              <div>
                <label className="text-xs font-medium text-foreground mb-1.5 block">类型</label>
                <select
                  value={newEntityType}
                  onChange={(e) => setNewEntityType(e.target.value)}
                  className={`${inputStyle.search} w-full`}
                >
                  {['Entity', 'Person', 'Court', 'Law', 'Company', 'Case', 'Provision'].map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
              </div>
              {/* 属性 */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="text-xs font-medium text-foreground">属性</label>
                  <button
                    onClick={() => setNewEntityProps((prev) => [...prev, { key: '', value: '' }])}
                    className={`${buttonStyle.ghost} text-xs`}
                  >
                    <icons.Plus className={iconSize.xs} />
                    添加
                  </button>
                </div>
                {newEntityProps.map((prop, idx) => (
                  <div key={idx} className="flex gap-2 mb-2">
                    <input
                      type="text"
                      value={prop.key}
                      onChange={(e) => {
                        const updated = [...newEntityProps]
                        updated[idx].key = e.target.value
                        setNewEntityProps(updated)
                      }}
                      placeholder="属性名"
                      className={`${inputStyle.search} flex-1`}
                    />
                    <input
                      type="text"
                      value={prop.value}
                      onChange={(e) => {
                        const updated = [...newEntityProps]
                        updated[idx].value = e.target.value
                        setNewEntityProps(updated)
                      }}
                      placeholder="属性值"
                      className={`${inputStyle.search} flex-1`}
                    />
                    <button
                      onClick={() => setNewEntityProps((prev) => prev.filter((_, i) => i !== idx))}
                      className={buttonStyle.icon}
                    >
                      <icons.X className={iconSize.xs} />
                    </button>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 p-5 border-t border-border">
              <button onClick={() => setShowAddEntity(false)} className={buttonStyle.secondary}>
                取消
              </button>
              <button onClick={handleCreateEntity} className={buttonStyle.primary}>
                创建实体
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 弹窗：添加关系 */}
      {/* ============================================================ */}
      {showAddRelation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className={heading.section}>添加关系</h3>
              <button onClick={() => setShowAddRelation(false)} className={buttonStyle.icon}>
                <icons.X className={iconSize.sm} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-foreground mb-1.5 block">
                  主体名称 <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={newRelSubject}
                  onChange={(e) => setNewRelSubject(e.target.value)}
                  placeholder="输入主体实体名称"
                  className={`${inputStyle.search} w-full`}
                />
              </div>
              <div>
                <label className="text-xs font-medium text-foreground mb-1.5 block">关系类型</label>
                <select
                  value={newRelPredicate}
                  onChange={(e) => setNewRelPredicate(e.target.value)}
                  className={`${inputStyle.search} w-full`}
                >
                  {[
                    'INVOLVED_IN', 'HEARD_BY', 'REFERENCES', 'REPRESENTS',
                    'APPLIES_TO', 'RELATED_TO', 'CITES', 'AMENDS',
                    'REPEALS', 'SUPPLEMENTS', 'CONTRADICTS',
                  ].map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-foreground mb-1.5 block">
                  客体名称 <span className="text-destructive">*</span>
                </label>
                <input
                  type="text"
                  value={newRelObject}
                  onChange={(e) => setNewRelObject(e.target.value)}
                  placeholder="输入客体实体名称"
                  className={`${inputStyle.search} w-full`}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 p-5 border-t border-border">
              <button onClick={() => setShowAddRelation(false)} className={buttonStyle.secondary}>
                取消
              </button>
              <button onClick={handleCreateRelation} className={buttonStyle.primary}>
                创建关系
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 弹窗：导入 */}
      {/* ============================================================ */}
      {showImport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className={heading.section}>导入三元组</h3>
              <button onClick={() => { setShowImport(false); setImportFile(null); setImportPreview([]) }} className={buttonStyle.icon}>
                <icons.X className={iconSize.sm} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-xs text-muted-foreground">
                上传 CSV 文件，格式：subject, predicate, object（每行一条三元组）
              </p>
              <input
                type="file"
                accept=".csv,.txt"
                onChange={handleImportFileChange}
                className="block w-full text-xs text-muted-foreground file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-border file:text-xs file:font-medium file:bg-muted file:text-foreground hover:file:bg-muted/80 file:cursor-pointer"
              />
              {importFile && importPreview.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs text-foreground font-medium mb-2">
                    预览（共 {importPreview.length} 条三元组）
                  </p>
                  <div className="border border-border rounded-lg overflow-hidden max-h-48 overflow-y-auto">
                    <table className="w-full text-[11px]">
                      <thead>
                        <tr className="bg-muted/50">
                          <th className="px-2 py-1 text-left text-muted-foreground font-medium">主体</th>
                          <th className="px-2 py-1 text-left text-muted-foreground font-medium">关系</th>
                          <th className="px-2 py-1 text-left text-muted-foreground font-medium">客体</th>
                        </tr>
                      </thead>
                      <tbody>
                        {importPreview.slice(0, 20).map((t, i) => (
                          <tr key={i} className="border-t border-border">
                            <td className="px-2 py-1 text-foreground">{t.subject}</td>
                            <td className="px-2 py-1 text-primary">{t.predicate}</td>
                            <td className="px-2 py-1 text-foreground">{t.object}</td>
                          </tr>
                        ))}
                        {importPreview.length > 20 && (
                          <tr className="border-t border-border">
                            <td colSpan={3} className="px-2 py-1 text-center text-muted-foreground">
                              ... 还有 {importPreview.length - 20} 条
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                  <button
                    onClick={handleImportConfirm}
                    disabled={importLoading}
                    className={`${buttonStyle.primary} mt-3 flex items-center gap-1.5`}
                  >
                    {importLoading ? (
                      <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                    ) : (
                      <icons.Upload className={iconSize.sm} />
                    )}
                    {importLoading ? '导入中...' : `确认导入 ${importPreview.length} 条`}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 弹窗：导出 */}
      {/* ============================================================ */}
      {showExport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-md mx-4">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className={heading.section}>导出图谱</h3>
              <button onClick={() => setShowExport(false)} className={buttonStyle.icon}>
                <icons.X className={iconSize.sm} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <p className="text-xs text-muted-foreground">
                将当前知识图谱中所有三元组导出为 CSV 文件（subject, predicate, object 格式）
              </p>
              <button
                onClick={handleExportGraph}
                disabled={exportLoading}
                className={`${buttonStyle.primary} flex items-center gap-1.5`}
              >
                {exportLoading ? (
                  <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                ) : (
                  <icons.Download className={iconSize.sm} />
                )}
                {exportLoading ? '导出中...' : '导出 CSV'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/* 弹窗：AI 实体抽取 */}
      {/* ============================================================ */}
      {showAIExtract && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className={heading.section}>AI 实体抽取</h3>
              <button onClick={() => { setShowAIExtract(false); setExtractText(''); setExtractResult(null) }} className={buttonStyle.icon}>
                <icons.X className={iconSize.sm} />
              </button>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="text-xs font-medium text-foreground mb-1.5 block">
                  输入文本
                </label>
                <textarea
                  value={extractText}
                  onChange={(e) => setExtractText(e.target.value)}
                  placeholder="粘贴法律文本，AI 将自动抽取实体和关系..."
                  rows={6}
                  className={`${inputStyle.search} w-full resize-none`}
                />
                <p className="text-[10px] text-muted-foreground mt-1">
                  支持合同文本、裁判文书、法规条文等
                </p>
              </div>

              <button
                onClick={handleAIExtract}
                disabled={extractLoading || !extractText.trim()}
                className={`${buttonStyle.primary} flex items-center gap-1.5`}
              >
                {extractLoading ? (
                  <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                ) : (
                  <icons.Sparkles className={iconSize.sm} />
                )}
                {extractLoading ? '抽取中...' : '开始抽取'}
              </button>

              {/* 抽取结果预览 */}
              {extractResult && (
                <div className="space-y-3">
                  <div className="border-t border-border pt-3" />

                  {/* 实体列表 */}
                  {extractResult.entities.length > 0 && (
                    <div>
                      <h4 className={`${heading.card} mb-2`}>
                        抽取到的实体
                        <span className="text-muted-foreground font-normal ml-1">
                          ({extractResult.entities.length})
                        </span>
                      </h4>
                      <div className="flex flex-wrap gap-1.5">
                        {extractResult.entities.map((ent: any, i: number) => (
                          <span
                            key={i}
                            className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-muted text-xs text-foreground"
                          >
                            <span
                              className="w-1.5 h-1.5 rounded-full"
                              style={{ backgroundColor: getNodeColor(ent.type || ent.entity_type || '') }}
                            />
                            {ent.name || ent.label}
                            <span className="text-[10px] text-muted-foreground">
                              {ent.type || ent.entity_type || ''}
                            </span>
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 关系列表 */}
                  {extractResult.relations.length > 0 && (
                    <div>
                      <h4 className={`${heading.card} mb-2`}>
                        抽取到的关系
                        <span className="text-muted-foreground font-normal ml-1">
                          ({extractResult.relations.length})
                        </span>
                      </h4>
                      <div className="border border-border rounded-lg overflow-hidden max-h-40 overflow-y-auto">
                        <table className="w-full text-[11px]">
                          <tbody>
                            {extractResult.relations.map((rel: any, i: number) => (
                              <tr key={i} className="border-b border-border last:border-b-0">
                                <td className="px-2 py-1 text-foreground">{rel.subject || rel.source}</td>
                                <td className="px-2 py-1 text-primary font-medium">{rel.predicate || rel.relation}</td>
                                <td className="px-2 py-1 text-foreground">{rel.object || rel.target}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 导入按钮 */}
                  <button
                    onClick={handleAIExtractImport}
                    disabled={extractLoading}
                    className={`${buttonStyle.primary} w-full justify-center flex items-center gap-1.5`}
                  >
                    {extractLoading ? (
                      <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                    ) : (
                      <icons.Upload className={iconSize.sm} />
                    )}
                    {extractLoading ? '导入中...' : '确认导入到图谱'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
