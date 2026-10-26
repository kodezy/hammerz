import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useSession } from '../app/session'
import { Banner } from '../components/Banner'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { deposit, getWallet } from '../features/wallet'
import { HttpError } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'
import { clearPending, savePending } from '../lib/pending'

export function Wallet() {
  const { user } = useSession()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['wallet'], queryFn: getWallet, enabled: !!user })
  const [amount, setAmount] = useState('')
  const [msg, setMsg] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!user || user.role !== 'BIDDER') {
    return <p className="text-muted">Wallet is for bidders only.</p>
  }

  async function onDeposit(e: FormEvent) {
    e.preventDefault()
    if (!user) return
    setError(null)
    setMsg(null)
    const cents = parseDollarsToCents(amount)
    if (cents === null || cents <= 0) {
      setError('Enter a valid USD amount')
      return
    }
    const key = crypto.randomUUID()
    savePending(user.id, {
      key,
      method: 'POST',
      path: '/wallet/deposits',
      body: { amount_cents: cents },
      actorId: user.id,
      createdAt: new Date().toISOString(),
    })
    setPending(true)
    try {
      await deposit(cents, key)
      clearPending(user.id, key)
      setMsg('Funds added')
      setAmount('')
      await qc.invalidateQueries({ queryKey: ['wallet'] })
    } catch (err) {
      if (err instanceof HttpError && err.status === 202) {
        setError('Confirmation pending')
      } else {
        setError(err instanceof HttpError ? err.message : 'Deposit failed')
      }
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="mb-4 text-2xl font-semibold">Wallet</h1>
      {q.data?.confirmation_pending && <Banner variant="warning">Confirmation pending</Banner>}
      {q.isLoading && <p>Loading…</p>}
      {q.data && (
        <Card className="mb-4 space-y-2">
          <p>Total balance: <Money value={q.data.total} /></p>
          <p>Committed: <Money value={q.data.committed} /></p>
          <p className="font-medium">Available to bid: <Money value={q.data.available} /></p>
        </Card>
      )}
      <Card>
        <h2 className="mb-2 font-medium">Add funds</h2>
        <p className="mb-3 text-sm text-muted">No payment will be processed.</p>
        <form onSubmit={onDeposit} className="flex flex-col gap-2">
          <label className="text-sm">
            Amount (USD)
            <input
              className="mt-1 w-full rounded-lg border border-control-border px-3 py-2"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              disabled={pending}
            />
          </label>
          {error && <Banner variant="danger">{error}</Banner>}
          {msg && <Banner variant="success">{msg}</Banner>}
          <button
            type="submit"
            disabled={pending}
            className="rounded-lg bg-action px-4 py-2 text-on-action disabled:opacity-50"
          >
            Add funds
          </button>
        </form>
        {msg && (
          <Link to="/wallet" className="mt-3 inline-block text-brand hover:underline">
            Back to wallet
          </Link>
        )}
      </Card>
    </div>
  )
}
