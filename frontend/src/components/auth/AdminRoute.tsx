import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/lib/store'
import { usePermission } from '@/hooks/usePermission'

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuthStore()
  const { isAdmin } = usePermission()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (!user || !isAdmin) {
    return <Navigate to="/chat" replace />
  }

  return <>{children}</>
}
