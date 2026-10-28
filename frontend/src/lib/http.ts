import type { ApiError } from './types'

let token: string | null = null
let onUnauthorized: (() => void) | null = null

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

export async function api<T>(
  path: string,
  init: RequestInit & { json?: unknown } = {},
): Promise<T> {
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
    body: init.json !== undefined ? JSON.stringify(init.json) : init.body,
  })
  const text = await res.text()
  let data: unknown = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = { message: text }
    }
  }
  if (res.status === 401 && token) {
    token = null
    onUnauthorized?.()
  }
  if (!res.ok) {
    const body = (data ?? { code: 'UNKNOWN', message: res.statusText }) as ApiError
    throw new HttpError(res.status, body)
  }
  return data as T
}

const AUDIT_UNAVAILABLE_MESSAGE =
  'Temporarily unavailable while audit evidence is checked.'

export function httpErrorMessage(err: unknown, fallback: string): string {
  if (err instanceof HttpError && err.code === 'AUDIT_UNAVAILABLE') {
    return AUDIT_UNAVAILABLE_MESSAGE
  }
  return err instanceof HttpError ? err.message : fallback
}

export function httpErrorToastVariant(err: unknown): 'warning' | 'danger' {
  return err instanceof HttpError && err.code === 'AUDIT_UNAVAILABLE' ? 'warning' : 'danger'
}
