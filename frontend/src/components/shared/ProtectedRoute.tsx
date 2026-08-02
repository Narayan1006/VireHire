import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'
import type { ReactNode } from 'react'

interface ProtectedRouteProps {
  children: ReactNode
}

/**
 * Redirects unauthenticated users to /login.
 * When authDisabled (local dev without Supabase), lets everyone through.
 */
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, authDisabled } = useAuth()
  const location = useLocation()

  // Still checking stored token — show nothing briefly
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-cream">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-ink border-t-transparent" />
      </div>
    )
  }

  // Auth is disabled (local dev) — allow through
  if (authDisabled) return <>{children}</>

  // Authenticated — allow through
  if (isAuthenticated) return <>{children}</>

  // Not authenticated — redirect to login, preserving the target URL
  return <Navigate to="/login" state={{ from: location }} replace />
}
