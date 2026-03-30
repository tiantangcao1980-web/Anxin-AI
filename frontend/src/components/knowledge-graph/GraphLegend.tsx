/**
 * GraphLegend - 知识图谱浮动图例面板
 * 显示节点类型颜色映射 + 操作提示 + 统计
 */

import { useState } from 'react'
import { icons } from '@/lib/icons'

const LEGEND_ITEMS = [
  { type: '法规', char: '法', color: '#22c55e' },
  { type: '案例', char: '案', color: '#3b82f6' },
  { type: '当事人', char: '当', color: '#f59e0b' },
  { type: '机构', char: '机', color: '#8b5cf6' },
  { type: '律师', char: '律', color: '#ec4899' },
  { type: '其他', char: '其', color: '#6b7280' },
]

interface Props {
  nodeCount: number
  edgeCount: number
  viewMode: '2d' | '3d'
}

export function GraphLegend({ nodeCount, edgeCount, viewMode }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const dark = viewMode === '3d'

  const panelCls = dark
    ? 'bg-slate-900/80 backdrop-blur-md border-slate-700 text-slate-300'
    : 'bg-background/90 backdrop-blur-sm border-border text-muted-foreground'

  return (
    <div className={`rounded-xl border shadow-lg ${panelCls}`}>
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center justify-between w-full px-3 py-2"
      >
        <div className="flex items-center gap-1.5">
          <icons.Layers className="w-3.5 h-3.5" />
          <span className="text-[10px] font-bold uppercase tracking-wider">图例</span>
        </div>
        <icons.ChevronDown className={`w-3 h-3 transition-transform ${collapsed ? '-rotate-90' : ''}`} />
      </button>

      {!collapsed && (
        <div className="px-3 pb-3">
          <div className="space-y-1.5">
            {LEGEND_ITEMS.map(item => (
              <div key={item.type} className="flex items-center gap-2">
                <div
                  className="w-5 h-5 rounded-full flex items-center justify-center text-[9px] font-bold text-white shadow-sm"
                  style={{ backgroundColor: item.color }}
                >
                  {item.char}
                </div>
                <span className="text-[11px]">{item.type}</span>
              </div>
            ))}
          </div>

          {/* 统计 */}
          <div className={`mt-2.5 pt-2 border-t flex gap-4 ${dark ? 'border-slate-700' : 'border-border'}`}>
            <div className="text-center flex-1">
              <div className={`text-sm font-bold ${dark ? 'text-white' : 'text-foreground'}`}>{nodeCount}</div>
              <div className="text-[10px]">节点</div>
            </div>
            <div className="text-center flex-1">
              <div className={`text-sm font-bold ${dark ? 'text-white' : 'text-foreground'}`}>{edgeCount}</div>
              <div className="text-[10px]">关系</div>
            </div>
          </div>

          {/* 操作提示 */}
          <div className={`mt-2 pt-2 border-t text-[10px] space-y-0.5 ${dark ? 'border-slate-700 text-slate-500' : 'border-border'}`}>
            <p>左键点击 = 查看详情</p>
            <p>右键点击 = 展开关系</p>
            <p>滚轮 = 缩放 · 拖拽 = 平移</p>
          </div>
        </div>
      )}
    </div>
  )
}
