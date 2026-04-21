import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import AsyncStorage from '@react-native-async-storage/async-storage'

/**
 * 移动端三态运行模式。与 Web / Desktop 端的 `AppMode` 对齐：
 *
 * - LOCAL   完全离线：所有数据留在设备内，不外发。
 *   移动端受本地模型可用性限制，默认仅当 LLM_BASE_URL 是同网段 Ollama 时启用。
 * - HYBRID  混合：本地敏感 + 云端算力；受 ModeGate 控制的功能（律师/尽调/RTC）启用。
 * - CLOUD   云端：所有功能完整可用。
 *
 * 切换模式时会：
 * - 写入 AsyncStorage（冷启动恢复）
 * - 触发 modeGate 事件（订阅方根据需要重连 / 关断 / 提示）
 */

export type PrivacyMode = 'local' | 'hybrid' | 'cloud'

const STORAGE_KEY = 'anxin-privacy-mode'

interface PrivacyContextValue {
  mode: PrivacyMode
  hydrated: boolean
  setMode: (m: PrivacyMode) => Promise<void>
  /**
   * 判断给定功能在当前模式下是否允许使用。
   * 与 Web 端 `ModeGate` 的 `required` 取值保持一致：
   * - 'any'                     任何模式允许
   * - 'hybrid_or_cloud'          混合 / 云端允许
   * - 'cloud_only'               仅云端允许
   * - 'local_ok_with_download'   本地需要先下载数据包（移动端暂视同 hybrid_or_cloud）
   */
  canUseFeature: (required: 'any' | 'hybrid_or_cloud' | 'cloud_only' | 'local_ok_with_download') => boolean
}

const PrivacyContext = createContext<PrivacyContextValue | null>(null)

export function PrivacyProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<PrivacyMode>('cloud')
  const [hydrated, setHydrated] = useState(false)

  useEffect(() => {
    const hydrate = async () => {
      try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY)
        if (stored === 'local' || stored === 'hybrid' || stored === 'cloud') {
          setModeState(stored)
        }
      } catch {
        // 读失败用默认 cloud
      } finally {
        setHydrated(true)
      }
    }
    hydrate()
  }, [])

  const setMode = async (next: PrivacyMode) => {
    setModeState(next)
    try {
      await AsyncStorage.setItem(STORAGE_KEY, next)
    } catch {
      // 持久化失败不阻塞 UI
    }
  }

  const canUseFeature: PrivacyContextValue['canUseFeature'] = (required) => {
    if (required === 'any') return true
    if (required === 'cloud_only') return mode === 'cloud'
    if (required === 'hybrid_or_cloud') return mode !== 'local'
    if (required === 'local_ok_with_download') {
      // 移动端没有本地数据包下载渠道，暂同 hybrid_or_cloud
      return mode !== 'local'
    }
    return true
  }

  const value = useMemo<PrivacyContextValue>(
    () => ({ mode, hydrated, setMode, canUseFeature }),
    // canUseFeature 是纯函数，依赖 mode
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [mode, hydrated],
  )

  return <PrivacyContext.Provider value={value}>{children}</PrivacyContext.Provider>
}

export function usePrivacy(): PrivacyContextValue {
  const ctx = useContext(PrivacyContext)
  if (!ctx) {
    throw new Error('usePrivacy 必须在 PrivacyProvider 内使用')
  }
  return ctx
}
