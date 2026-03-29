// -*- coding: utf-8 -*-
/**
 * KnowledgeGraph.tsx - 商业级交互式知识图谱页面
 *
 * 功能：
 * - SVG 力导向图可视化（原生实现，无 d3 依赖）
 * - 节点拖拽、缩放、平移
 * - 搜索、过滤、路径查询
 * - 实体详情面板
 * - 统计面板（recharts PieChart）
 */

import {
  useState,
  useEffect,
  useCallback,
  useRef,
  useMemo,
  type ReactNode,
  type MouseEvent as ReactMouseEvent,
} from 'react'
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

// ============================================================
// 类型定义
// ============================================================

interface ForceNode {
  id: string
  name: string
  type: string
  x: number
  y: number
  vx: number
  vy: number
  relationCount: number
  fixed?: boolean
  properties?: Record<string, string>
}

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
  const types = ['法规', '案例', '当事人', '机构', '律师']
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
    id: 'c0', name: centerName, type: '案例',
    x: 0, y: 0, vx: 0, vy: 0, relationCount: 7,
  }
  const satellites: ForceNode[] = [
    { id: 's1', name: '民法典', type: '法规', x: 0, y: 0, vx: 0, vy: 0, relationCount: 5 },
    { id: 's2', name: '合同法', type: '法规', x: 0, y: 0, vx: 0, vy: 0, relationCount: 4 },
    { id: 's3', name: '张某', type: '当事人', x: 0, y: 0, vx: 0, vy: 0, relationCount: 3 },
    { id: 's4', name: '李某', type: '当事人', x: 0, y: 0, vx: 0, vy: 0, relationCount: 2 },
    { id: 's5', name: '北京市高级人民法院', type: '机构', x: 0, y: 0, vx: 0, vy: 0, relationCount: 6 },
    { id: 's6', name: '王律师', type: '律师', x: 0, y: 0, vx: 0, vy: 0, relationCount: 3 },
    { id: 's7', name: '侵权责任法', type: '法规', x: 0, y: 0, vx: 0, vy: 0, relationCount: 4 },
    { id: 's8', name: '合同效力争议', type: '案例', x: 0, y: 0, vx: 0, vy: 0, relationCount: 2 },
    { id: 's9', name: '刘律师', type: '律师', x: 0, y: 0, vx: 0, vy: 0, relationCount: 1 },
    { id: 's10', name: '赵某', type: '当事人', x: 0, y: 0, vx: 0, vy: 0, relationCount: 2 },
    { id: 's11', name: '损害赔偿', type: '其他', x: 0, y: 0, vx: 0, vy: 0, relationCount: 3 },
    { id: 's12', name: '违约金', type: '其他', x: 0, y: 0, vx: 0, vy: 0, relationCount: 2 },
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
    { id: 'p0', name: from, type: '案例', x: 0, y: 0, vx: 0, vy: 0, relationCount: 3 },
    { id: 'p1', name: '合同法', type: '法规', x: 0, y: 0, vx: 0, vy: 0, relationCount: 5 },
    { id: 'p2', name: '民法典', type: '法规', x: 0, y: 0, vx: 0, vy: 0, relationCount: 8 },
    { id: 'p3', name: to, type: '当事人', x: 0, y: 0, vx: 0, vy: 0, relationCount: 2 },
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

function getNodeRadius(relationCount: number): number {
  return Math.min(Math.max(relationCount * 3 + 14, 20), 50) / 2
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
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
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

/** 力导向布局 Hook */
function useForceLayout(
  inputNodes: ForceNode[],
  inputEdges: ForceEdge[],
  width: number,
  height: number
) {
  const nodesRef = useRef<ForceNode[]>([])
  const edgesRef = useRef<ForceEdge[]>([])
  const rafRef = useRef<number>(0)
  const tickRef = useRef(0)
  const [renderTick, setRenderTick] = useState(0)
  const alphaRef = useRef(1)
  const stableRef = useRef(false)

  // 初始化节点位置
  useEffect(() => {
    if (inputNodes.length === 0) {
      nodesRef.current = []
      edgesRef.current = []
      stableRef.current = true
      setRenderTick((t) => t + 1)
      return
    }

    const cx = width / 2
    const cy = height / 2
    const radius = Math.min(width, height) * 0.35

    const initialized = inputNodes.map((n, i) => {
      const angle = (2 * Math.PI * i) / inputNodes.length
      return {
        ...n,
        x: n.x !== 0 ? n.x : cx + radius * Math.cos(angle) + (Math.random() - 0.5) * 30,
        y: n.y !== 0 ? n.y : cy + radius * Math.sin(angle) + (Math.random() - 0.5) * 30,
        vx: 0,
        vy: 0,
      }
    })

    nodesRef.current = initialized
    edgesRef.current = inputEdges
    alphaRef.current = 1
    stableRef.current = false
    tickRef.current = 0
  }, [inputNodes, inputEdges, width, height])

  // 力计算循环
  useEffect(() => {
    if (stableRef.current || nodesRef.current.length === 0) return

    const simulate = () => {
      const nodes = nodesRef.current
      const edges = edgesRef.current
      const alpha = alphaRef.current

      if (alpha < 0.005 || tickRef.current > 300) {
        stableRef.current = true
        setRenderTick((t) => t + 1)
        return
      }

      const n = nodes.length
      const cx = width / 2
      const cy = height / 2

      // 库仑排斥力
      const repulsionStrength = 800
      for (let i = 0; i < n; i++) {
        for (let j = i + 1; j < n; j++) {
          const dx = nodes[j].x - nodes[i].x
          const dy = nodes[j].y - nodes[i].y
          let dist = Math.sqrt(dx * dx + dy * dy) || 1
          if (dist < 1) dist = 1
          const force = (repulsionStrength * alpha) / (dist * dist)
          const fx = (dx / dist) * force
          const fy = (dy / dist) * force
          if (!nodes[i].fixed) {
            nodes[i].vx -= fx
            nodes[i].vy -= fy
          }
          if (!nodes[j].fixed) {
            nodes[j].vx += fx
            nodes[j].vy += fy
          }
        }
      }

      // 弹簧吸引力
      const springStrength = 0.05
      const idealLength = 120
      const nodeMap = new Map(nodes.map((nd) => [nd.id, nd]))
      for (const edge of edges) {
        const s = nodeMap.get(edge.source)
        const t = nodeMap.get(edge.target)
        if (!s || !t) continue
        const dx = t.x - s.x
        const dy = t.y - s.y
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const displacement = dist - idealLength
        const force = springStrength * displacement * alpha
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        if (!s.fixed) {
          s.vx += fx
          s.vy += fy
        }
        if (!t.fixed) {
          t.vx -= fx
          t.vy -= fy
        }
      }

      // 中心引力
      const centerStrength = 0.01
      for (const node of nodes) {
        if (node.fixed) continue
        node.vx += (cx - node.x) * centerStrength * alpha
        node.vy += (cy - node.y) * centerStrength * alpha
      }

      // 速度衰减 + 位置更新
      const damping = 0.6
      for (const node of nodes) {
        if (node.fixed) continue
        node.vx *= damping
        node.vy *= damping
        node.x += node.vx
        node.y += node.vy
        // 边界约束
        const r = getNodeRadius(node.relationCount)
        node.x = Math.max(r, Math.min(width - r, node.x))
        node.y = Math.max(r, Math.min(height - r, node.y))
      }

      alphaRef.current *= 0.99
      tickRef.current++

      // 每 3 帧触发一次渲染
      if (tickRef.current % 3 === 0) {
        setRenderTick((t) => t + 1)
      }

      rafRef.current = requestAnimationFrame(simulate)
    }

    rafRef.current = requestAnimationFrame(simulate)
    return () => cancelAnimationFrame(rafRef.current)
  }, [inputNodes, inputEdges, width, height])

  const setNodePosition = useCallback((id: string, x: number, y: number, fixed: boolean) => {
    const node = nodesRef.current.find((n) => n.id === id)
    if (node) {
      node.x = x
      node.y = y
      node.vx = 0
      node.vy = 0
      node.fixed = fixed
      if (!fixed) {
        alphaRef.current = 0.3
        stableRef.current = false
      }
      setRenderTick((t) => t + 1)
    }
  }, [])

  const reheat = useCallback(() => {
    alphaRef.current = 0.5
    stableRef.current = false
    tickRef.current = 0
  }, [])

  return {
    nodes: nodesRef.current,
    edges: edgesRef.current,
    renderTick,
    setNodePosition,
    reheat,
  }
}

// ============================================================
// 子组件
// ============================================================

/** Skeleton 占位 */
function Skeleton({ className = '' }: { className?: string }) {
  return <div className={`animate-pulse bg-muted rounded ${className}`} />
}

/** 空状态 */
function EmptyState({ message, icon }: { message: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
      {icon || <icons.Search className={`${iconSize.xl} mb-3 opacity-30`} />}
      <p className="text-sm">{message}</p>
    </div>
  )
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
  const pieData = useMemo(() => {
    if (!stats) return []
    return Object.entries(stats.node_types).map(([name, value]) => ({
      name: getNodeLabel(name),
      value,
      color: getNodeColor(name),
    }))
  }, [stats])

  return (
    <div className="w-64 border-r border-border flex flex-col h-full overflow-hidden shrink-0 hidden lg:flex">
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
        <div className="p-4 space-y-3">
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
      </div>
    </div>
  )
}

// ============================================================
// 中间 SVG 图谱
// ============================================================

interface GraphCanvasProps {
  nodes: ForceNode[]
  edges: ForceEdge[]
  activeTypes: Set<string>
  selectedNodeId: string | null
  hoveredNodeId: string | null
  onSelectNode: (id: string | null) => void
  onHoverNode: (id: string | null) => void
  onDoubleClickNode: (id: string) => void
  onDragStart: (id: string, e: ReactMouseEvent) => void
  zoom: number
  pan: { x: number; y: number }
  onWheel: (e: React.WheelEvent) => void
  onPanStart: (e: ReactMouseEvent) => void
  containerRef: React.RefObject<HTMLDivElement>
  width: number
  height: number
  tooManyNodes: boolean
}

function GraphCanvas({
  nodes,
  edges,
  activeTypes,
  selectedNodeId,
  hoveredNodeId,
  onSelectNode,
  onHoverNode,
  onDoubleClickNode,
  onDragStart,
  zoom,
  pan,
  onWheel,
  onPanStart,
  containerRef,
  width,
  height,
  tooManyNodes,
}: GraphCanvasProps) {
  const visibleNodes = useMemo(
    () => nodes.filter((n) => activeTypes.has(n.type)),
    [nodes, activeTypes]
  )
  const visibleNodeIds = useMemo(() => new Set(visibleNodes.map((n) => n.id)), [visibleNodes])
  const visibleEdges = useMemo(
    () => edges.filter((e) => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target)),
    [edges, visibleNodeIds]
  )

  const nodeMap = useMemo(() => new Map(visibleNodes.map((n) => [n.id, n])), [visibleNodes])

  // 选中节点的直接关系边
  const highlightedEdges = useMemo(() => {
    if (!selectedNodeId) return new Set<number>()
    const set = new Set<number>()
    visibleEdges.forEach((e, i) => {
      if (e.source === selectedNodeId || e.target === selectedNodeId) set.add(i)
    })
    return set
  }, [selectedNodeId, visibleEdges])

  const highlightedNodes = useMemo(() => {
    if (!selectedNodeId) return new Set<string>()
    const set = new Set<string>([selectedNodeId])
    visibleEdges.forEach((e) => {
      if (e.source === selectedNodeId) set.add(e.target)
      if (e.target === selectedNodeId) set.add(e.source)
    })
    return set
  }, [selectedNodeId, visibleEdges])

  if (tooManyNodes) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <icons.AlertTriangle className={`${iconSize.xl} mx-auto mb-3 text-amber-500`} />
          <p className="text-sm font-medium text-foreground mb-1">
            节点数量超过 {MAX_VISIBLE_NODES}
          </p>
          <p className="text-xs text-muted-foreground">请缩小搜索范围或使用过滤器减少显示节点</p>
        </div>
      </div>
    )
  }

  if (visibleNodes.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-muted-foreground">
          <icons.Network className="w-16 h-16 mx-auto mb-4 opacity-20" />
          <p className="text-sm">输入关键词探索知识图谱</p>
          <p className="text-xs mt-1 opacity-60">可视化法规、案件、主体间的关系网络</p>
        </div>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="flex-1 relative overflow-hidden bg-muted/20 cursor-grab active:cursor-grabbing"
      onWheel={onWheel}
      onMouseDown={(e) => {
        if ((e.target as HTMLElement).tagName === 'svg' || (e.target as HTMLElement).tagName === 'rect') {
          onPanStart(e)
        }
      }}
    >
      <svg width={width} height={height} className="select-none">
        <defs>
          <marker
            id="arrowhead"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" className="text-border" />
          </marker>
          <marker
            id="arrowhead-highlight"
            viewBox="0 0 10 7"
            refX="10"
            refY="3.5"
            markerWidth="8"
            markerHeight="6"
            orient="auto"
          >
            <polygon points="0 0, 10 3.5, 0 7" fill="hsl(var(--primary))" />
          </marker>
        </defs>

        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* 边 */}
          {visibleEdges.map((edge, i) => {
            const s = nodeMap.get(edge.source)
            const t = nodeMap.get(edge.target)
            if (!s || !t) return null
            const isHighlighted = highlightedEdges.has(i)
            const dimmed = selectedNodeId && !isHighlighted
            const sr = getNodeRadius(s.relationCount)
            const tr = getNodeRadius(t.relationCount)
            // 缩短线到节点边缘
            const dx = t.x - s.x
            const dy = t.y - s.y
            const dist = Math.sqrt(dx * dx + dy * dy) || 1
            const ux = dx / dist
            const uy = dy / dist
            const x1 = s.x + ux * sr
            const y1 = s.y + uy * sr
            const x2 = t.x - ux * (tr + 8)
            const y2 = t.y - uy * (tr + 8)
            const mx = (s.x + t.x) / 2
            const my = (s.y + t.y) / 2

            return (
              <g key={`edge-${i}`} opacity={dimmed ? 0.15 : 1}>
                <line
                  x1={x1}
                  y1={y1}
                  x2={x2}
                  y2={y2}
                  stroke={isHighlighted ? 'hsl(var(--primary))' : 'var(--border)'}
                  strokeWidth={isHighlighted ? 2 : 1}
                  markerEnd={isHighlighted ? 'url(#arrowhead-highlight)' : 'url(#arrowhead)'}
                />
                {zoom > 0.5 && (
                  <text
                    x={mx}
                    y={my - 6}
                    textAnchor="middle"
                    fontSize={10}
                    fill={isHighlighted ? 'hsl(var(--primary))' : 'var(--muted-foreground)'}
                    fontWeight={isHighlighted ? 600 : 400}
                    className="pointer-events-none"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            )
          })}

          {/* 节点 */}
          {visibleNodes.map((node) => {
            const r = getNodeRadius(node.relationCount)
            const color = getNodeColor(node.type)
            const isSelected = selectedNodeId === node.id
            const isHovered = hoveredNodeId === node.id
            const dimmed = selectedNodeId && !highlightedNodes.has(node.id)

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                opacity={dimmed ? 0.2 : 1}
                className="cursor-pointer"
                onMouseDown={(e) => {
                  e.stopPropagation()
                  onDragStart(node.id, e)
                }}
                onClick={(e) => {
                  e.stopPropagation()
                  onSelectNode(selectedNodeId === node.id ? null : node.id)
                }}
                onDoubleClick={(e) => {
                  e.stopPropagation()
                  onDoubleClickNode(node.id)
                }}
                onMouseEnter={() => onHoverNode(node.id)}
                onMouseLeave={() => onHoverNode(null)}
              >
                {/* 选中光环 */}
                {isSelected && (
                  <circle
                    r={r + 5}
                    fill="none"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    opacity={0.5}
                  />
                )}
                {/* 悬停光环 */}
                {isHovered && !isSelected && (
                  <circle
                    r={r + 3}
                    fill="none"
                    stroke={color}
                    strokeWidth={1.5}
                    opacity={0.4}
                  />
                )}
                {/* 节点圆 */}
                <circle
                  r={r}
                  fill={color + '20'}
                  stroke={isSelected ? 'hsl(var(--primary))' : color}
                  strokeWidth={isSelected ? 2.5 : 1.5}
                />
                {/* 内部文字（类型首字） */}
                <text
                  textAnchor="middle"
                  dy="0.35em"
                  fontSize={r > 12 ? 11 : 9}
                  fontWeight={600}
                  fill={color}
                  className="pointer-events-none"
                >
                  {getNodeLabel(node.type)?.[0] || '?'}
                </text>
                {/* 节点名称（下方） */}
                {zoom > 0.4 && (
                  <text
                    textAnchor="middle"
                    y={r + 14}
                    fontSize={11}
                    fill="var(--foreground)"
                    fontWeight={isSelected || isHovered ? 600 : 400}
                    className="pointer-events-none"
                  >
                    {node.name.length > 8 ? node.name.slice(0, 8) + '...' : node.name}
                  </text>
                )}
              </g>
            )
          })}
        </g>

        {/* 背景可点击区域（用于取消选中） */}
        <rect
          width={width}
          height={height}
          fill="transparent"
          className="pointer-events-none"
        />
      </svg>

      {/* Tooltip */}
      {hoveredNodeId && !selectedNodeId && (() => {
        const hNode = nodes.find((n) => n.id === hoveredNodeId)
        if (!hNode) return null
        const sx = hNode.x * zoom + pan.x
        const sy = hNode.y * zoom + pan.y
        return (
          <div
            className="absolute pointer-events-none bg-background border border-border rounded-lg shadow-lg px-3 py-2 z-10"
            style={{
              left: sx + 20,
              top: sy - 10,
              maxWidth: 200,
            }}
          >
            <p className="text-sm font-medium text-foreground">{hNode.name}</p>
            <div className="flex items-center gap-1.5 mt-1">
              <TypeBadge type={hNode.type} />
              <span className="text-[10px] text-muted-foreground">
                {hNode.relationCount} 条关系
              </span>
            </div>
          </div>
        )
      })()}

      {/* 缩放信息 */}
      <div className="absolute bottom-3 left-3 text-[10px] text-muted-foreground bg-background/80 border border-border rounded px-2 py-1">
        {Math.round(zoom * 100)}% | {visibleNodes.length} 节点 | {visibleEdges.length} 关系
      </div>
    </div>
  )
}

