/**
 * Canvas 文本测量缓存 —— 借鉴 pretext "预处理+缓存"架构思想
 *
 * 解决知识图谱每帧 60fps × N节点 反复调用 ctx.font / ctx.measureText 的性能问题：
 * 1. measureAndCache: 缓存 (text, font) → width，避免重复 measureText
 * 2. truncateToWidth: 基于实际像素宽度的智能截断，替代朴素 slice(0, N)
 * 3. setFontIfChanged: 字体指纹比对，仅在字体变化时才设置 ctx.font
 * 4. LRU 淘汰防止内存泄漏
 */

const MAX_CACHE_SIZE = 2048

/** 宽度缓存: "font\0text" → number */
const widthCache = new Map<string, number>()

/** 截断结果缓存: "font\0text\0maxWidth" → string */
const truncCache = new Map<string, string>()

/** 离屏测量用 Canvas（惰性初始化） */
let _measureCtx: CanvasRenderingContext2D | null = null
let _currentFont = ''

function getMeasureCtx(): CanvasRenderingContext2D {
  if (!_measureCtx) {
    const canvas = document.createElement('canvas')
    canvas.width = 1
    canvas.height = 1
    _measureCtx = canvas.getContext('2d')!
  }
  return _measureCtx
}

function makeWidthKey(text: string, font: string): string {
  return font + '\0' + text
}

function makeTruncKey(text: string, font: string, maxWidth: number): string {
  return font + '\0' + text + '\0' + maxWidth
}

/** LRU 淘汰：超过上限时删除最早的 25% 条目 */
function evictIfNeeded(map: Map<string, any>) {
  if (map.size > MAX_CACHE_SIZE) {
    const deleteCount = MAX_CACHE_SIZE >> 2
    const iter = map.keys()
    for (let i = 0; i < deleteCount; i++) {
      const { value, done } = iter.next()
      if (done) break
      map.delete(value)
    }
  }
}

/**
 * 测量并缓存文本宽度
 * @returns 文本在指定字体下的像素宽度
 */
export function measureAndCache(text: string, font: string): number {
  const key = makeWidthKey(text, font)
  const cached = widthCache.get(key)
  if (cached !== undefined) return cached

  const ctx = getMeasureCtx()
  if (_currentFont !== font) {
    ctx.font = font
    _currentFont = font
  }
  const width = ctx.measureText(text).width
  widthCache.set(key, width)
  evictIfNeeded(widthCache)
  return width
}

/**
 * 基于实际像素宽度的智能截断
 * 中英文混排场景下远优于朴素 slice(0, N)
 * 使用二分查找加速定位截断点
 */
export function truncateToWidth(text: string, font: string, maxWidth: number): string {
  // 快速路径：全文不超宽
  const fullWidth = measureAndCache(text, font)
  if (fullWidth <= maxWidth) return text

  const key = makeTruncKey(text, font, maxWidth)
  const cached = truncCache.get(key)
  if (cached !== undefined) return cached

  // 省略号宽度
  const ellipsis = '\u2026'
  const ellipsisWidth = measureAndCache(ellipsis, font)
  const targetWidth = maxWidth - ellipsisWidth

  if (targetWidth <= 0) {
    truncCache.set(key, ellipsis)
    return ellipsis
  }

  // 二分查找截断点
  let lo = 0
  let hi = text.length
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    const w = measureAndCache(text.slice(0, mid), font)
    if (w <= targetWidth) {
      lo = mid
    } else {
      hi = mid - 1
    }
  }

  const result = lo > 0 ? text.slice(0, lo) + ellipsis : ellipsis
  truncCache.set(key, result)
  evictIfNeeded(truncCache)
  return result
}

/**
 * 仅在字体变化时才设置 ctx.font（避免浏览器每次重新解析字体字符串）
 * 返回当前追踪的字体值供外部保存
 */
export function setFontIfChanged(
  ctx: CanvasRenderingContext2D,
  font: string,
  lastFont: string,
): string {
  if (font !== lastFont) {
    ctx.font = font
  }
  return font
}

/** 清空全部缓存（可在图谱数据大规模变更时调用） */
export function clearMeasureCache() {
  widthCache.clear()
  truncCache.clear()
  _currentFont = ''
}
