import type { ApiError } from './types'

let token: string | null = null
let onUnauthorized: (() => void) | null = null
let refreshInFlight: Promise<string | null> | null = null

const NO_REFRESH_PATHS = new Set([
  '/auth/login',
  '/auth/register',
  '/auth/refresh',
  '/auth/logout',
])

export function setAuthToken(t: string | null): void {
  token = t
}

export function setUnauthorizedHandler(fn: () => void): void {
  onUnauthorized = fn
}

export class HttpError extends Error {
  status: number
  code: string
  body: ApiError

  constructor(status: number, body: ApiError) {
    super(body.message)
    this.status = status
    this.code = body.code
    this.body = body
  }
}

function isApiErrorBody(data: unknown): data is ApiError {
  return (
    typeof data === 'object' &&
    data !== null &&
    'code' in data &&
    typeof (data as ApiError).code === 'string' &&
    'message' in data &&
    typeof (data as ApiError).message === 'string'
  )
}

export function isPendingApiResponse(status: number, data: unknown): boolean {
  if (status === 202) return true
  return isApiErrorBody(data) && data.code === 'OPERATION_PENDING'
}

export function apiErrorBody(data: unknown, res: Response): ApiError {
  if (isApiErrorBody(data)) return data
  if (res.status === 202) {
    return {
      code: 'OPERATION_PENDING',
      message: res.statusText || 'Operation pending',
    }
  }
  return { code: 'UNKNOWN', message: res.statusText || 'Request failed' }
}

export function isOperationPending(err: unknown): boolean {
  return (
    err instanceof HttpError &&
    (err.status === 202 || err.code === 'OPERATION_PENDING')
  )
}

async function parseResponse(res: Response): Promise<{ data: unknown }> {
  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { message: text }
    }
  }
  return { data }
}

async function refreshAccessToken(): Promise<string | null> {
  if (refreshInFlight) return refreshInFlight
  refreshInFlight = (async () => {
    try {
      const res = await fetch('/api/v1/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      })
      const { data } = await parseResponse(res)
      if (!res.ok) return null
      const body = data as { token?: string }
      if (!body.token) return null
      token = body.token
      return body.token
    } catch {
      return null
    } finally {
      refreshInFlight = null
    }
  })()
  return refreshInFlight
}

export async function api<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
  async function once(): Promise<{ res: Response; data: unknown }> {
    const headers = new Headers(init.headers)
    if (init.json !== undefined) {
      headers.set('Content-Type', 'application/json')
    }
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
    const res = await fetch(`/api/v1${path}`, {
      ...init,
      headers,
      credentials: 'include',
      body: init.json !== undefined ? JSON.stringify(init.json) : init.body,
    })
    const { data } = await parseResponse(res)
    return { res, data }
  }

  let { res, data } = await once()

  if (
    res.status === 401 &&
    !NO_REFRESH_PATHS.has(path) &&
    (data as ApiError | null)?.code === 'UNAUTHORIZED'
  ) {
    const newToken = await refreshAccessToken()
    if (newToken) {
      ;({ res, data } = await once())
    } else {
      token = null
      onUnauthorized?.()
    }
  }

  if (!res.ok || isPendingApiResponse(res.status, data)) {
    throw new HttpError(res.status, apiErrorBody(data, res))
  }
  return data as T
}

const AUDIT_UNAVAILABLE_MESSAGE =
  'Temporarily unavailable while audit evidence is checked.'

export function httpErrorMessage(err: unknown, fallback: string): string {
  if (isOperationPending(err)) return 'Confirmation pending'
  if (err instanceof HttpError && err.code === 'AUDIT_UNAVAILABLE') {
    return AUDIT_UNAVAILABLE_MESSAGE
  }
  return err instanceof HttpError ? err.message : fallback
}

export function httpErrorToastVariant(err: unknown): 'warning' | 'danger' {
  return err instanceof HttpError && err.code === 'AUDIT_UNAVAILABLE' ? 'warning' : 'danger'
}
