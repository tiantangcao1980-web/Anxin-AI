/**
 * ProtectedRoute - 路由守卫组件
 *
 * 检查用户是否已认证，未认证时重定向到登录页。
 * 支持页面刷新后通过 localStorage 恢复认证状态。
 * 检查 JWT token 是否过期，过期时清除认证状态并重定向。
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/lib/store'
import { usePermission } from '@/hooks/usePermission'

interface ProtectedRouteProps {
  children: React.ReactNode
  feature?: string
  fallbackPath?: string
}

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

export function ProtectedRoute({
  children,
  feature,
  fallbackPath = '/chat',
}: ProtectedRouteProps) {
  const { token, logout } = useAuthStore()
  const location = useLocation()
  const { canAccess } = usePermission()

  const storedToken = token || localStorage.getItem('access_token')

  if (!storedToken || isTokenExpired(storedToken)) {
    // Token missing or expired — clear state and redirect
    if (storedToken) {
      logout()
    }
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (feature && !canAccess(feature)) {
    return <Navigate to={fallbackPath} replace />
  }

  return <>{children}</>
}
