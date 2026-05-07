/**
 * ForceGraphCanvas - 专业级知识图谱可视化组件
 *
 * 基于 react-force-graph 实现 3D/2D 切换渲染：
 * - 3D: THREE.js 发光球体 + SpriteText 标签 + 粒子流动
 * - 2D: Canvas 自定义绘制（光晕圆 + 类型首字 + 标签）
 * - 节点点击聚焦、右键展开、拖拽交互
 */

import { useState, useCallback, useEffect, useRef, useMemo, forwardRef, useImperativeHandle } from 'react'
import * as THREE from 'three'
import SpriteText from 'three-spritetext'
import { graphCanvasColors, graphNodeColors } from '@/lib/design-tokens'
import { measureAndCache, truncateToWidth, setFontIfChanged } from './textMeasureCache'
import { createGraphRenderPlan, GRAPH_RENDER_LIMITS } from './graphPerformance'

// 节点类型配置（颜色 + 发光 + 图标 + 中文标签）
const NODE_CONFIG: Record<string, { color: string; emissive: string; char: string; label: string }> = {
  '法规': { color: graphNodeColors.law, emissive: '#16a34a', char: '法', label: '法规' },
  '案例': { color: graphNodeColors.case, emissive: '#2563eb', char: '案', label: '案例' },
  '当事人': { color: graphNodeColors.party, emissive: '#d97706', char: '当', label: '当事人' },
  '机构': { color: graphNodeColors.organization, emissive: '#7c3aed', char: '机', label: '机构' },
  '律师': { color: graphNodeColors.lawyer, emissive: '#ea580c', char: '律', label: '律师' },
  '其他': { color: graphNodeColors.other, emissive: '#4b5563', char: '其', label: '其他' },
  // API 字段兼容
  law: { color: graphNodeColors.law, emissive: '#16a34a', char: '法', label: '法规' },
  entity: { color: graphNodeColors.case, emissive: '#2563eb', char: '实', label: '实体' },
  document: { color: graphNodeColors.lawyer, emissive: '#ea580c', char: '文', label: '文档' },
  query: { color: graphNodeColors.query, emissive: '#475569', char: '查', label: '查询' },
  conclusion: { color: graphNodeColors.conclusion, emissive: '#9333ea', char: '结', label: '结论' },
}

function getCfg(type: string) {
  return NODE_CONFIG[type] || NODE_CONFIG['其他']
}

// ---- 接口 ----

export interface ForceGraphNode {
  id: string
  name: string
  type: string
  relationCount: number
}

export interface ForceGraphEdge {
  source: string
  target: string
  label: string
}

interface Props {
  nodes: ForceGraphNode[]
  edges: ForceGraphEdge[]
  activeTypes: Set<string>
  selectedNodeId: string | null
  onSelectNode: (id: string | null) => void
  onDoubleClickNode: (id: string) => void
  viewMode: '2d' | '3d'
  showLabels: boolean
  autoRotate?: boolean
}

export interface ForceGraphCanvasHandle {
  zoomToFit: () => void
  resetView: () => void
}

// ---- 内部数据格式 ----

interface FGNode {
  id: string
  name: string
  type: string
  val: number
  color: string
}

interface FGLink {
  source: string
  target: string
  label: string
  color: string
}

function toFGData(nodes: ForceGraphNode[], edges: ForceGraphEdge[], activeTypes: Set<string>) {
  const filteredNodes = nodes.filter(n => activeTypes.has(n.type))
  const nodeIds = new Set(filteredNodes.map(n => n.id))

  const fgNodes: FGNode[] = filteredNodes.map(n => ({
    id: n.id,
    name: n.name,
    type: n.type,
    val: Math.max(4, Math.min(n.relationCount * 1.5 + 4, 14)),
    color: getCfg(n.type).color,
  }))

  const fgLinks: FGLink[] = edges
    .filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
    .map(e => ({
      source: e.source,
      target: e.target,
      label: e.label,
      color: 'rgba(148, 163, 184, 0.35)',
    }))

  return { nodes: fgNodes, links: fgLinks }
}

// ---- 组件 ----

