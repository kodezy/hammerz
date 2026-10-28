import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, setAuthToken, setUnauthorizedHandler } from '../lib/http'
import type { Role, User } from '../lib/types'

type SessionState = {
  user: User | null
  ready: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => void
}

const SessionContext = createContext<SessionState | null>(null)

const BIDDER_PATHS = ['/', '/wallet', '/bids', '/lots']
const SELLER_PATHS = ['/', '/seller', '/lots']

export function isReturnToAllowed(role: Role | null, path: string): boolean {
  if (!path.startsWith('/') || path.startsWith('//')) return false
  if (path.startsWith('/login') || path.startsWith('/register')) return false
  if (role === 'SELLER') {
    return SELLER_PATHS.some((p) => path === p || path.startsWith(`${p}/`))
  }
  if (role === 'BIDDER') {
    return BIDDER_PATHS.some((p) => path === p || path.startsWith(`${p}/`))
  }
  return path === '/' || path.startsWith('/lots/') || path.startsWith('/receipts/')
}

export function defaultHome(role: Role | null): string {
  if (role === 'SELLER') return '/seller'
  return '/'
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  const clearSession = useCallback(() => {
    setUser(null)
    setAuthToken(null)
  }, [])

  const logout = useCallback(() => {
    void api<null>('/auth/logout', { method: 'POST' }).catch(() => {})
    clearSession()
  }, [clearSession])

  useEffect(() => {
    setUnauthorizedHandler(clearSession)
  }, [clearSession])

  useEffect(() => {
    let cancelled = false
    api<{ token: string }>('/auth/refresh', { method: 'POST' })
      .then(async (res) => {
        setAuthToken(res.token)
        const me = await api<User>('/auth/me')
        if (!cancelled) setUser(me)
      })
      .catch(() => {
        /* anonymous default; do not clearSession — races with in-flight login */
      })
      .finally(() => {
        if (!cancelled) setReady(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api<{ token: string }>('/auth/login', {
      method: 'POST',
      json: { email, password },
    })
    setAuthToken(res.token)
    const me = await api<User>('/auth/me')
    setUser(me)
    return me
  }, [])

  const value = useMemo(
    () => ({ user, ready, login, logout }),
    [user, ready, login, logout],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('SessionProvider missing')
  return ctx
}
