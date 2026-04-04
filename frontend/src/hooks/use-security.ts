/**
 * 安全初始化 Hook
 *
 * 在 App 入口调用，负责：
 * 1. 获取后端安全配置
 * 2. 初始化 HMAC 签名器
 * 3. 初始化浏览器指纹（Phase 2）
 * 4. 采集 Bot 信号（Phase 2）
 */

import { useEffect, useRef } from 'react'
import { setSigningKey, setHmacEnabled } from '../lib/security/hmac-signer'
import { initFingerprint } from '../lib/security/fingerprint'
import { collectBotSignals } from '../lib/security/bot-detection'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export function useSecurity() {
  const initialized = useRef(false)

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    async function init() {
      try {
        // 1. 获取安全配置
        const resp = await fetch(`${API_BASE}/auth/security-config`)
        if (!resp.ok) return

        const config = await resp.json()

        // 2. 初始化 HMAC
        if (config.hmac_enabled && config.public_signing_key) {
          setSigningKey(config.public_signing_key)
          setHmacEnabled(true)
        }

        // 3. 初始化指纹（Phase 2，如果启用）
        if (config.fingerprint_enabled) {
          initFingerprint()
        }

        // 4. 采集 Bot 信号（总是采集，后端决定是否使用）
        collectBotSignals()
      } catch {
        // 安全初始化失败不应影响应用正常使用
      }
    }

    init()
  }, [])
}
