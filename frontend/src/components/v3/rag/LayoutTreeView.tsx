/**
 * LayoutTreeView — 文档章/条/款/项层级树（V3 P13-D）
 *
 * 直接根据 Segment[] 中的 parent_segment_id + layout_level 构建树。
 * 父-子关系不存在时降级为 layout_path 字符串切分（兜底）。
 *
 * 极简实现：受控 expanded set，点击节点回调上层。
 */

import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

import type { Segment } from '@/lib/api/rag'
import { modalityVisual } from './modalityStyle'

interface TreeNode {
  segment: Segment
  children: TreeNode[]
}

function buildTree(segments: Segment[]): TreeNode[] {
  const byId = new Map<string, TreeNode>()
  segments.forEach((s) => byId.set(s.segment_id, { segment: s, children: [] }))

  const roots: TreeNode[] = []
  segments.forEach((s) => {
    const node = byId.get(s.segment_id)!
    if (s.parent_segment_id && byId.has(s.parent_segment_id)) {
      byId.get(s.parent_segment_id)!.children.push(node)
    } else {
      roots.push(node)
    }
  })
  return roots
}

interface NodeRowProps {
  node: TreeNode
  depth: number
  expandedIds: Set<string>
  onToggle: (id: string) => void
  selectedId: string | null
  onSelect: (id: string) => void
}

function NodeRow({ node, depth, expandedIds, onToggle, selectedId, onSelect }: NodeRowProps) {
  const v = modalityVisual(node.segment.modality)
  const hasChildren = node.children.length > 0
  const expanded = expandedIds.has(node.segment.segment_id)
  const selected = selectedId === node.segment.segment_id

  const indent = depth * 12

  // 展示文案：layout_path 末段 优先；否则取 content 摘要
  const lastSeg = node.segment.layout_path?.split(/[\s/]/).pop() ?? ''
  const display = lastSeg || node.segment.content.slice(0, 40)

  return (
    <li>
      <button
        type="button"
        onClick={() => {
          onSelect(node.segment.segment_id)
          if (hasChildren) onToggle(node.segment.segment_id)
        }}
        style={{ paddingLeft: 8 + indent }}
        className={`group flex w-full items-center gap-1.5 rounded-md py-1 pr-2 text-left text-xs transition-colors ${
          selected ? 'bg-primary/10 text-primary' : 'hover:bg-muted/60 text-foreground/80'
        }`}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="h-3 w-3 shrink-0 opacity-60" />
          ) : (
            <ChevronRight className="h-3 w-3 shrink-0 opacity-60" />
          )
        ) : (
          <span className="h-3 w-3 shrink-0" aria-hidden />
        )}
        <span aria-hidden className="text-[10px]">
          {v.emoji}
        </span>
        <span className="truncate">{display}</span>
      </button>
      {hasChildren && expanded && (
        <ul className="space-y-0.5">
          {node.children.map((child) => (
            <NodeRow
              key={child.segment.segment_id}
              node={child}
              depth={depth + 1}
              expandedIds={expandedIds}
              onToggle={onToggle}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </ul>
      )}
    </li>
  )
}

export interface LayoutTreeViewProps {
  segments: Segment[]
  selectedId?: string | null
  onSelect?: (segmentId: string) => void
}

export function LayoutTreeView({ segments, selectedId = null, onSelect }: LayoutTreeViewProps) {
  const tree = useMemo(() => buildTree(segments), [segments])
  const [expandedIds, setExpandedIds] = useState<Set<string>>(
    () => new Set(segments.filter((s) => (s.layout_level ?? 0) <= 1).map((s) => s.segment_id)),
  )

  const toggle = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  if (segments.length === 0) {
    return (
      <p className="px-3 py-4 text-xs text-muted-foreground">尚无 layout segments</p>
    )
  }

  return (
    <ul className="space-y-0.5 py-1">
      {tree.map((root) => (
        <NodeRow
          key={root.segment.segment_id}
          node={root}
          depth={0}
          expandedIds={expandedIds}
          onToggle={toggle}
          selectedId={selectedId}
          onSelect={(id) => onSelect?.(id)}
        />
      ))}
    </ul>
  )
}

export default LayoutTreeView