export const ForceGraphCanvas = forwardRef<ForceGraphCanvasHandle, Props>(function ForceGraphCanvas({
  nodes, edges, activeTypes, selectedNodeId, onSelectNode, onDoubleClickNode, viewMode, showLabels, autoRotate = false,
}, ref) {
  const graphRef = useRef<any>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  useImperativeHandle(ref, () => ({
    zoomToFit: () => {
      graphRef.current?.zoomToFit?.(400, 40)
    },
    resetView: () => {
      if (viewMode === '3d') {
        graphRef.current?.cameraPosition?.({ x: 0, y: 0, z: 300 }, { x: 0, y: 0, z: 0 }, 800)
      } else {
        graphRef.current?.centerAt?.(0, 0, 400)
        graphRef.current?.zoom?.(1, 400)
      }
    },
  }), [viewMode])

  // 跟随系统深色/浅色模式
  const [isDark, setIsDark] = useState(() => document.documentElement.classList.contains('dark'))
  useEffect(() => {
    const root = document.documentElement
    const observer = new MutationObserver(() => {
      setIsDark(root.classList.contains('dark'))
    })
    observer.observe(root, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

  // 3D 自动旋转：通过 OrbitControls 的 autoRotate 属性实现
  useEffect(() => {
    if (viewMode !== '3d' || !graphRef.current) return
    const controls = graphRef.current.controls?.()
    if (controls) {
      controls.autoRotate = autoRotate
      controls.autoRotateSpeed = 1.5
    }
  }, [autoRotate, viewMode])

  // 动态导入 react-force-graph
  const [FG3D, setFG3D] = useState<any>(null)
  const [FG2D, setFG2D] = useState<any>(null)
  const [graphEngineError, setGraphEngineError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setGraphEngineError(null)
    Promise.all([
      import('react-force-graph-3d'),
      import('react-force-graph-2d'),
    ]).then(([mod3d, mod2d]) => {
      if (cancelled) return
      setFG3D(() => mod3d.default)
      setFG2D(() => mod2d.default)
    }).catch((err) => {
      if (cancelled) return
      console.error('图谱引擎加载失败:', err)
      setGraphEngineError(err?.message || '图谱引擎加载失败')
    })
    return () => { cancelled = true }
  }, [])

  // 容器尺寸监听
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const observer = new ResizeObserver(entries => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect
        if (width > 0 && height > 0) setDimensions({ width, height })
      }
    })
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  const rawFgData = useMemo(
    () => toFGData(nodes, edges, activeTypes),
    [nodes, edges, activeTypes]
  )

  const renderPlan = useMemo(
    () => createGraphRenderPlan(rawFgData.nodes, rawFgData.links, {
      maxNodes: GRAPH_RENDER_LIMITS.maxNodes,
      maxLinks: GRAPH_RENDER_LIMITS.maxLinks,
      selectedNodeId,
    }),
    [rawFgData.nodes, rawFgData.links, selectedNodeId]
  )

  // 数据转换
  const fgData = useMemo(
    () => ({ nodes: renderPlan.nodes, links: renderPlan.links }),
    [renderPlan.nodes, renderPlan.links]
  )

  const particleCount = renderPlan.isDownsampled ? 0 : 2
  const warmupTicks = renderPlan.isDownsampled ? 20 : 60
  const cooldownTicks = renderPlan.isDownsampled ? 80 : 200

  // 选中节点的关联节点 ID（用于高亮）
  const highlightIds = useMemo(() => {
    if (!selectedNodeId) return new Set<string>()
    const set = new Set<string>([selectedNodeId])
    fgData.links.forEach(l => {
      const src = typeof l.source === 'object' ? (l.source as any).id : l.source
      const tgt = typeof l.target === 'object' ? (l.target as any).id : l.target
      if (src === selectedNodeId) set.add(tgt)
      if (tgt === selectedNodeId) set.add(src)
    })
    return set
  }, [selectedNodeId, fgData.links])

  // 节点点击 — 3D 模式下聚焦
  const handleNodeClick = useCallback((node: any) => {
    onSelectNode(node.id)
    if (viewMode === '3d' && graphRef.current) {
      const distance = 120
      const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0)
      graphRef.current.cameraPosition(
        { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
        node, 1200
      )
    }
  }, [viewMode, onSelectNode])

  // 右键展开
  const handleRightClick = useCallback((node: any) => {
    onDoubleClickNode(node.id)
  }, [onDoubleClickNode])

  // ---- 3D 节点渲染 ----
  const nodeThreeObject = useCallback((node: any) => {
    const cfg = getCfg(node.type)
    const group = new THREE.Group()
    const r = node.val || 6

    // 发光球体
    const geo = new THREE.SphereGeometry(r, 24, 24)
    const mat = new THREE.MeshPhongMaterial({
      color: cfg.color, emissive: cfg.emissive, emissiveIntensity: isDark ? 0.3 : 0.15,
      shininess: 100, transparent: true, opacity: 0.92,
    })
    group.add(new THREE.Mesh(geo, mat))

    // 外层光晕
    const glowGeo = new THREE.SphereGeometry(r * 1.3, 16, 16)
    const glowMat = new THREE.MeshBasicMaterial({ color: cfg.color, transparent: true, opacity: isDark ? 0.08 : 0.12 })
    group.add(new THREE.Mesh(glowGeo, glowMat))

    // 选中高亮
    if (selectedNodeId && !highlightIds.has(node.id)) {
      mat.opacity = 0.25
      glowMat.opacity = 0.02
    }

    // 文字标签
    if (showLabels) {
      const sprite = new SpriteText(node.name)
      sprite.color = isDark ? graphCanvasColors.labelDark : graphCanvasColors.labelLight
      sprite.textHeight = 3.5
      sprite.fontWeight = '600'
      sprite.backgroundColor = isDark ? graphCanvasColors.tooltipDarkBg : graphCanvasColors.tooltipLightBg
      sprite.padding = [2, 4] as any
      sprite.borderRadius = 3
      sprite.position.y = -r - 5
      group.add(sprite)
    }
    return group
  }, [showLabels, selectedNodeId, highlightIds, isDark])

  // ---- 2D 节点渲染（使用文本测量缓存） ----
  const lastFontRef = useRef('')
  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const cfg = getCfg(node.type)
    const r = (node.val || 6) * 1.2
    const x = node.x || 0
    const y = node.y || 0
    const dimmed = selectedNodeId && !highlightIds.has(node.id)
    const alpha = dimmed ? 0.2 : 1

    ctx.globalAlpha = alpha

    // 光晕
    ctx.beginPath()
    ctx.arc(x, y, r * 1.6, 0, 2 * Math.PI)
    ctx.fillStyle = cfg.color + '15'
    ctx.fill()

    // 实心圆 + 描边
    ctx.beginPath()
    ctx.arc(x, y, r, 0, 2 * Math.PI)
    ctx.fillStyle = cfg.color
    ctx.fill()
    ctx.strokeStyle = cfg.color + '60'
    ctx.lineWidth = 1.5
    ctx.stroke()

    // 类型首字（白色）—— 字体缓存避免每帧重复 ctx.font 赋值
    const charSize = Math.max(r * 0.9, 5)
    const charFont = `bold ${charSize}px "Inter", "SF Pro", system-ui, sans-serif`
    lastFontRef.current = setFontIfChanged(ctx, charFont, lastFontRef.current)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = '#ffffff'
    ctx.fillText(cfg.char, x, y)

    // 名称标签 —— 基于像素宽度智能截断，替代朴素 slice(0,10)
    if (showLabels && globalScale > 0.4) {
      const fontSize = Math.max(10 / globalScale, 3)
      const labelFont = `600 ${fontSize}px "Inter", "SF Pro", system-ui, sans-serif`
      lastFontRef.current = setFontIfChanged(ctx, labelFont, lastFontRef.current)
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillStyle = document.documentElement.classList.contains('dark') ? graphCanvasColors.labelDark : graphCanvasColors.labelLight
      const maxLabelWidth = r * 6
      const label = truncateToWidth(node.name, labelFont, maxLabelWidth)
      ctx.fillText(label, x, y + r + 3)
    }

    ctx.globalAlpha = 1
  }, [showLabels, selectedNodeId, highlightIds])

  // 点击区域
  const nodePointerArea = useCallback((node: any, color: string, ctx: CanvasRenderingContext2D) => {
    const r = (node.val || 6) * 1.6
    ctx.beginPath()
    ctx.arc(node.x || 0, node.y || 0, r, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()
  }, [])

  // 2D 边标签绘制（使用文本测量缓存）
  const linkLastFontRef = useRef('')
  const linkCanvasObject = useCallback((link: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    if (globalScale < 0.6) return // 缩放太小不绘制标签
    const src = link.source
    const tgt = link.target
    if (!src || !tgt || !src.x || !tgt.x) return
    const mx = (src.x + tgt.x) / 2
    const my = (src.y + tgt.y) / 2
    const fontSize = Math.max(8 / globalScale, 2.5)
    const linkFont = `500 ${fontSize}px "Inter", system-ui, sans-serif`

    linkLastFontRef.current = setFontIfChanged(ctx, linkFont, linkLastFontRef.current)
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = document.documentElement.classList.contains('dark') ? 'rgba(148,163,184,0.7)' : 'rgba(100,116,139,0.7)'
    ctx.fillText(link.label || '', mx, my)
  }, [])

  // ---- 重置视角 ----
  const resetView = useCallback(() => {
    if (!graphRef.current) return
    if (viewMode === '3d') {
      graphRef.current.cameraPosition({ x: 0, y: 0, z: 300 }, { x: 0, y: 0, z: 0 }, 1000)
    } else {
      graphRef.current.zoomToFit(500, 60)
    }
  }, [viewMode])

  // 暴露 resetView
  useEffect(() => {
    if (containerRef.current) {
      (containerRef.current as any).__resetView = resetView
    }
  }, [resetView])

  // 自动 zoomToFit
  useEffect(() => {
    if (fgData.nodes.length > 0 && graphRef.current && viewMode === '2d') {
      setTimeout(() => graphRef.current?.zoomToFit?.(600, 60), 300)
    }
  }, [fgData.nodes.length, viewMode])

  const GraphComp = viewMode === '3d' ? FG3D : FG2D
  if (graphEngineError) {
    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted-foreground text-sm max-w-md text-center">
          <svg className="w-8 h-8 text-destructive" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></svg>
          <p>图谱引擎加载失败</p>
          <p className="text-xs text-muted-foreground/70">{graphEngineError}</p>
          <button
            className="mt-2 px-4 py-1.5 text-xs rounded-md border border-border hover:bg-accent transition-colors"
            onClick={() => window.location.reload()}
          >
            刷新重试
          </button>
        </div>
      </div>
    )
  }
  if (!GraphComp) {
    return (
      <div ref={containerRef} className="w-full h-full flex items-center justify-center">
        <div className="flex items-center gap-2 text-muted-foreground text-sm">
          <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeDasharray="30 70" /></svg>
          加载图谱引擎...
        </div>
      </div>
    )
  }

  const bgColor = isDark
    ? (viewMode === '3d' ? graphCanvasColors.dark3d : graphCanvasColors.dark2d)
    : (viewMode === '3d' ? graphCanvasColors.light3d : graphCanvasColors.light2d)

  return (
    <div
      ref={containerRef}
      className="w-full h-full relative"
      data-testid="knowledge-graph-canvas"
      data-rendered-nodes={fgData.nodes.length}
      data-rendered-links={fgData.links.length}
      data-downsampled={renderPlan.isDownsampled ? 'true' : 'false'}
      style={{ background: bgColor }}
    >
      {viewMode === '3d' ? (
        <FG3D
          ref={graphRef}
          graphData={fgData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor={bgColor}
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
          onNodeClick={handleNodeClick}
          onNodeRightClick={handleRightClick}
          onBackgroundClick={() => onSelectNode(null)}
          linkColor={(l: any) => l.color || (isDark ? graphCanvasColors.linkDark : graphCanvasColors.linkLight)}
          linkWidth={1.2}
          linkOpacity={isDark ? 0.5 : 0.6}
          linkDirectionalParticles={particleCount}
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleColor={() => graphCanvasColors.particle}
          linkDirectionalParticleSpeed={0.004}
          linkLabel={(l: any) => `<span style="color:${isDark ? graphCanvasColors.labelDark : graphCanvasColors.labelLight};font-size:11px;background:${isDark ? graphCanvasColors.tooltipDarkBg : graphCanvasColors.tooltipLightBg};padding:2px 6px;border-radius:4px;${isDark ? '' : `box-shadow:${graphCanvasColors.tooltipLightShadow}` }">${l.label}</span>`}
          enableNodeDrag
          enableNavigationControls
          showNavInfo={false}
          warmupTicks={warmupTicks}
          cooldownTicks={cooldownTicks}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      ) : (
        <FG2D
          ref={graphRef}
          graphData={fgData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor={bgColor}
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={nodePointerArea}
          onNodeClick={handleNodeClick}
          onNodeRightClick={handleRightClick}
          onBackgroundClick={() => onSelectNode(null)}
          linkColor={() => isDark ? graphCanvasColors.linkDark : graphCanvasColors.linkLight}
          linkWidth={1.5}
          linkDirectionalParticles={particleCount}
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleColor={() => graphCanvasColors.particle}
          linkCanvasObjectMode={() => 'after' as any}
          linkCanvasObject={linkCanvasObject}
          enableNodeDrag
          warmupTicks={renderPlan.isDownsampled ? 20 : 40}
          cooldownTicks={renderPlan.isDownsampled ? 80 : 150}
          d3AlphaDecay={0.025}
          d3VelocityDecay={0.3}
        />
      )}
    </div>
  )
})
