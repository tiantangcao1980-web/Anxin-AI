/**
 * GraphLegend - 知识图谱浮动图例面板
 * 显示节点类型颜色映射（可点击切换可见性）+ 操作提示 + 统计
 */

import { useState } from 'react'
import { icons } from '@/lib/icons'
import { graphNodeColors } from '@/lib/design-tokens'

const LEGEND_ITEMS = [
  { type: '法规', char: '法', color: graphNodeColors.law },
  { type: '案例', char: '案', color: graphNodeColors.case },
  { type: '当事人', char: '当', color: graphNodeColors.party },
  { type: '机构', char: '机', color: graphNodeColors.organization },
  { type: '律师', char: '律', color: graphNodeColors.lawyer },
  { type: '其他', char: '其', color: graphNodeColors.other },
]

interface Props {
  nodeCount: number
  edgeCount: number
  viewMode: '2d' | '3d'
  activeTypes?: Set<string>
  onToggleType?: (type: string) => void
  onSelectAll?: () => void
  onClearAll?: () => void
}

export function GraphLegend({ nodeCount, edgeCount, activeTypes, onToggleType, onSelectAll, onClearAll }: Props) {
  const [collapsed, setCollapsed] = useState(false)

  const isInteractive = !!activeTypes && !!onToggleType

  return (
    <div className="rounded-xl border shadow-lg bg-background/90 backdrop-blur-md border-border text-foreground">
      <div className="flex items-center justify-between px-3 py-2">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex items-center gap-1.5 text-muted-foreground"
        >
          <icons.Layers className="w-3.5 h-3.5" />
          <span className="text-[10px] font-medium uppercase tracking-caption">图例</span>
          <icons.ChevronDown className={`w-3 h-3 transition-transform ${collapsed ? '-rotate-90' : ''}`} />
        </button>
        {!collapsed && (onSelectAll || onClearAll) && (
          <div className="flex gap-1.5">
            {onSelectAll && (
              <button onClick={onSelectAll} className="text-[9px] text-primary hover:underline">全选</button>
            )}
            {onSelectAll && onClearAll && <span className="text-[9px] text-muted-foreground">/</span>}
            {onClearAll && (
              <button onClick={onClearAll} className="text-[9px] text-muted-foreground hover:underline">清空</button>
            )}
          </div>
        )}
      </div>

      {!collapsed && (
        <div className="px-3 pb-3">
          <div className="space-y-1">
            {LEGEND_ITEMS.map(item => {
              const isActive = activeTypes ? activeTypes.has(item.type) : true
              return (
                <button
                  key={item.type}
                  onClick={() => onToggleType?.(item.type)}
                  disabled={!isInteractive}
                  className={`flex items-center gap-2 w-full rounded-md px-1.5 py-1 transition-all ${
                    isInteractive
                      ? 'hover:bg-muted cursor-pointer'
                      : 'cursor-default'
                  } ${isActive ? 'opacity-100' : 'opacity-40'}`}
                >
                  <div
                    className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-semibold text-white shadow-sm shrink-0 transition-opacity"
                    style={{ backgroundColor: item.color }}
                  >
                    {item.char}
                  </div>
                  <span className="text-[11px] flex-1 text-left text-foreground">{item.type}</span>
                  {isInteractive && (
                    <div className={`w-3 h-3 rounded border transition-colors flex items-center justify-center ${
                      isActive
                        ? 'border-primary bg-primary'
                        : 'border-border bg-background'
                    }`}>
                      {isActive && (
                        <icons.Check className="w-2 h-2 text-white" />
                      )}
                    </div>
                  )}
                </button>
              )
            })}
          </div>

          {/* 统计 */}
          <div className="mt-2.5 pt-2 border-t border-border flex gap-4">
            <div className="text-center flex-1">
              <div className="text-sm font-semibold text-foreground">{nodeCount}</div>
              <div className="text-[10px] text-muted-foreground">节点</div>
            </div>
            <div className="text-center flex-1">
              <div className="text-sm font-semibold text-foreground">{edgeCount}</div>
              <div className="text-[10px] text-muted-foreground">关系</div>
            </div>
          </div>

          {/* 操作提示 */}
          <div className="mt-2 pt-2 border-t border-border text-[10px] text-muted-foreground space-y-0.5">
            <p>左键点击 = 查看详情</p>
            <p>右键点击 = 展开关系</p>
            <p>滚轮 = 缩放 · 拖拽 = 平移</p>
          </div>
        </div>
      )}
    </div>
  )
}
