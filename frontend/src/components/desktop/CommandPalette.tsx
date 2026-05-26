/**
 * CommandPalette — 飞书风 ⌘K 命令面板
 *
 * 触发：⌘K（macOS） / Ctrl+K（Windows/Linux）
 * 行为：屏幕上方居中浮层，560px 宽，分组结果（跳转/智能体/设置）
 *
 * 关联：DESIGN.md §10.7 / docs/plans/2026-05-22-desktop-bootstrap.md
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'

interface CommandItem {
  id: string
  group: string
  title: string
  desc?: string
  icon: keyof typeof icons
  action: () => void
  keywords?: string[]
}

interface CommandPaletteProps {
  open: boolean
  onClose: () => void
}

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [highlightedIndex, setHighlightedIndex] = useState(0)

  const allItems = useMemo<CommandItem[]>(
    () => [
      // 跳转
      { id: 'go-chat', group: '跳转', title: '智能对话', icon: 'MessageSquare', action: () => navigate('/chat') },
      { id: 'go-agents', group: '跳转', title: '智能体工作台', icon: 'LayoutGrid', action: () => navigate('/agents') },
      { id: 'go-tasks', group: '跳转', title: '任务中心', icon: 'ClipboardCheck', action: () => navigate('/v3/tasks') },
      { id: 'go-knowledge', group: '跳转', title: '法律智库', icon: 'BookOpen', action: () => navigate('/knowledge-base') },
      { id: 'go-settings', group: '跳转', title: '设置', icon: 'Settings', action: () => navigate('/settings') },
      { id: 'go-private-llm', group: '跳转', title: '配置 AI 模型', icon: 'Sparkles', action: () => navigate('/private-llm') },
      // 智能体（与 workbench 一致）
      { id: 'persona-anxin', group: '智能体', title: '安心助理', desc: '综合协调', icon: 'Bot', action: () => navigate('/v3/personas/anxin') },
      { id: 'persona-legal', group: '智能体', title: '法律顾问', desc: '合规经营', icon: 'Bot', action: () => navigate('/v3/personas/legal') },
      { id: 'persona-contract', group: '智能体', title: '合同管家', desc: '合规经营', icon: 'Bot', action: () => navigate('/v3/personas/contract') },
      { id: 'persona-finance', group: '智能体', title: '财税顾问', desc: '合规经营', icon: 'Bot', action: () => navigate('/v3/personas/finance') },
      { id: 'persona-market', group: '智能体', title: '市场研究员', desc: '增长获客', icon: 'Bot', action: () => navigate('/v3/personas/market') },
      // 设置
      { id: 'open-about', group: '设置', title: '关于 / 重新查看引导', icon: 'BookOpen', action: () => navigate('/settings?tab=about') },
      { id: 'open-mode', group: '设置', title: '隐私模式（本地/混合/云端）', icon: 'Lock', action: () => navigate('/settings?tab=workstation') },
    ],
    [navigate],
  )

  const filtered = useMemo(() => {
    if (!query.trim()) return allItems
    const q = query.toLowerCase()
    return allItems.filter(
      (item) =>
        item.title.toLowerCase().includes(q) ||
        item.desc?.toLowerCase().includes(q) ||
        item.group.toLowerCase().includes(q) ||
        item.keywords?.some((k) => k.toLowerCase().includes(q)),
    )
  }, [allItems, query])

  const grouped = useMemo(() => {
    const map = new Map<string, CommandItem[]>()
    filtered.forEach((item) => {
      const list = map.get(item.group) ?? []
      list.push(item)
      map.set(item.group, list)
    })
    return Array.from(map.entries())
  }, [filtered])

  const handleSelect = useCallback(
    (item: CommandItem) => {
      item.action()
      onClose()
      setQuery('')
      setHighlightedIndex(0)
    },
    [onClose],
  )

  // 键盘：↑↓ 移动，Enter 执行，Esc 关闭
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setHighlightedIndex((i) => Math.min(i + 1, filtered.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setHighlightedIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const item = filtered[highlightedIndex]
        if (item) handleSelect(item)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, filtered, highlightedIndex, handleSelect, onClose])

  // 打开时清空 query
  useEffect(() => {
    if (open) {
      setQuery('')
      setHighlightedIndex(0)
    }
  }, [open])

  if (!open) return null

  let flatIndex = -1

  return (
    <div
      role="dialog"
      aria-label="命令面板"
      className="fixed inset-0 z-50 bg-foreground/30 backdrop-blur-sm flex items-start justify-center pt-[20vh]"
      onClick={onClose}
    >
      <div
        className="bg-surface-1 rounded-xl border border-border shadow-float w-full max-w-[560px] max-h-[480px] overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 搜索框 */}
        <div className="flex items-center gap-2 px-4 h-12 border-b border-border">
          <icons.Search className="w-4 h-4 text-muted-foreground shrink-0" />
          <input
            type="text"
            autoFocus
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setHighlightedIndex(0)
            }}
            placeholder="搜索智能体、页面、设置…"
            className="flex-1 bg-transparent border-0 outline-none text-sm text-foreground placeholder:text-muted-foreground"
          />
          <kbd className="text-[10px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5">
            Esc
          </kbd>
        </div>

        {/* 结果列表 */}
        <div className="flex-1 overflow-y-auto py-2">
          {grouped.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">没有匹配项</div>
          ) : (
            grouped.map(([group, items]) => (
              <div key={group} className="mb-1">
                <div className="px-3 py-1 text-[10px] font-medium text-muted-foreground uppercase tracking-wider">
                  {group}
                </div>
                {items.map((item) => {
                  flatIndex++
                  const isActive = flatIndex === highlightedIndex
                  const Icon = icons[item.icon] as React.ComponentType<{ className?: string }>
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setHighlightedIndex(flatIndex)}
                      className={`w-full flex items-center gap-3 px-3 h-9 text-left ${
                        isActive ? 'bg-primary/10 text-primary' : 'hover:bg-surface-2'
                      }`}
                    >
                      <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                      <span className="flex-1 text-sm truncate text-foreground">{item.title}</span>
                      {item.desc && (
                        <span className="text-[11px] text-muted-foreground shrink-0">{item.desc}</span>
                      )}
                    </button>
                  )
                })}
              </div>
            ))
          )}
        </div>

        {/* 底部提示 */}
        <div className="h-8 border-t border-border bg-surface-2 px-3 flex items-center gap-3 text-[10px] text-muted-foreground">
          <span className="inline-flex items-center gap-1">
            <kbd className="font-mono border border-border rounded px-1 py-0.5 bg-surface-1">↑↓</kbd>
            移动
          </span>
          <span className="inline-flex items-center gap-1">
            <kbd className="font-mono border border-border rounded px-1 py-0.5 bg-surface-1">⏎</kbd>
            选择
          </span>
          <span className="inline-flex items-center gap-1">
            <kbd className="font-mono border border-border rounded px-1 py-0.5 bg-surface-1">Esc</kbd>
            关闭
          </span>
        </div>
      </div>
    </div>
  )
}

export default CommandPalette
