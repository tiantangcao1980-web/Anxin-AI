/**
 * [CREAO 自愈闭环 Slice 1] 前端错误上报
 *
 * 职责：
 *   - 把 ErrorBoundary 捕获的 JS 错误上报到后端 /incidents/report
 *   - 5 分钟内同一指纹（hash(error.message + stack[:100])）只上报 1 次
 *   - 任意上报失败必须静默，绝不能影响错误页面显示
 */
import type { ErrorInfo } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
const DEDUPE_TTL_MS = 5 * 60 * 1000 // 5 分钟
const DEDUPE_KEY_PREFIX = 'incident-report:dedupe:'
const SESSION_ID_KEY = 'incident-report:session-id'

/** 生成简易 hash（FNV-1a 32 位变体），不依赖 crypto，浏览器同步可用 */
function fnv1a(input: string): string {
  let hash = 0x811c9dc5
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i)
    hash = (hash + ((hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24))) >>> 0
  }
  return hash.toString(16).padStart(8, '0')
}

/** 取或生成 session_id（仅本会话内有效） */
function getOrCreateSessionId(): string {
  try {
    const existing = sessionStorage.getItem(SESSION_ID_KEY)
    if (existing) return existing
    const generated =
      typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    sessionStorage.setItem(SESSION_ID_KEY, generated)
    return generated
  } catch {
    return `sess-${Date.now()}`
  }
}

/** 检查 + 写入去重指纹；返回 true 表示需要上报（首次或已过期） */
function shouldReport(fingerprint: string): boolean {
  try {
    const key = DEDUPE_KEY_PREFIX + fingerprint
    const raw = sessionStorage.getItem(key)
    const now = Date.now()
    if (raw) {
      const ts = Number(raw)
      if (Number.isFinite(ts) && now - ts < DEDUPE_TTL_MS) {
        return false
      }
    }
    sessionStorage.setItem(key, String(now))
    return true
  } catch {
    // sessionStorage 不可用时（隐私模式 / SSR）：默认放行，避免漏报
    return true
  }
}

/**
 * 上报前端错误到 /incidents/report
 * - 调用方应用 try/catch 包裹（双保险）
 * - Promise 永远 resolve，不抛错；rejected 只在调用方主动 .catch 时出现
 */
export async function reportFrontendError(
  error: Error,
  _info?: ErrorInfo,
): Promise<void> {
  try {
    const message = error?.message || ''
    const stack = error?.stack || ''
    const fingerprint = fnv1a(message + '|' + stack.slice(0, 100))

    if (!shouldReport(fingerprint)) {
      return
    }

    const name = error?.name || 'Error'
    const titlePrefix = `${name}: ${message}`.slice(0, 80)

    const payload = {
      source: 'frontend_error',
      title: titlePrefix,
      message,
      stack,
      url: typeof window !== 'undefined' ? window.location.href : '',
      user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
      session_id: getOrCreateSessionId(),
    }

    // 用裸 fetch（绕过 api.ts 的 401 跳转 / PoW 等副作用，错误上报应轻量）
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    try {
      const token = localStorage.getItem('access_token')
      if (token) headers['Authorization'] = `Bearer ${token}`
    } catch {
      /* 忽略 */
    }

    await fetch(`${API_BASE_URL}/incidents/report`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(() => {
      /* 网络错误静默 */
    })
  } catch {
    /* 任意异常都吞掉 —— 上报永远不能让用户看不到错误页面 */
  }
}
