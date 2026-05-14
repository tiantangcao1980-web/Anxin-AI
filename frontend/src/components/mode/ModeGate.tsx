/**
 * ModeGate — 运行模式功能门控组件（V2 架构 + T8 后端能力协商）
 *
 * 用于包裹需要特定运行模式（本地/混合/云端）才能使用的功能。
 * 当前模式不满足时，显示友好引导提示，而不是直接阻断。
 *
 * 使用示例（保留向下兼容）：
 *   <ModeGate required="hybrid_or_cloud" feature="舆情监测">
 *     <SentimentMonitorPage />
 *   </ModeGate>
 *
 * T8 二阶段：当传入 ``featureKey`` 时会同步走后端 ``capability_negotiator``，
 * 后端判断优先级高于本地 ``checkModeAccess``（本地仅作 fallback / 0-RTT 预检）。
 *   <ModeGate required="hybrid_or_cloud" feature="舆情监测" featureKey="sentiment_monitor">
 *     <SentimentMonitorPage />
 *   </ModeGate>
 *
 * 支持的策略：
 *   - "any"           — 任何模式都能用（默认）
 *   - "hybrid_or_cloud" — 仅混合/云端（如舆情监测、找律师、IM）
 *   - "cloud_only"    — 仅云端（如跨会话 AI 训练）
 *   - "local_ok_with_download" — 本地可用，但需要先在云端下载数据包
 */

import { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { usePrivacy, PrivacyMode } from '@/context/PrivacyContext'
import { icons } from '@/lib/icons'
import { useCapabilities, isFeatureAllowed, type AppMode } from '@/hooks/useCapabilities'

export type ModeRequirement =
  | 'any'
  | 'hybrid_or_cloud'
  | 'cloud_only'
  | 'local_ok_with_download'

interface ModeGateProps {
  children: ReactNode
  required: ModeRequirement
  feature: string
  // 对于 local_ok_with_download 模式，检查数据包是否已下载
  hasLocalData?: boolean
  // 可选：自定义不可用时的提示
  fallback?: ReactNode
  /**
   * T8: 后端 capability_negotiator 的 feature key（如 "sentiment_monitor"）。
   * 传入后会调 /harness/capability/negotiate 取得后端判断,优先级高于本地 checkModeAccess。
   * 后端故障 / 加载中 / 未声明该 key 时, 回退到本地 checkModeAccess。
   */
  featureKey?: string
}

/**
 * T8: 把 PrivacyContext 的 PrivacyMode 映射到 capability_negotiator 的 AppMode。
 */
function privacyModeToAppMode(mode: PrivacyMode): AppMode {
  switch (mode) {
    case PrivacyMode.CLOUD:
      return 'cloud'
    case PrivacyMode.HYBRID:
      return 'hybrid'
    case PrivacyMode.LOCAL:
    default:
      return 'top_secret'
  }
}

/**
 * 检查当前模式是否满足要求
 */
export function checkModeAccess(
  currentMode: PrivacyMode,
  required: ModeRequirement,
  hasLocalData = false,
): { allowed: boolean; reason?: string } {
  switch (required) {
    case 'any':
      return { allowed: true }

    case 'hybrid_or_cloud':
      if (currentMode === PrivacyMode.LOCAL) {
        return {
          allowed: false,
          reason: '此功能需要云端服务支持（如舆情抓取、律师匹配、消息推送），请切换到混合模式或云端模式使用。',
        }
      }
      return { allowed: true }

    case 'cloud_only':
      if (currentMode !== PrivacyMode.CLOUD) {
        return {
          allowed: false,
          reason: '此功能仅在云端模式下可用，请切换到云端模式。',
        }
      }
      return { allowed: true }

    case 'local_ok_with_download':
      if (currentMode === PrivacyMode.LOCAL && !hasLocalData) {
        return {
          allowed: false,
          reason: '本地模式下使用此功能需要先下载数据包。请切换到混合或云端模式下载，下载后可在本地模式使用。',
        }
      }
      return { allowed: true }

    default:
      return { allowed: true }
  }
}

/**
 * 模式不满足时的默认 UI
 *
 * V2: 不再提供"一键 setMode"按钮——切换模式必须经过订阅检查（requestModeSwitch）。
 * 这里仅引导用户去设置页或订阅页，避免绕过订阅校验。
 */
function DefaultFallback({
  feature,
  reason,
  onGoToSettings,
}: {
  feature: string
  reason: string
  onGoToSettings: () => void
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center justify-center min-h-[50vh] sm:min-h-[60vh] p-6"
      role="alert"
      aria-live="polite"
    >
      <div className="max-w-md w-full bg-card border border-border rounded-xl shadow-sm p-6 text-center">
        <div className="w-14 h-14 mx-auto mb-4 rounded-full bg-warning/10 border border-warning/20 flex items-center justify-center">
          <icons.Lock className="w-6 h-6 text-warning" aria-hidden="true" />
        </div>
        <h3 className="text-lg font-semibold text-foreground mb-2">
          {feature}暂不可用
        </h3>
        <p className="text-sm text-muted-foreground leading-relaxed mb-5">
          {reason}
        </p>
        <div className="flex flex-col gap-2">
          <button
            onClick={onGoToSettings}
            className="w-full px-4 py-2.5 bg-primary text-primary-foreground text-sm font-medium rounded-lg hover:bg-primary/90 transition-colors"
          >
            前往设置切换模式
          </button>
          <button
            onClick={() => { window.location.href = '/pricing' }}
            className="w-full px-4 py-2.5 bg-transparent border border-border text-foreground text-sm font-medium rounded-lg hover:bg-muted transition-colors"
          >
            了解订阅方案
          </button>
        </div>
      </div>
    </motion.div>
  )
}

export function ModeGate({
  children,
  required,
  feature,
  hasLocalData = false,
  fallback,
  featureKey,
}: ModeGateProps) {
  const { mode } = usePrivacy()
  const navigate = useNavigate()
  const localCheck = checkModeAccess(mode, required, hasLocalData)

  // T8: 后端 capability_negotiator 判断 (仅在 featureKey 提供时启用)
  // 注意: Hook 必须无条件调用; featureKey 为空时仍调, 但忽略结果
  const { data: capabilities } = useCapabilities('web', privacyModeToAppMode(mode))

  let allowed = localCheck.allowed
  let reason = localCheck.reason

  if (featureKey && capabilities) {
    // 后端声明了该 feature → 用后端判断覆盖
    const backendKnowsFeature = featureKey in capabilities.available_features
    if (backendKnowsFeature) {
      allowed = isFeatureAllowed(capabilities, featureKey, true)
      if (!allowed) {
        // 后端在 warnings / unavailable_features 里通常有原因, 取第一条
        const unavailableMatch = capabilities.unavailable_features.find(s =>
          s.toLowerCase().includes(featureKey.toLowerCase()),
        )
        reason =
          unavailableMatch ||
          capabilities.warnings[0] ||
          localCheck.reason ||
          '当前运行模式下不可用 (后端能力协商)'
      }
    }
  }

  if (allowed) {
    return <>{children}</>
  }

  if (fallback) {
    return <>{fallback}</>
  }

  return (
    <DefaultFallback
      feature={feature}
      reason={reason || '当前运行模式下不可用'}
      onGoToSettings={() => {
        // V2 修复：不再直接 setMode（绕过订阅校验），跳到设置页让用户走 requestModeSwitch
        navigate('/settings?tab=privacy')
      }}
    />
  )
}

/**
 * 紧凑版 ModeGate — 用于按钮/小组件场景，不可用时显示灰态并禁用点击
 */
interface ModeGateInlineProps {
  required: ModeRequirement
  feature: string
  hasLocalData?: boolean
  children: (props: { disabled: boolean; reason?: string }) => ReactNode
}

export function ModeGateInline({
  required,
  feature: _feature,
  hasLocalData = false,
  children,
}: ModeGateInlineProps) {
  const { mode } = usePrivacy()
  const check = checkModeAccess(mode, required, hasLocalData)
  return <>{children({ disabled: !check.allowed, reason: check.reason })}</>
}
