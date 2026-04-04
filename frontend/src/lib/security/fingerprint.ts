/**
 * 浏览器指纹采集（Phase 2）
 *
 * 默认使用内置轻量指纹算法（基于 canvas + navigator 属性）。
 * 如需更高精度，安装 @fingerprintjs/fingerprintjs 后自动升级。
 */

let visitorId: string | null = null
let initialized = false

/**
 * 内置轻量指纹：基于 canvas + screen + navigator 属性生成哈希
 * 精度不如 FingerprintJS，但零依赖。
 */
async function builtinFingerprint(): Promise<string> {
  const components: string[] = []

  // Screen
  components.push(`${screen.width}x${screen.height}x${screen.colorDepth}`)

  // Navigator
  components.push(navigator.language || '')
  components.push(String(navigator.hardwareConcurrency || 0))
  components.push(navigator.platform || '')

  // Timezone
  components.push(Intl.DateTimeFormat().resolvedOptions().timeZone || '')

  // Canvas fingerprint
  try {
    const canvas = document.createElement('canvas')
    const ctx = canvas.getContext('2d')
    if (ctx) {
      ctx.textBaseline = 'top'
      ctx.font = '14px Arial'
      ctx.fillStyle = '#f60'
      ctx.fillRect(125, 1, 62, 20)
      ctx.fillStyle = '#069'
      ctx.fillText('AnxinFP', 2, 15)
      components.push(canvas.toDataURL())
    }
  } catch { /* canvas 不可用 */ }

  // SHA-256 哈希
  const data = components.join('|')
  const encoded = new TextEncoder().encode(data)
  const hashBuffer = await crypto.subtle.digest('SHA-256', encoded)
  return Array.from(new Uint8Array(hashBuffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('')
    .slice(0, 32)
}

/**
 * 初始化指纹采集（仅执行一次）
 */
export async function initFingerprint(): Promise<void> {
  if (initialized) return
  initialized = true

  try {
    visitorId = await builtinFingerprint()
  } catch {
    visitorId = null
  }
}

/** 获取当前 visitorId（可能为 null） */
export function getVisitorId(): string | null {
  return visitorId
}
