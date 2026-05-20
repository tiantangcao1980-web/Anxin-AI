/**
 * RootGate —— "/" 根路由智能分发
 *
 * - 已登录 → /chat
 * - 未登录 → /site（官网落地页）
 *
 * 放在 `<Routes>` 的最顶层（在 /login 之前），React Router 优先匹配根 path="/"。
 * 任何 isAuthenticated 状态变化时立即重定向，不渲染中间态。
 */

import { Navigate } from 'react-router-dom'

import { useAuthStore } from '@/lib/store'

export function RootGate() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  return <Navigate to={isAuthenticated ? '/chat' : '/site'} replace />
}

export default RootGate
