import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { defaultHome, isReturnToAllowed, useSession } from '../app/session'
import { Banner } from '../components/Banner'
import { Card } from '../components/Card'
import { HttpError } from '../lib/http'

export function Login() {
  const { login, user } = useSession()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const created = params.get('created') === '1'

  useEffect(() => {
    if (user) navigate(defaultHome(user.role), { replace: true })
  }, [user, navigate])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const me = await login(email, password)
      const returnTo = params.get('returnTo')
      const dest =
        returnTo && isReturnToAllowed(me.role, returnTo) ? returnTo : defaultHome(me.role)
      navigate(dest, { replace: true })
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'Sign in failed')
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-4 text-2xl font-semibold">Sign in</h1>
      {created && (
      <div className="mb-4">
        <Banner variant="success">Account created. Sign in to continue.</Banner>
      </div>
      )}
      <Card>
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <label className="text-sm">
            Email
            <input
              type="email"
              autoComplete="email"
              className="mt-1 w-full rounded-lg border border-control-border bg-surface px-3 py-2"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            Password
            <input
              type="password"
              autoComplete="current-password"
              className="mt-1 w-full rounded-lg border border-control-border bg-surface px-3 py-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </label>
          {error && <Banner variant="danger">{error}</Banner>}
          <button
            type="submit"
            className="rounded-lg bg-action px-4 py-2 text-on-action hover:opacity-90"
          >
            Sign in
          </button>
        </form>
        <p className="mt-4 text-sm text-muted">
          <Link to="/register" className="text-brand hover:underline">Create account</Link>
        </p>
      </Card>
    </div>
  )
}
