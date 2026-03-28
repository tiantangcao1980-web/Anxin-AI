import { useEffect, useState, useCallback } from 'react'
import { useAuthStore } from '@/lib/store'
import { FEATURE_FLAGS } from './usePermission'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8003/api/v1'
const POLL_INTERVAL = 5 * 60 * 1000 // 5 min

let remoteFlags: Record<string, boolean> | null = null
let fetchPromise: Promise<void> | null = null
let lastFetchTime = 0

async function fetchRemoteFlags(): Promise<Record<string, boolean>> {
  const token = localStorage.getItem('access_token')
  if (!token) return {}
  const resp = await fetch(`${API_BASE_URL}/feature-flags`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!resp.ok) throw new Error('Failed to fetch feature flags')
  const json = await resp.json()
  return (json.data ?? json) as Record<string, boolean>
}

function loadFlags(): Promise<void> {
  const now = Date.now()
  if (remoteFlags && now - lastFetchTime < POLL_INTERVAL) {
    return Promise.resolve()
  }
  if (fetchPromise) return fetchPromise
  fetchPromise = fetchRemoteFlags()
    .then((data) => {
      remoteFlags = data
      lastFetchTime = Date.now()
    })
    .catch(() => {
      // fallback: keep existing or null
    })
    .finally(() => {
      fetchPromise = null
    })
  return fetchPromise
}

export function useFeatureFlags() {
  const { user } = useAuthStore()
  const [flags, setFlags] = useState<Record<string, boolean>>(remoteFlags ?? {})
  const [loading, setLoading] = useState(remoteFlags === null)

  const refresh = useCallback(async () => {
    remoteFlags = null
    lastFetchTime = 0
    setLoading(true)
    await loadFlags()
    setFlags(remoteFlags ?? {})
    setLoading(false)
  }, [])

  useEffect(() => {
    if (!user) return

    let cancelled = false
    loadFlags().then(() => {
      if (!cancelled) {
        setFlags(remoteFlags ?? {})
        setLoading(false)
      }
    })

    const timer = setInterval(() => {
      remoteFlags = null
      lastFetchTime = 0
      loadFlags().then(() => {
        if (!cancelled) setFlags(remoteFlags ?? {})
      })
    }, POLL_INTERVAL)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [user?.id])

  return { flags, loading, refresh }
}

export function useFeatureFlag(key: string): { enabled: boolean; loading: boolean } {
  const { flags, loading } = useFeatureFlags()

  if (loading && remoteFlags === null) {
    // still loading, fallback to local FEATURE_FLAGS
    const local = FEATURE_FLAGS[key]
    return { enabled: local === 'released' || local === 'beta', loading: true }
  }

  if (key in flags) {
    return { enabled: flags[key], loading }
  }

  // key not in remote, fallback to local
  const local = FEATURE_FLAGS[key]
  return { enabled: local === 'released' || local === 'beta', loading }
}
