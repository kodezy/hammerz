import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../app/session'
import { Banner } from '../components/Banner'
import { Card } from '../components/Card'
import { register } from '../features/auth'
import { HttpError } from '../lib/http'

export function Register() {
  const { user } = useSession()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user) navigate('/', { replace: true })
  }, [user, navigate])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      await register(email, password)
      navigate('/login?returnTo=/wallet&created=1', { replace: true })
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'Registration failed')
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-4 text-2xl font-semibold">Create account</h1>
      <Card>
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <label className="text-sm">
            Email
            <input
              type="email"
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
              className="mt-1 w-full rounded-lg border border-control-border bg-surface px-3 py-2"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </label>
          {error && <Banner variant="danger">{error}</Banner>}
          <button type="submit" className="rounded-lg bg-action px-4 py-2 text-on-action">
            Create account
          </button>
        </form>
        <p className="mt-4 text-sm">
          <Link to="/login" className="text-brand hover:underline">Sign in</Link>
        </p>
      </Card>
    </div>
  )
}
