/**
 * useLlmStatus — 共享 LLM 配置状态 hook
 *
 * 用法：
 *   const { status, loading, refresh } = useLlmStatus()
 *   if (loading) return <Spinner/>
 *   if (!status?.configured) return <LlmRequiredPlaceholder/>
 *
 * 关联：docs/plans/2026-05-22-desktop-bootstrap.md §4.3
 */

import { useCallback, useEffect, useState } from 'react'
import { checkLlmStatus, type LlmStatus } from '@/lib/llm-status'

export interface UseLlmStatusResult {
  status: LlmStatus | null
  loading: boolean
  refresh: () => Promise<void>
}

export function useLlmStatus(): UseLlmStatusResult {
  const [status, setStatus] = useState<LlmStatus | null>(null)
  const [loading, setLoading] = useState<boolean>(true)

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const next = await checkLlmStatus()
      setStatus(next)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    void checkLlmStatus()
      .then((next) => {
        if (active) setStatus(next)
      })
      .catch(() => {
        if (active) setStatus(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return { status, loading, refresh }
}

export default useLlmStatus
