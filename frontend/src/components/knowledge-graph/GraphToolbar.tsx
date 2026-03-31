/**
 * GraphToolbar - 知识图谱浮动控制工具栏
 * 2D/3D 切换 + 视图控制按钮，跟随系统深色/浅色模式
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
  return (
    <div className="flex flex-col gap-2">
      {/* 2D/3D 切换 */}
      <div className="flex gap-0.5 p-0.5 rounded-lg border shadow-lg bg-background/90 backdrop-blur-md border-border">
        <button
          onClick={() => onViewModeChange('2d')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
            viewMode === '2d'
              ? 'bg-primary/10 text-primary shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}
        >
          <icons.Grid3x3 className="w-3.5 h-3.5" />
          2D
        </button>
        <button
          onClick={() => onViewModeChange('3d')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
            viewMode === '3d'
              ? 'bg-primary/10 text-primary shadow-sm'
              : 'text-muted-foreground hover:text-foreground hover:bg-muted'
          }`}
        >
          <icons.Box className="w-3.5 h-3.5" />
          3D
        </button>
      </div>

      {/* 控制按钮 */}
      <div className="flex flex-col gap-1 rounded-xl border shadow-lg p-1.5 bg-background/90 backdrop-blur-md border-border">
        <CtrlBtn icon={icons.RotateCcw} label="重置视角" onClick={onResetView} />
        <CtrlBtn icon={icons.Focus} label="适应画面" onClick={onZoomToFit} />
        {viewMode === '3d' && (
          <CtrlBtn icon={icons.RefreshCw} label={autoRotate ? '停止旋转' : '自动旋转'} onClick={onToggleAutoRotate} active={autoRotate} />
        )}
        <CtrlBtn icon={icons.Eye} label={showLabels ? '隐藏标签' : '显示标签'} onClick={onToggleLabels} active={showLabels} />
      </div>
    </div>
  )
}

function CtrlBtn({ icon: Icon, label, onClick, active }: {
  icon: any; label: string; onClick: () => void; active?: boolean
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`p-2 rounded-lg transition-all ${
        active
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:text-foreground hover:bg-muted'
      }`}
    >
      <Icon className="w-4 h-4" />
    </button>
  )
}
