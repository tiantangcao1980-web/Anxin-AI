/**
 * ModalityWeightSlider — 5 个模态权重滑块（V3 P13-D）
 *
 * 用户可调 text/image/table/formula/seal 5 个模态权重，影响 query 的 retrieval ranking。
 * 滑块 0~1，每个模态独立调，不强制 sum=1（后端做归一化）。
 *
 * UX 亮点：
 *   - 每行：emoji + 模态名 + 权重数字 + 滑块（颜色与 modalityStyle 同步）
 *   - 顶部"重置"按钮，回到默认权重
 */

import { icons } from '@/lib/icons'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'

import { useRagStore } from '@/lib/store/ragStore'
import { MODALITIES, modalityVisual } from './modalityStyle'

export function ModalityWeightSlider() {
  const weights = useRagStore((s) => s.modalityWeights)
  const setModalityWeights = useRagStore((s) => s.setModalityWeights)
  const resetModalityWeights = useRagStore((s) => s.resetModalityWeights)

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-medium text-foreground">模态权重</p>
          <p className="text-[11px] text-muted-foreground">调高某模态权重，检索更偏向该类型片段</p>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={resetModalityWeights}
          iconLeft={<icons.RotateCcw className="h-3.5 w-3.5" />}
          className="h-7 px-2 text-[11px]"
        >
          重置
        </Button>
      </div>

      <div className="space-y-2.5">
        {MODALITIES.map((m) => {
          const v = modalityVisual(m)
          const value = weights[m]
          return (
            <div key={m} className="flex items-center gap-3">
              <div className="flex w-20 shrink-0 items-center gap-1.5">
                <span aria-hidden>{v.emoji}</span>
                <span className={`text-[11px] font-medium ${v.text}`}>{v.label}</span>
              </div>
              <Slider
                value={[value]}
                onValueChange={(arr) => setModalityWeights({ [m]: arr[0] })}
                min={0}
                max={1}
                step={0.05}
                className="flex-1"
                aria-label={`${v.label} 权重`}
              />
              <span className="w-10 shrink-0 text-right text-[11px] tabular-nums text-foreground/80">
                {value.toFixed(2)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ModalityWeightSlider
