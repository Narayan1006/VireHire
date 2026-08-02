/**
 * VeriHire — Auth Context
 *
 * Stores the JWT and user info in localStorage.
 * Provides login(), signup(), logout() to all children.
 * When SUPABASE_URL is not set on the backend, auth endpoints return 501 —
 * in that case the context falls back to an unauthenticated dev state and
 * the dashboard remains accessible without logging in.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const TOKEN_KEY = 'vh_access_token'
const USER_KEY = 'vh_user'

export interface AuthUser {
  id: string
  email: string
}

interface AuthContextValue {
  user: AuthUser | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => void
  /** true when backend has no Supabase configured — auth is optional */
  authDisabled: boolean
}

const AuthContext = createContext<AuthContextValue | null>(null)

async function callAuth(
  path: string,
  body: object,
): Promise<{ access_token: string; user: { id: string; email: string } }> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (res.status === 501) {
    // Backend has no Supabase configured — auth is disabled
    throw Object.assign(new Error('AUTH_DISABLED'), { status: 501 })
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const json = await res.json()
      detail = json?.detail || detail
    } catch {
      // ignore
    }
    throw new Error(detail)
  }

  return res.json()
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(
    () => localStorage.getItem(TOKEN_KEY),
  )
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? (JSON.parse(raw) as AuthUser) : null
    } catch {
      return null
    }
  })
  const [isLoading, setIsLoading] = useState(false)
  const [authDisabled, setAuthDisabled] = useState(false)

  const persist = (t: string, u: AuthUser) => {
    localStorage.setItem(TOKEN_KEY, t)
    localStorage.setItem(USER_KEY, JSON.stringify(u))
    setToken(t)
    setUser(u)
  }

  const clear = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }

  // On mount: verify stored token is still valid
  useEffect(() => {
    if (!token) return
    fetch(`${BASE_URL}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (res) => {
        if (res.status === 501) { setAuthDisabled(true); return }
        if (!res.ok) clear()
      })
      .catch(() => {
        // network error — keep token, will retry later
      })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const data = await callAuth('/api/auth/login', { email, password })
      persist(data.access_token, { id: data.user.id, email: data.user.email })
    } catch (err) {
      if ((err as { status?: number }).status === 501) setAuthDisabled(true)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const signup = useCallback(async (email: string, password: string) => {
    setIsLoading(true)
    try {
      const data = await callAuth('/api/auth/signup', { email, password })
      persist(data.access_token, { id: data.user.id, email: data.user.email })
    } catch (err) {
      if ((err as { status?: number }).status === 501) setAuthDisabled(true)
      throw err
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    clear()
    // Fire-and-forget server-side logout
    if (token) {
      fetch(`${BASE_URL}/api/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {})
    }
  }, [token])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      isAuthenticated: !!token || authDisabled,
      isLoading,
      login,
      signup,
      logout,
      authDisabled,
    }),
    [user, token, authDisabled, isLoading, login, signup, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
