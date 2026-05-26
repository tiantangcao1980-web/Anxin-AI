/**
 * LlmNotConfiguredBanner — 全局"未配置 LLM"横幅
 *
 * 行为：
 *  - mount 后调 checkLlmStatus；configured = false 时显示
 *  - "配置模型"按钮跳到 /private-llm
 *  - "关闭"按钮 → localStorage 暂存 24h，本周期不再弹（但配置后会重新检测）
 *  - 用户配置完成后（任意 LLM 设默认）下次刷新自动消失
 *
 * 风格：DESIGN §10.6 "系统提示" — warning/10 底 + 左 4px brand 色条，不抢主视觉
 * 关联：docs/plans/2026-05-22-desktop-bootstrap.md §4.4
 */

import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { icons } from '@/lib/icons'
import { checkLlmStatus, type LlmStatus } from '@/lib/llm-status'

const DISMISS_KEY = 'anxin.llm-banner.dismissedAt'
const DISMISS_DURATION_MS = 24 * 60 * 60 * 1000 // 24 小时

function isDismissed(): boolean {
  try {
    const raw = localStorage.getItem(DISMISS_KEY)
    if (!raw) return false
    const ts = Number(raw)
    return Number.isFinite(ts) && Date.now() - ts < DISMISS_DURATION_MS
  } catch {
    return false
  }
}

function rememberDismiss(): void {
  try {
    localStorage.setItem(DISMISS_KEY, String(Date.now()))
  } catch {
    // localStorage 不可用时静默
  }
}

export function LlmNotConfiguredBanner() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<LlmStatus | null>(null)
  const [dismissed, setDismissed] = useState<boolean>(() => isDismissed())

  useEffect(() => {
    let active = true
    checkLlmStatus()
      .then((s) => {
        if (active) setStatus(s)
      })
      .catch(() => {
        // 检测失败时不显示 banner，避免接口出错误导用户
        if (active) setStatus(null)
      })
    return () => {
      active = false
    }
  }, [])

  if (dismissed) return null
  if (!status) return null
  if (status.configured) return null

  return (
    <div
      role="status"
      aria-live="polite"
      className="border-l-4 border-l-warning border-y border-r border-warning/30 bg-warning/10 px-4 py-3 flex items-center gap-3 text-sm"
    >
      <icons.AlertTriangle className="w-5 h-5 text-warning shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="font-medium text-foreground">还未配置 AI 模型</p>
        <p className="text-muted-foreground text-xs mt-0.5">
          需要配置至少一个 LLM（OpenAI / 通义 / DeepSeek / Ollama 等）才能使用智能对话和工作台。
        </p>
      </div>
      <button
        type="button"
        onClick={() => navigate('/private-llm')}
        className="px-3 h-8 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary-600 transition-colors flex items-center gap-1.5 shrink-0"
      >
        配置模型
        <icons.ArrowRight className="w-3.5 h-3.5" />
      </button>
      <button
        type="button"
        onClick={() => {
          rememberDismiss()
          setDismissed(true)
        }}
        className="p-1.5 rounded-md hover:bg-warning/20 transition-colors shrink-0"
        aria-label="关闭提示（24 小时内不再显示）"
      >
        <icons.X className="w-4 h-4 text-muted-foreground" />
      </button>
    </div>
  )
}

export default LlmNotConfiguredBanner
