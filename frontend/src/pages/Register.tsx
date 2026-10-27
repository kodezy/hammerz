import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useSession } from '../app/session'
import { Banner } from '../components/Banner'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { PageHeading } from '../components/PageHeading'
import { TextField } from '../components/TextField'
import { register } from '../features/auth'
import { HttpError } from '../lib/http'

export function Register() {
  const { user } = useSession()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (user) navigate('/', { replace: true })
  }, [user, navigate])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError('Passwords do not match')
      return
    }
    try {
      await register(email, password)
      navigate('/login?created=1', { replace: true })
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'Registration failed')
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-6">
      <PageHeading
        title="Create your account."
        subtitle="Register to place bids on live lots."
      />
      <Card>
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <TextField
            label="Email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <TextField
            label="Password"
            type="password"
            placeholder="Create a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          <p className="text-xs text-muted">At least 8 characters.</p>
          <TextField
            label="Confirm password"
            type="password"
            placeholder="Re-enter your password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
            minLength={8}
          />
          {error && <Banner variant="danger">{error}</Banner>}
          <Button type="submit">Create account</Button>
        </form>
        <p className="mt-4 text-sm text-muted">
          Already have an account?{' '}
          <Link to="/login" className="text-brand hover:underline">Sign in →</Link>
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
