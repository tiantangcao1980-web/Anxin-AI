import { Navigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/lib/store'
import { usePermission } from '@/hooks/usePermission'

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return payload.exp * 1000 < Date.now()
  } catch {
    return true
  }
}

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, token, logout } = useAuthStore()
  const { isAdmin } = usePermission()
  const location = useLocation()
  const storedToken = token || localStorage.getItem('access_token')

  if (!storedToken || isTokenExpired(storedToken)) {
    if (storedToken) {
      logout()
    }
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }

  if (!user || !isAdmin) {
    return <Navigate to="/chat" replace />
  }

  return <>{children}</>
}
