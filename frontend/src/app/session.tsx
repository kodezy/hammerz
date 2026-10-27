import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { api, HttpError, setAuthToken, setUnauthorizedHandler } from '../lib/http'
import type { Role, User } from '../lib/types'

type SessionState = {
  user: User | null
  login: (email: string, password: string) => Promise<User>
  logout: () => void
}

const SessionContext = createContext<SessionState | null>(null)

const TOKEN_KEY = 'hammerz:token'

function readStoredToken(): string | null {
  try {
    return sessionStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

function writeStoredToken(value: string | null): void {
  try {
    if (value) sessionStorage.setItem(TOKEN_KEY, value)
    else sessionStorage.removeItem(TOKEN_KEY)
  } catch {
    /* ignore quota / private mode */
  }
}

const BIDDER_PATHS = ['/', '/wallet', '/my-wins', '/lots']
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
  const [token, setToken] = useState<string | null>(() => {
    const stored = readStoredToken()
    if (stored) setAuthToken(stored)
    return stored
  })

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    setAuthToken(null)
    writeStoredToken(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null)
      setUser(null)
      setAuthToken(null)
      writeStoredToken(null)
    })
  }, [])

  useEffect(() => {
    if (!token) {
      setUser(null)
      setAuthToken(null)
      return
    }
    setAuthToken(token)
    let cancelled = false
    api<User>('/auth/me')
      .then((me) => {
        if (!cancelled) setUser(me)
      })
      .catch((err) => {
        if (!cancelled && err instanceof HttpError && err.status === 401) logout()
      })
    return () => {
      cancelled = true
    }
  }, [token, logout])

  const login = useCallback(async (email: string, password: string) => {
    const res = await api<{ token: string }>('/auth/login', {
      method: 'POST',
      json: { email, password },
    })
    setToken(res.token)
    setAuthToken(res.token)
    writeStoredToken(res.token)
    const me = await api<User>('/auth/me')
    setUser(me)
    return me
  }, [])

  const value = useMemo(
    () => ({ user, login, logout }),
    [user, login, logout],
  )

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionState {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('SessionProvider missing')
  return ctx
}
