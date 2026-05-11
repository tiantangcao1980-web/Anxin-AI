/**
 * CrossModalGraph — 跨模态知识图谱（V3 P13-D）
 *
 * 基于 react-force-graph-2d 渲染：
 *   - 节点颜色由 entity 主 modality 决定（多模态 entity 取首个 modality + 内圈描边表示其它）
 *   - 跨模态边（cross_modal=true）特殊样式：
 *     - 虚线（短破折）
 *     - 线宽 2px（默认 1px）
 *     - 颜色为两端 modality 颜色的混合（绘制时分两段渐变）
 *     - 多颗粒子流动（直观提示跨模态融合）
 *
 * 极简：固定 2D（避免在面板里挤进 3D 控制），跟随系统深色模式。
 */

import { useEffect, useMemo, useRef, useState } from 'react'

import type { CrossModalKG, KGEntity, KGRelation, Modality } from '@/lib/api/rag'
import { modalityVisual } from './modalityStyle'

interface FGNode {
  id: string
  name: string
  primary_modality: Modality
  modalities: Modality[]
  val: number
  type: string
}

interface FGLink {
  source: string
  target: string
  label: string
  cross_modal: boolean
  modality_pair?: [Modality, Modality]
  weight: number
}

function nodeRadius(e: KGEntity): number {
  return Math.max(6, Math.min(14, 4 + Math.log2(e.mentions + 1) * 3))
}

export interface CrossModalGraphProps {
  kg: CrossModalKG | null
  selectedEntityId?: string | null
  onSelectEntity?: (entityId: string | null) => void
  /** 当节点关联到 segment 时，可以双击跳转 */
  onJumpToSegment?: (segmentId: string) => void
  height?: number
}

