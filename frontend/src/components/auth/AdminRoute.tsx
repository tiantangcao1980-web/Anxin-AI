import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/lib/store'

export function AdminRoute({ children }: { children: React.ReactNode }) {
  const { user, isAuthenticated } = useAuthStore()

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}
