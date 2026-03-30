/**
 * GraphToolbar - 知识图谱浮动控制工具栏
 * 2D/3D 切换 + 视图控制按钮
 */

import { icons } from '@/lib/icons'

interface Props {
  viewMode: '2d' | '3d'
  onViewModeChange: (mode: '2d' | '3d') => void
  showLabels: boolean
  onToggleLabels: () => void
  autoRotate: boolean
  onToggleAutoRotate: () => void
  onResetView: () => void
  onZoomToFit: () => void
}

export function GraphToolbar({
  viewMode, onViewModeChange, showLabels, onToggleLabels,
  autoRotate, onToggleAutoRotate, onResetView, onZoomToFit,
}: Props) {
  const dark = viewMode === '3d'

  const panelCls = dark
    ? 'bg-slate-900/80 backdrop-blur-md border-slate-700'
    : 'bg-background/90 backdrop-blur-sm border-border'

  const btnBase = (active?: boolean) => dark
    ? active ? 'bg-primary text-primary-foreground' : 'text-slate-400 hover:text-white hover:bg-slate-800'
    : active ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-muted'

  return (
    <div className="flex flex-col gap-2">
      {/* 2D/3D 切换 */}
      <div className={`flex gap-0.5 p-0.5 rounded-lg border shadow-lg ${panelCls}`}>
        <button
          onClick={() => onViewModeChange('2d')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
            viewMode === '2d' ? (dark ? 'bg-slate-700 text-white' : 'bg-background text-primary shadow-sm') : (dark ? 'text-slate-400' : 'text-muted-foreground')
          }`}
        >
          <icons.Grid3x3 className="w-3.5 h-3.5" />
          2D
        </button>
        <button
          onClick={() => onViewModeChange('3d')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
            viewMode === '3d' ? (dark ? 'bg-slate-700 text-white' : 'bg-background text-primary shadow-sm') : (dark ? 'text-slate-400' : 'text-muted-foreground')
          }`}
        >
          <icons.Box className="w-3.5 h-3.5" />
          3D
        </button>
      </div>

      {/* 控制按钮 */}
      <div className={`flex flex-col gap-1 rounded-xl border shadow-lg p-1.5 ${panelCls}`}>
        <CtrlBtn icon={icons.RotateCcw} label="重置视角" onClick={onResetView} dark={dark} />
        <CtrlBtn icon={icons.Focus} label="适应画面" onClick={onZoomToFit} dark={dark} />
        {viewMode === '3d' && (
          <CtrlBtn icon={icons.Focus} label={autoRotate ? '停止旋转' : '自动旋转'} onClick={onToggleAutoRotate} active={autoRotate} dark={dark} />
        )}
        <CtrlBtn icon={icons.Eye} label={showLabels ? '隐藏标签' : '显示标签'} onClick={onToggleLabels} active={showLabels} dark={dark} />
      </div>
    </div>
  )
}

function CtrlBtn({ icon: Icon, label, onClick, active, dark }: {
  icon: any; label: string; onClick: () => void; active?: boolean; dark?: boolean
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`p-2 rounded-lg transition-all ${
        dark
          ? active ? 'bg-primary text-primary-foreground' : 'text-slate-400 hover:text-white hover:bg-slate-800'
          : active ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      <Icon className="w-4 h-4" />
    </button>
  )
}