// ============================================================
// 右侧详情面板
// ============================================================

interface DetailPanelProps {
  detail: EntityDetail | null
  loading: boolean
  onClose: () => void
  onClickRelation: (name: string) => void
  onExpandInGraph: () => void
  collapsed: boolean
  onToggleCollapse: () => void
  onDeleteEntity?: (name: string) => void
  onEditEntity?: (name: string) => void
}

function DetailPanel({
  detail,
  loading,
  onClose,
  onClickRelation,
  onExpandInGraph,
  collapsed,
  onToggleCollapse,
  onDeleteEntity,
  onEditEntity,
}: DetailPanelProps) {
  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        className="w-10 border-l border-border flex items-center justify-center hover:bg-muted transition-colors shrink-0 hidden lg:flex"
        title="展开详情"
      >
        <icons.ChevronLeft className={iconSize.sm} />
      </button>
    )
  }

  return (
    <div className="w-80 border-l border-border flex flex-col h-full overflow-hidden shrink-0 hidden lg:flex">
      <div className="flex items-center justify-between p-4 border-b border-border shrink-0">
        <h3 className={heading.section}>实体详情</h3>
        <div className="flex items-center gap-1">
          <button onClick={onToggleCollapse} className={buttonStyle.icon} title="收起">
            <icons.ChevronRight className={iconSize.sm} />
          </button>
          <button onClick={onClose} className={buttonStyle.icon} title="关闭">
            <icons.X className={iconSize.sm} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-8 w-2/3" />
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-32 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : detail ? (
          <>
            {/* 名称 + 类型 */}
            <div>
              <h4 className="text-base font-semibold text-foreground mb-1.5">{detail.name}</h4>
              <TypeBadge type={detail.type} size="md" />
            </div>

            {/* 属性列表 */}
            {Object.keys(detail.properties).length > 0 && (
              <div>
                <h5 className={`${heading.card} mb-2`}>属性</h5>
                <div className="border border-border rounded-lg overflow-hidden">
                  <table className="w-full text-xs">
                    <tbody>
                      {Object.entries(detail.properties).map(([k, v]) => (
                        <tr key={k} className="border-b border-border last:border-b-0">
                          <td className="px-3 py-1.5 bg-muted/50 text-muted-foreground font-medium w-24">
                            {k}
                          </td>
                          <td className="px-3 py-1.5 text-foreground">{v}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* 出边关系 */}
            {detail.outEdges.length > 0 && (
              <div>
                <h5 className={`${heading.card} mb-2`}>
                  出边关系
                  <span className="text-muted-foreground font-normal ml-1">
                    ({detail.outEdges.length})
                  </span>
                </h5>
                <div className="space-y-1">
                  {detail.outEdges.map((edge, i) => (
                    <button
                      key={i}
                      onClick={() => onClickRelation(edge.target)}
                      className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-muted transition-colors group"
                    >
                      <span className="text-xs text-foreground truncate flex-1">
                        {detail.name}
                      </span>
                      <span className={`${statusBadge.info} text-[10px] px-1.5 py-0 rounded`}>
                        {edge.label}
                      </span>
                      <icons.ArrowRight className={`${iconSize.xs} text-muted-foreground`} />
                      <span className="text-xs text-primary group-hover:underline truncate flex-1">
                        {edge.target}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 入边关系 */}
            {detail.inEdges.length > 0 && (
              <div>
                <h5 className={`${heading.card} mb-2`}>
                  入边关系
                  <span className="text-muted-foreground font-normal ml-1">
                    ({detail.inEdges.length})
                  </span>
                </h5>
                <div className="space-y-1">
                  {detail.inEdges.map((edge, i) => (
                    <button
                      key={i}
                      onClick={() => onClickRelation(edge.source)}
                      className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-muted transition-colors group"
                    >
                      <span className="text-xs text-primary group-hover:underline truncate flex-1">
                        {edge.source}
                      </span>
                      <icons.ArrowRight className={`${iconSize.xs} text-muted-foreground`} />
                      <span className={`${statusBadge.info} text-[10px] px-1.5 py-0 rounded`}>
                        {edge.label}
                      </span>
                      <icons.ArrowRight className={`${iconSize.xs} text-muted-foreground`} />
                      <span className="text-xs text-foreground truncate flex-1">
                        {detail.name}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 关联文档 */}
            {detail.documents && detail.documents.length > 0 && (
              <div>
                <h5 className={`${heading.card} mb-2`}>关联文档</h5>
                <div className="space-y-1">
                  {detail.documents.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-muted transition-colors cursor-pointer"
                    >
                      <icons.FileText className={`${iconSize.sm} text-muted-foreground`} />
                      <span className="text-xs text-primary truncate">{doc.title}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 操作按钮 */}
            <div className="space-y-2">
              <button
                onClick={onExpandInGraph}
                className={`${buttonStyle.secondary} w-full justify-center flex items-center gap-1.5`}
              >
                <icons.Network className={iconSize.sm} />
                在图谱中展开
              </button>
              <div className="flex gap-2">
                {onEditEntity && (
                  <button
                    onClick={() => onEditEntity(detail.name)}
                    className={`${buttonStyle.ghost} flex-1 justify-center flex items-center gap-1.5`}
                  >
                    <icons.Edit className={iconSize.sm} />
                    编辑
                  </button>
                )}
                {onDeleteEntity && (
                  <button
                    onClick={() => onDeleteEntity(detail.name)}
                    className="flex-1 justify-center flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <icons.Trash2 className={iconSize.sm} />
                    删除
                  </button>
                )}
              </div>
            </div>
          </>
        ) : (
          <EmptyState message="点击图谱节点查看详情" />
        )}
      </div>
    </div>
  )
}

// ============================================================
// 移动端底部抽屉
// ============================================================

function MobileDetailDrawer({
  detail,
  loading,
  onClose,
  onClickRelation,
}: {
  detail: EntityDetail | null
  loading: boolean
  onClose: () => void
  onClickRelation: (name: string) => void
}) {
  if (!detail && !loading) return null

  return (
    <div className="lg:hidden fixed inset-x-0 bottom-0 z-50 bg-background border-t border-border rounded-t-2xl shadow-xl max-h-[50vh] overflow-y-auto">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border sticky top-0 bg-background">
        <h3 className={heading.section}>{loading ? '加载中...' : detail?.name}</h3>
        <button onClick={onClose} className={buttonStyle.icon}>
          <icons.X className={iconSize.sm} />
        </button>
      </div>
      <div className="p-4 space-y-3">
        {loading ? (
          <div className="space-y-2">
            <Skeleton className="h-6 w-1/2" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : detail ? (
          <>
            <TypeBadge type={detail.type} size="md" />
            {Object.keys(detail.properties).length > 0 && (
              <div className="grid grid-cols-2 gap-2 text-xs">
                {Object.entries(detail.properties).map(([k, v]) => (
                  <div key={k}>
                    <span className="text-muted-foreground">{k}: </span>
                    <span className="text-foreground font-medium">{v}</span>
                  </div>
                ))}
              </div>
            )}
            {detail.outEdges.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {detail.outEdges.map((e, i) => (
                  <button
                    key={i}
                    onClick={() => onClickRelation(e.target)}
                    className="text-[10px] px-2 py-1 rounded bg-muted text-primary hover:underline"
                  >
                    {e.label} {e.target}
                  </button>
                ))}
              </div>
            )}
          </>
        ) : null}
      </div>
    </div>
  )
}

// ============================================================
// 主组件
// ============================================================

export default function KnowledgeGraph() {
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
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null)
  const [entityDetail, setEntityDetail] = useState<EntityDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailCollapsed, setDetailCollapsed] = useState(false)

  const [pathFrom, setPathFrom] = useState('')
  const [pathTo, setPathTo] = useState('')
  const [pathLoading, setPathLoading] = useState(false)

  const [graphLoading, setGraphLoading] = useState(false)
  const [graphError, setGraphError] = useState<string | null>(null)

  // --- 弹窗状态 ---
  const [showAddEntity, setShowAddEntity] = useState(false)
  const [showAddRelation, setShowAddRelation] = useState(false)
  const [showImportExport, setShowImportExport] = useState(false)
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

  // --- 视口 ---
  const containerRef = useRef<HTMLDivElement>(null!)
  const [canvasSize, setCanvasSize] = useState({ width: 800, height: 600 })
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const panStartRef = useRef<{ x: number; y: number; px: number; py: number } | null>(null)
  const dragRef = useRef<{ nodeId: string; startX: number; startY: number } | null>(null)

  // --- 力导向布局 ---
  const { nodes, edges, renderTick, setNodePosition, reheat } = useForceLayout(
    graphNodes,
    graphEdges,
    canvasSize.width,
    canvasSize.height
  )

  const tooManyNodes = graphNodes.length > MAX_VISIBLE_NODES

  // --- 初始化 ---
  useEffect(() => {
    loadStats()
    loadTypes()
  }, [])

  // --- 画布尺寸监听 ---
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) {
          setCanvasSize({ width, height })
        }
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [graphNodes.length])

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
    const node = nodes.find((n) => n.id === selectedNodeId)
    if (node) {
      loadEntityDetail(node.name, node.type)
    }
  }, [selectedNodeId])

  // ============================================================
  // API 调用
  // ============================================================

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
      const resp = await fetch('/api/knowledge-center/graph/types')
      if (resp.ok) {
        const data = await resp.json()
        const types: string[] = data.types || data
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
      const resp = await fetch(
        `/api/knowledge-center/graph/search?keyword=${encodeURIComponent(keyword)}&limit=50`
      )
      if (resp.ok) {
        const data = await resp.json()
        const results: SearchResult[] = (data.nodes || data.results || data).map((n: any) => ({
          id: n.id || n.name,
          name: n.name || n.label,
          type: n.type,
        }))
        setSearchResults(results)
        return
      }
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
      const resp = await fetch(
        `/api/knowledge-center/graph/subgraph/${encodeURIComponent(name)}?depth=${depth}&max_nodes=100`
      )
      if (resp.ok) {
        const data = await resp.json()
        const { nodes: n, edges: e } = convertApiData(data)
        mergeGraph(n, e)
        return
      }
      // 尝试旧 API
      const data = await knowledgeCenterApi.searchGraph(name, depth, 100)
      const { nodes: n, edges: e } = convertApiData(data)
      mergeGraph(n, e)
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
      const resp = await fetch(
        `/api/knowledge-center/graph/entity/${encodeURIComponent(name)}/detail`
      )
      if (resp.ok) {
        const data = await resp.json()
        setEntityDetail(data)
        return
      }
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
      const resp = await fetch(
        `/api/knowledge-center/graph/path?from=${encodeURIComponent(pathFrom)}&to=${encodeURIComponent(pathTo)}`
      )
      if (resp.ok) {
        const data = await resp.json()
        const { nodes: n, edges: e } = convertApiData(data)
        setGraphNodes(n)
        setGraphEdges(e)
        setSelectedNodeId(null)
        toast.success(`找到从 "${pathFrom}" 到 "${pathTo}" 的路径`)
        return
      }
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
    const existing = nodes.find((n) => n.name === result.name)
    if (existing) {
      setSelectedNodeId(existing.id)
      // 居中到该节点
      setPan({
        x: canvasSize.width / 2 - existing.x * zoom,
        y: canvasSize.height / 2 - existing.y * zoom,
      })
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
    const node = nodes.find((n) => n.id === id)
    if (node) {
      loadSubgraph(node.name, 1)
      toast.info(`展开 "${node.name}" 的子图`)
    }
  }

  function handleDragStart(nodeId: string, e: ReactMouseEvent) {
    e.preventDefault()
    dragRef.current = { nodeId, startX: e.clientX, startY: e.clientY }
    setNodePosition(nodeId, nodes.find((n) => n.id === nodeId)!.x, nodes.find((n) => n.id === nodeId)!.y, true)

    const onMove = (ev: globalThis.MouseEvent) => {
      if (!dragRef.current) return
      const node = nodes.find((n) => n.id === dragRef.current!.nodeId)
      if (!node) return
      const dx = (ev.clientX - dragRef.current.startX) / zoom
      const dy = (ev.clientY - dragRef.current.startY) / zoom
      dragRef.current.startX = ev.clientX
      dragRef.current.startY = ev.clientY
      setNodePosition(dragRef.current.nodeId, node.x + dx, node.y + dy, true)
    }

    const onUp = () => {
      if (dragRef.current) {
        setNodePosition(dragRef.current.nodeId, nodes.find((n) => n.id === dragRef.current!.nodeId)!.x, nodes.find((n) => n.id === dragRef.current!.nodeId)!.y, false)
        dragRef.current = null
      }
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  function handleWheel(e: React.WheelEvent) {
    e.preventDefault()
    const delta = e.deltaY > 0 ? 0.92 : 1.08
    const newZoom = Math.min(Math.max(zoom * delta, 0.1), 5)
    // 缩放对准鼠标位置
    const rect = containerRef.current?.getBoundingClientRect()
    if (rect) {
      const mx = e.clientX - rect.left
      const my = e.clientY - rect.top
      const scale = newZoom / zoom
      setPan({
        x: mx - (mx - pan.x) * scale,
        y: my - (my - pan.y) * scale,
      })
    }
    setZoom(newZoom)
  }

  function handlePanStart(e: ReactMouseEvent) {
    if (e.button !== 0) return
    panStartRef.current = { x: e.clientX, y: e.clientY, px: pan.x, py: pan.y }

    const onMove = (ev: globalThis.MouseEvent) => {
      if (!panStartRef.current) return
      setPan({
        x: panStartRef.current.px + (ev.clientX - panStartRef.current.x),
        y: panStartRef.current.py + (ev.clientY - panStartRef.current.y),
      })
    }

    const onUp = () => {
      panStartRef.current = null
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  function handleClickRelation(name: string) {
    // 尝试选中已有节点
    const existing = nodes.find((n) => n.name === name)
    if (existing) {
      setSelectedNodeId(existing.id)
      setPan({
        x: canvasSize.width / 2 - existing.x * zoom,
        y: canvasSize.height / 2 - existing.y * zoom,
      })
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
      setShowImportExport(false)
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
  // 渲染
  // ============================================================

  return (
    <PageContainer
      title="知识图谱"
      description="可视化法规、案件、主体间的关系网络"
      scrollable={false}
      fullHeight
      actions={
        <div className="flex items-center gap-1.5 flex-wrap">
          <button onClick={() => setShowAddEntity(true)} className={buttonStyle.ghost} title="添加实体">
            <icons.Plus className={iconSize.sm} />
            <span className="hidden sm:inline text-xs ml-1">实体</span>
          </button>
          <button onClick={() => setShowAddRelation(true)} className={buttonStyle.ghost} title="添加关系">
            <icons.Link className={iconSize.sm} />
            <span className="hidden sm:inline text-xs ml-1">关系</span>
          </button>
          <button onClick={() => setShowImportExport(true)} className={buttonStyle.ghost} title="导入/导出">
            <icons.Download className={iconSize.sm} />
            <span className="hidden sm:inline text-xs ml-1">导入导出</span>
          </button>
          <button onClick={() => setShowAIExtract(true)} className={buttonStyle.ghost} title="AI抽取">
            <icons.Sparkles className={iconSize.sm} />
            <span className="hidden sm:inline text-xs ml-1">AI抽取</span>
          </button>
          <div className="w-px h-5 bg-border mx-1 hidden sm:block" />
          {graphNodes.length > 0 && (
            <>
              <button
                onClick={() => {
                  setZoom(1)
                  setPan({ x: 0, y: 0 })
                }}
                className={buttonStyle.ghost}
                title="重置视图"
              >
                <icons.Focus className={iconSize.sm} />
              </button>
              <button onClick={reheat} className={buttonStyle.ghost} title="重新布局">
                <icons.RefreshCw className={iconSize.sm} />
              </button>
              <button
                onClick={() => {
                  setGraphNodes([])
                  setGraphEdges([])
                  setSelectedNodeId(null)
                  setEntityDetail(null)
                  setPan({ x: 0, y: 0 })
                  setZoom(1)
                }}
                className={buttonStyle.ghost}
                title="清除图谱"
              >
                <icons.Trash2 className={iconSize.sm} />
              </button>
            </>
          )}
        </div>
      }
    >
      <div className="flex-1 flex min-h-0 -mx-4 sm:-mx-5 lg:-mx-6 -mb-4 sm:-mb-5 lg:-mb-6">
        {/* 左侧工具栏 */}
        <LeftPanel
          searchQuery={searchQuery}
          setSearchQuery={setSearchQuery}
          searchResults={searchResults}
          searchLoading={searchLoading}
          onSelectResult={handleSelectSearchResult}
          entityTypes={entityTypes}
          activeTypes={activeTypes}
          onToggleType={handleToggleType}
          pathFrom={pathFrom}
          setPathFrom={setPathFrom}
          pathTo={pathTo}
          setPathTo={setPathTo}
          onQueryPath={handlePathQuery}
          pathLoading={pathLoading}
          stats={stats}
          statsLoading={statsLoading}
        />

        {/* 中间图谱 */}
        <div className="flex-1 flex flex-col min-w-0 relative">
          {graphLoading && (
            <div className="absolute inset-0 bg-background/60 backdrop-blur-sm z-20 flex items-center justify-center">
              <div className="flex items-center gap-3 bg-background border border-border rounded-xl px-5 py-3 shadow-lg">
                <icons.Loader2 className={`${iconSize.md} animate-spin text-primary`} />
                <span className="text-sm text-foreground">加载图谱数据...</span>
              </div>
            </div>
          )}

          {graphError ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <icons.AlertCircle className={`${iconSize.xl} mx-auto mb-3 text-destructive`} />
                <p className="text-sm text-foreground mb-3">{graphError}</p>
                <button onClick={handleRetry} className={buttonStyle.primary}>
                  重试
                </button>
              </div>
            </div>
          ) : (
            <GraphCanvas
              nodes={nodes}
              edges={edges}
              activeTypes={activeTypes}
              selectedNodeId={selectedNodeId}
              hoveredNodeId={hoveredNodeId}
              onSelectNode={setSelectedNodeId}
              onHoverNode={setHoveredNodeId}
              onDoubleClickNode={handleDoubleClickNode}
              onDragStart={handleDragStart}
              zoom={zoom}
              pan={pan}
              onWheel={handleWheel}
              onPanStart={handlePanStart}
              containerRef={containerRef}
              width={canvasSize.width}
              height={canvasSize.height}
              tooManyNodes={tooManyNodes}
            />
          )}
        </div>

        {/* 右侧详情面板 (桌面) */}
        {(selectedNodeId || entityDetail || detailLoading) && (
          <DetailPanel
            detail={entityDetail}
            loading={detailLoading}
            onClose={() => {
              setSelectedNodeId(null)
              setEntityDetail(null)
            }}
            onClickRelation={handleClickRelation}
            onExpandInGraph={handleExpandInGraph}
            collapsed={detailCollapsed}
            onToggleCollapse={() => setDetailCollapsed(!detailCollapsed)}
            onDeleteEntity={handleDeleteEntity}
            onEditEntity={(name) => {
              setNewEntityName(name)
              setNewEntityType(entityDetail?.type || 'Entity')
              setNewEntityProps(
                entityDetail?.properties
                  ? Object.entries(entityDetail.properties).map(([key, value]) => ({ key, value }))
                  : []
              )
              setShowAddEntity(true)
            }}
          />
        )}
      </div>

      {/* 移动端底部抽屉 */}
      <MobileDetailDrawer
        detail={entityDetail}
        loading={detailLoading}
        onClose={() => {
          setSelectedNodeId(null)
          setEntityDetail(null)
        }}
        onClickRelation={handleClickRelation}
      />

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
      {/* 弹窗：导入/导出 */}
      {/* ============================================================ */}
      {showImportExport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
          <div className="bg-background border border-border rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between p-5 border-b border-border">
              <h3 className={heading.section}>导入 / 导出</h3>
              <button onClick={() => { setShowImportExport(false); setImportFile(null); setImportPreview([]) }} className={buttonStyle.icon}>
                <icons.X className={iconSize.sm} />
              </button>
            </div>
            <div className="p-5 space-y-5">
              {/* 导出区域 */}
              <div>
                <h4 className={`${heading.card} mb-2`}>导出图谱</h4>
                <p className="text-xs text-muted-foreground mb-3">
                  将当前知识图谱中所有三元组导出为 CSV 文件（subject, predicate, object 格式）
                </p>
                <button
                  onClick={handleExportGraph}
                  disabled={exportLoading}
                  className={`${buttonStyle.secondary} flex items-center gap-1.5`}
                >
                  {exportLoading ? (
                    <icons.Loader2 className={`${iconSize.sm} animate-spin`} />
                  ) : (
                    <icons.Download className={iconSize.sm} />
                  )}
                  {exportLoading ? '导出中...' : '导出 CSV'}
                </button>
              </div>

              <div className="border-t border-border" />

              {/* 导入区域 */}
              <div>
                <h4 className={`${heading.card} mb-2`}>导入三元组</h4>
                <p className="text-xs text-muted-foreground mb-3">
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
    </PageContainer>
  )
}