export function CrossModalGraph({
  kg,
  selectedEntityId,
  onSelectEntity,
  onJumpToSegment,
  height = 520,
}: CrossModalGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<unknown>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height })

  // 跟随深色模式
  const [isDark, setIsDark] = useState(() =>
    typeof document !== 'undefined' && document.documentElement.classList.contains('dark'),
  )
  useEffect(() => {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    const obs = new MutationObserver(() => setIsDark(root.classList.contains('dark')))
    obs.observe(root, { attributes: true, attributeFilter: ['class'] })
    return () => obs.disconnect()
  }, [])

  // 容器尺寸
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height: h } = entry.contentRect
        if (width > 0) setDimensions({ width, height: h > 0 ? h : height })
      }
    })
    obs.observe(el)
    return () => obs.disconnect()
  }, [height])

  // 异步加载 react-force-graph-2d（与 ForceGraphCanvas 同套路）
  const [FG2D, setFG2D] = useState<React.ComponentType<Record<string, unknown>> | null>(null)
  const [loadErr, setLoadErr] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    import('react-force-graph-2d')
      .then((mod) => {
        if (!cancelled) setFG2D(() => mod.default as React.ComponentType<Record<string, unknown>>)
      })
      .catch((err) => {
        if (!cancelled) setLoadErr(err?.message ?? '图谱引擎加载失败')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const fgData = useMemo(() => {
    if (!kg) return { nodes: [] as FGNode[], links: [] as FGLink[] }
    const nodes: FGNode[] = kg.entities.map((e) => ({
      id: e.entity_id,
      name: e.name,
      primary_modality: e.modalities[0] ?? 'text',
      modalities: e.modalities,
      val: nodeRadius(e),
      type: e.entity_type,
    }))
    const ids = new Set(nodes.map((n) => n.id))
    const links: FGLink[] = kg.relations
      .filter((r) => ids.has(r.source) && ids.has(r.target))
      .map((r: KGRelation) => ({
        source: r.source,
        target: r.target,
        label: r.label,
        cross_modal: r.cross_modal,
        modality_pair: r.modality_pair,
        weight: r.weight,
      }))
    return { nodes, links }
  }, [kg])

  if (loadErr) {
    return (
      <div ref={containerRef} className="flex h-[520px] w-full items-center justify-center rounded-2xl border border-border/40 bg-surface-1 text-sm text-destructive">
        图谱引擎加载失败：{loadErr}
      </div>
    )
  }
  if (!FG2D || !kg) {
    return (
      <div ref={containerRef} className="flex h-[520px] w-full items-center justify-center rounded-2xl border border-border/40 bg-surface-1 text-xs text-muted-foreground">
        {kg ? '加载图谱引擎…' : '未加载知识图谱'}
      </div>
    )
  }

  const bg = isDark ? '#0b1220' : '#f8fafc'

  // 节点绘制（圆形 + 多模态外环 + 文字）
  const nodeCanvasObject = (node: unknown, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const n = node as FGNode & { x: number; y: number }
    const v = modalityVisual(n.primary_modality)
    const r = n.val
    const x = n.x ?? 0
    const y = n.y ?? 0
    const dimmed = selectedEntityId && selectedEntityId !== n.id

    ctx.globalAlpha = dimmed ? 0.3 : 1

    // 主体圆
    ctx.beginPath()
    ctx.arc(x, y, r, 0, 2 * Math.PI)
    ctx.fillStyle = v.color
    ctx.fill()

    // 外圈：多模态 entity 用渐变环表达
    if (n.modalities.length > 1) {
      const ringR = r + 2.5
      const segAngle = (2 * Math.PI) / n.modalities.length
      n.modalities.forEach((m, i) => {
        ctx.beginPath()
        ctx.arc(x, y, ringR, i * segAngle, (i + 1) * segAngle)
        ctx.lineWidth = 2
        ctx.strokeStyle = modalityVisual(m).color
        ctx.stroke()
      })
    } else {
      ctx.beginPath()
      ctx.arc(x, y, r + 1, 0, 2 * Math.PI)
      ctx.lineWidth = 1
      ctx.strokeStyle = v.accent
      ctx.stroke()
    }

    // 选中：发光环
    if (selectedEntityId === n.id) {
      ctx.beginPath()
      ctx.arc(x, y, r + 6, 0, 2 * Math.PI)
      ctx.lineWidth = 1.5
      ctx.strokeStyle = '#f59e0b'
      ctx.stroke()
    }

    // 标签
    if (globalScale > 0.7) {
      const fontSize = Math.max(10 / globalScale, 3)
      ctx.font = `600 ${fontSize}px "Inter", system-ui, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'
      ctx.fillStyle = isDark ? '#e2e8f0' : '#1f2937'
      const label = n.name.length > 14 ? `${n.name.slice(0, 14)}…` : n.name
      ctx.fillText(label, x, y + r + 4)
    }
    ctx.globalAlpha = 1
  }

  // 边绘制（跨模态边 → 虚线 + 双色渐变）
  const linkCanvasObject = (link: unknown, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const l = link as FGLink & { source: { x: number; y: number }; target: { x: number; y: number } }
    if (!l.source || !l.target || typeof l.source.x !== 'number') return
    const sx = l.source.x
    const sy = l.source.y
    const tx = l.target.x
    const ty = l.target.y

    if (l.cross_modal) {
      // 虚线 + 渐变：两端 modality 色
      const [ma, mb] = l.modality_pair ?? ['text', 'text']
      const ca = modalityVisual(ma).color
      const cb = modalityVisual(mb).color
      const grad = ctx.createLinearGradient(sx, sy, tx, ty)
      grad.addColorStop(0, ca)
      grad.addColorStop(1, cb)
      ctx.save()
      ctx.setLineDash([6, 4])
      ctx.lineWidth = 2.2
      ctx.strokeStyle = grad
      ctx.beginPath()
      ctx.moveTo(sx, sy)
      ctx.lineTo(tx, ty)
      ctx.stroke()
      ctx.restore()
    } else {
      ctx.lineWidth = 1
      ctx.strokeStyle = isDark ? 'rgba(148,163,184,0.4)' : 'rgba(100,116,139,0.45)'
      ctx.beginPath()
      ctx.moveTo(sx, sy)
      ctx.lineTo(tx, ty)
      ctx.stroke()
    }

    // 标签（缩放够大才画）
    if (globalScale > 1.1 && l.label) {
      const fontSize = Math.max(8 / globalScale, 2.5)
      ctx.font = `500 ${fontSize}px "Inter", system-ui, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillStyle = isDark ? 'rgba(226,232,240,0.85)' : 'rgba(51,65,85,0.85)'
      ctx.fillText(l.label, (sx + tx) / 2, (sy + ty) / 2)
    }
  }

  const Comp = FG2D as unknown as React.ComponentType<Record<string, unknown>>
  return (
    <div ref={containerRef} className="relative h-full min-h-[520px] w-full overflow-hidden rounded-2xl border border-border/40" style={{ background: bg }}>
      <Comp
        ref={graphRef}
        graphData={fgData}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor={bg}
        nodeCanvasObject={nodeCanvasObject}
        linkCanvasObject={linkCanvasObject}
        linkCanvasObjectMode={() => 'replace'}
        nodePointerAreaPaint={(node: unknown, color: string, ctx: CanvasRenderingContext2D) => {
          const n = node as FGNode & { x: number; y: number }
          ctx.beginPath()
          ctx.arc(n.x ?? 0, n.y ?? 0, (n.val ?? 6) + 4, 0, 2 * Math.PI)
          ctx.fillStyle = color
          ctx.fill()
        }}
        onNodeClick={(node: unknown) => {
          const n = node as FGNode
          onSelectEntity?.(n.id)
        }}
        onNodeRightClick={(node: unknown) => {
          const n = node as FGNode
          // 右键尝试跳转到 anchor segment（外层从 KG entity 解析）
          if (kg) {
            const ent = kg.entities.find((e) => e.entity_id === n.id)
            if (ent?.anchor_segment_id) {
              onJumpToSegment?.(ent.anchor_segment_id)
            }
          }
        }}
        onBackgroundClick={() => onSelectEntity?.(null)}
        linkDirectionalParticles={(l: unknown) => ((l as FGLink).cross_modal ? 3 : 0)}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.006}
        enableNodeDrag
        warmupTicks={50}
        cooldownTicks={120}
        d3AlphaDecay={0.025}
        d3VelocityDecay={0.3}
      />
      {/* 图例 */}
      <div className="pointer-events-none absolute right-3 top-3 rounded-xl border border-border/40 bg-background/85 p-2.5 text-[10px] shadow-sm backdrop-blur">
        <div className="mb-1 font-medium text-foreground">图例</div>
        <div className="space-y-1">
          {(['text', 'image', 'table', 'formula', 'seal'] as Modality[]).map((m) => {
            const v = modalityVisual(m)
            return (
              <div key={m} className="flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full" style={{ background: v.color }} />
                <span className="text-foreground/80">{v.label}</span>
              </div>
            )
          })}
          <div className="mt-1 border-t border-border/60 pt-1 text-foreground/70">
            <span className="inline-block h-[2px] w-4 align-middle" style={{ background: 'linear-gradient(90deg,#2563eb,#dc2626)', borderTop: '0' }} />
            <span className="ml-1.5 align-middle">跨模态边（虚线 + 渐变）</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CrossModalGraph
