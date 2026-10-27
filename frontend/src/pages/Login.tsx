import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { defaultHome, isReturnToAllowed, useSession } from '../app/session'
import { useToast } from '../app/toast'
import { Banner } from '../components/Banner'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeading } from '../components/PageHeading'
import { TextField } from '../components/TextField'
import { HttpError } from '../lib/http'

export function Login() {
  const { login, user } = useSession()
  const { showToast } = useToast()
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
      const message = err instanceof HttpError ? err.message : 'Sign in failed'
      setError(message)
      showToast(message, 'danger')
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <PageHeading
        title="Welcome back."
        subtitle="Sign in to bid or manage your auctions."
      />
      {created && <Banner variant="success">Account created. Sign in to continue.</Banner>}
      <Card>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <TextField
            label="Email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <TextField
            label="Password"
            type="password"
            autoComplete="current-password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <Banner variant="danger">{error}</Banner>}
          <Button type="submit">Sign in</Button>
        </form>
        <p className="mt-4 text-sm text-muted">
          New here?{' '}
          <Link to="/register" className="text-brand hover:underline">Create account →</Link>
        </p>
      </Card>
      <p className="text-sm text-muted">
        <Link to="/" className="text-brand hover:underline">
          Back to auctions
        </Link>
      </p>
    </div>
  )
}
