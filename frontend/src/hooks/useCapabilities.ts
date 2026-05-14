/**
 * useCapabilities — T8: 多端能力协商前端 hook
 *
 * 从后端 /harness/capability/negotiate 拉取当前 (platform, mode) 下:
 *   - 可用功能 (按 key 的 boolean map)
 *   - 不可用功能 (字符串列表, 含原因)
 *   - 可用任务类型
 *   - 警告 + 建议
 *
 * 用于:
 *   - ModeGate 替代硬编码的 checkModeAccess (后续 PR)
 *   - 桌面端 Tauri command 一致委托给云端 (避免本地 / 前端 / 服务三处独立判断)
 *
 * 设计原则:
 *   - 失败 fallback: API 调不通时返回 null + last-known-good (内存缓存), 不阻断 UI
 *   - 缓存: 同 (platform, mode) 5 分钟复用, 切换时 invalidate
 *   - 模式变更主动触发重拉
 */

import { useEffect, useState, useCallback, useRef } from 'react'
import { harnessGovernanceApi } from '@/lib/api'

export type PlatformType = 'web' | 'desktop' | 'mobile' | 'mini_program'
export type AppMode = 'cloud' | 'hybrid' | 'top_secret'

export interface NegotiateResult {
  platform: string
  mode: string
  available_features: Record<string, boolean>
  unavailable_features: string[]
  available_tasks: string[]
  warnings: string[]
  recommendations: string[]
}

const CACHE_TTL_MS = 5 * 60 * 1000
const cache = new Map<string, { ts: number; data: NegotiateResult }>()

function cacheKey(platform: PlatformType, mode: AppMode): string {
  return `${platform}::${mode}`
}

export interface UseCapabilitiesState {
  data: NegotiateResult | null
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * Hook: 拉取多端能力协商结果
 *
 * 示例:
 *   const { data, loading } = useCapabilities('web', currentPrivacyMode === 'cloud' ? 'cloud' : 'top_secret')
 *   const showLawyerMarket = data?.available_features['lawyer_market'] ?? true  // API 故障时默认放行
 */
export function useCapabilities(platform: PlatformType, mode: AppMode): UseCapabilitiesState {
  const [data, setData] = useState<NegotiateResult | null>(() => {
    const cached = cache.get(cacheKey(platform, mode))
    if (cached && Date.now() - cached.ts < CACHE_TTL_MS) return cached.data
    return null
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<boolean>(false)

  const fetchOnce = useCallback(async () => {
    abortRef.current = false
    setLoading(true)
    setError(null)
    try {
      const result = await harnessGovernanceApi.negotiateCapability({ platform, mode })
      if (abortRef.current) return
      cache.set(cacheKey(platform, mode), { ts: Date.now(), data: result as NegotiateResult })
      setData(result as NegotiateResult)
    } catch (err) {
      if (abortRef.current) return
      const msg = err instanceof Error ? err.message : String(err)
      setError(msg)
      // 失败时保留上一次成功的数据, 不清空
    } finally {
      if (!abortRef.current) setLoading(false)
    }
  }, [platform, mode])

  useEffect(() => {
    const cached = cache.get(cacheKey(platform, mode))
    if (cached && Date.now() - cached.ts < CACHE_TTL_MS) {
      setData(cached.data)
      return
    }
    fetchOnce()
    return () => {
      abortRef.current = true
    }
  }, [platform, mode, fetchOnce])

  return { data, loading, error, refresh: fetchOnce }
}

/**
 * 工具函数: 同步判断某个 feature key 是否可用
 *
 * 在 negotiate 数据尚未到达 / API 故障时, fallback 到 defaultAllowed (默认 true 放行)。
 */
export function isFeatureAllowed(
  capabilities: NegotiateResult | null,
  featureKey: string,
  defaultAllowed = true,
): boolean {
  if (!capabilities) return defaultAllowed
  if (featureKey in capabilities.available_features) {
    return capabilities.available_features[featureKey]
  }
  return defaultAllowed
}
