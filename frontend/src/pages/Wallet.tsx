import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useSession } from '../app/session'
import { useToast } from '../app/toast'
import { Banner } from '../components/Banner'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { PageHeading } from '../components/PageHeading'
import { TextField } from '../components/TextField'
import { deposit, getWallet } from '../features/wallet'
import { lotListingTitle } from '../lib/lotCopy'
import { httpErrorMessage } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'
import { clearPending, listPending, savePending } from '../lib/pending'

export function Wallet() {
  const { user } = useSession()
  const { showToast } = useToast()
  const qc = useQueryClient()
  const q = useQuery({ queryKey: ['wallet'], queryFn: getWallet, enabled: !!user })
  const [amount, setAmount] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user || user.role !== 'BIDDER') return
    const rec = listPending(user.id).find((r) => r.path === '/wallet/deposits')
    if (!rec?.body || typeof rec.body !== 'object') return
    const cents = (rec.body as { amount_cents?: number }).amount_cents
    if (!cents) return
    setPending(true)
    deposit(cents, rec.key)
      .then(() => {
        clearPending(user.id, rec.key)
        showToast('Funds added')
        qc.invalidateQueries({ queryKey: ['wallet'] })
      })
      .catch((err) => {
        setError(httpErrorMessage(err, 'Deposit failed'))
      })
      .finally(() => setPending(false))
  }, [user, qc, showToast])

  if (!user || user.role !== 'BIDDER') {
    return <p className="text-muted">Wallet is for bidders only.</p>
  }

  async function onDeposit(e: FormEvent) {
    e.preventDefault()
    if (!user) return
    setError(null)
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
      showToast('Funds added')
      setAmount('')
      await qc.invalidateQueries({ queryKey: ['wallet'] })
    } catch (err) {
      setError(httpErrorMessage(err, 'Deposit failed'))
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="space-y-8">
      <PageHeading
        title="Your wallet"
        subtitle="USD balances for bidding"
      />
      {q.data?.confirmation_pending && <Banner variant="warning">Confirmation pending</Banner>}
      {q.isLoading && <p className="text-muted">Loading…</p>}
      {q.isError && <p className="text-danger">Could not load wallet.</p>}
      {q.data && (
        <div className="grid gap-4 md:grid-cols-3">
          <Card className="min-h-[180px]">
            <p className="text-sm text-muted">Total balance</p>
            <p className="mt-2 font-display text-3xl text-text">
              <Money value={q.data.total} />
            </p>
          </Card>
          <Card className="min-h-[180px]">
            <p className="text-sm text-muted">Committed</p>
            <p className="mt-2 font-display text-3xl text-text">
              <Money value={q.data.committed} />
            </p>
          </Card>
          <Card className="min-h-[180px]">
            <p className="text-sm text-muted">Available to bid</p>
            <p className="mt-2 font-display text-3xl text-text">
              <Money value={q.data.available} />
            </p>
          </Card>
        </div>
      )}
      {q.data?.commitments && q.data.commitments.length > 0 && (
        <Card>
          <h2 className="mb-1 font-semibold text-text">Current commitments</h2>
          <p className="mb-4 text-sm text-muted">
            Released when you are outbid or a lot is cancelled.
          </p>
          <ul className="divide-y divide-border">
            {q.data.commitments.map((c) => (
              <li
                key={c.auction_id}
                className="grid grid-cols-1 gap-1 py-3 text-sm sm:grid-cols-[1fr_auto] sm:items-center sm:gap-4"
              >
                <Link to={`/lots/${c.auction_id}`} className="text-brand hover:underline">
                  {lotListingTitle(c.display_no, c.title)}
                </Link>
                <span className="text-muted sm:text-right">
                  <Money value={c.reserved} /> reserved
                </span>
              </li>
            ))}
          </ul>
        </Card>
      )}
      <Card>
        <h2 className="mb-2 font-semibold text-text">Add funds</h2>
        <p className="mb-4 text-sm text-muted">
          Credits are added to your available balance. No payment will be processed.
        </p>
        <form onSubmit={onDeposit} className="max-w-xl space-y-4">
          <TextField
            label="Amount (USD)"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            disabled={pending}
          />
          {error && <Banner variant="danger">{error}</Banner>}
          <Button type="submit" disabled={pending} className="w-full sm:w-auto">
            Add funds
          </Button>
        </form>
      </Card>
    </div>
  )
}
