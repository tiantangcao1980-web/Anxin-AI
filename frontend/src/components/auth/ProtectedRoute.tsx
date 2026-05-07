/**
 * ProtectedRoute - 路由守卫组件
 *
 * 检查用户是否已认证，未认证时重定向到登录页。
 * 支持页面刷新后通过启动阶段 silent refresh 恢复认证状态。
 * 检查 JWT token 是否过期，过期时清除认证状态并重定向。
 *
 * V2 架构：支持按 primary_client（needer/provider）分流路由
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/lib/store'
import { usePermission } from '@/hooks/usePermission'

type PrimaryClient = 'needer' | 'provider'

interface ProtectedRouteProps {
  children: React.ReactNode
  feature?: string
  fallbackPath?: string
  /**
   * V2: 限制路由仅对特定客户端类型可见
   * - 'provider' 用于 /pro/* 服务方端
   * - 'needer'   用于 / 需求方端
   * 未设置时不做客户端类型校验（保持兼容）
   */
  requirePrimaryClient?: PrimaryClient
}

const PROVIDER_ROLES = new Set([
  'lawyer',
  'partner',
  'paralegal',
  'platform_lawyer',
])

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

/**
 * V2: 推断用户的客户端类型
 * 优先使用显式的 primary_client 字段；老用户字段为空时按 role 推断
 */
function inferPrimaryClient(user: { role?: string; primary_client?: PrimaryClient } | null | undefined): PrimaryClient {
  if (user?.primary_client) {
    return user.primary_client
  }
  if (user?.role && PROVIDER_ROLES.has(user.role)) {
    return 'provider'
  }
  return 'needer'
}

export function ProtectedRoute({
  children,
  feature,
  fallbackPath,
  requirePrimaryClient,
}: ProtectedRouteProps) {
  const { token, user, logout } = useAuthStore()
  const location = useLocation()
  const { canAccess } = usePermission()

  const storedToken = token

  if (!storedToken || isTokenExpired(storedToken)) {
    if (storedToken) {
      logout()
    }
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  // V2: 客户端类型分流（优先于 feature 检查，避免错误降级）
  if (requirePrimaryClient) {
    const actual = inferPrimaryClient(user)
    if (actual !== requirePrimaryClient) {
      const homeForActual = actual === 'provider' ? '/pro/dashboard' : '/chat'
      return <Navigate to={homeForActual} replace />
    }
  }

  if (feature && !canAccess(feature)) {
    const fallback = fallbackPath ?? (requirePrimaryClient === 'provider' ? '/pro/dashboard' : '/chat')
    return <Navigate to={fallback} replace />
  }

  return <>{children}</>
}
