import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useSession } from '../app/session'
import { Banner } from '../components/Banner'
import { Card } from '../components/Card'
import { Clock } from '../components/Clock'
import { Money } from '../components/Money'
import {
  cancelLot,
  getAuction,
  listBids,
  participantStatus,
  placeBid,
} from '../features/lots'
import { HttpError } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'
import { connectLotSocket } from '../lib/ws'
import { savePending, clearPending } from '../lib/pending'

export function Lot() {
  const { id = '' } = useParams()
  const { user } = useSession()
  const qc = useQueryClient()
  const auctionQ = useQuery({
    queryKey: ['auction', id],
    queryFn: () => getAuction(id),
  })
  const bidsQ = useQuery({
    queryKey: ['bids', id],
    queryFn: () => listBids(id),
  })
  const posQ = useQuery({
    queryKey: ['position', id],
    queryFn: () => participantStatus(id),
    enabled: !!user && user.role === 'BIDDER',
  })
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [showCancel, setShowCancel] = useState(false)

  useEffect(() => {
    if (!id) return
    const sock = connectLotSocket(
      id,
      () => {
        qc.invalidateQueries({ queryKey: ['auction', id] })
        qc.invalidateQueries({ queryKey: ['bids', id] })
        if (user?.role === 'BIDDER') {
          qc.invalidateQueries({ queryKey: ['position', id] })
          qc.invalidateQueries({ queryKey: ['wallet'] })
        }
      },
      () => qc.invalidateQueries({ queryKey: ['auction', id] }),
    )
    return () => sock.close()
  }, [id, qc, user?.role])

  const a = auctionQ.data
  const position = posQ.data?.position

  async function onBid(e: FormEvent) {
    e.preventDefault()
    if (!user || user.role !== 'BIDDER') return
    setError(null)
    const cents = parseDollarsToCents(amount)
    if (!cents) {
      setError('Invalid bid amount')
      return
    }
    const key = crypto.randomUUID()
    savePending(user.id, {
      key,
      method: 'POST',
      path: `/auctions/${id}/bids`,
      body: { amount_cents: cents },
      actorId: user.id,
      createdAt: new Date().toISOString(),
    })
    setPending(true)
    try {
      await placeBid(id, cents, key)
      clearPending(user.id, key)
      setAmount('')
      await qc.invalidateQueries({ queryKey: ['auction', id] })
      await qc.invalidateQueries({ queryKey: ['bids', id] })
      await qc.invalidateQueries({ queryKey: ['position', id] })
      await qc.invalidateQueries({ queryKey: ['wallet'] })
    } catch (err) {
      if (err instanceof HttpError && err.status === 202) {
        setError('Confirmation pending')
      } else {
        setError(err instanceof HttpError ? err.message : 'Bid failed')
      }
    } finally {
      setPending(false)
    }
  }

  async function onCancel() {
    if (!user || user.role !== 'SELLER') return
    const key = crypto.randomUUID()
    try {
      await cancelLot(id, cancelReason || null, key)
      setShowCancel(false)
      await qc.invalidateQueries({ queryKey: ['auction', id] })
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'Cancel failed')
    }
  }

  if (auctionQ.isLoading) return <p>Loading…</p>
  if (!a) return <p className="text-danger">Lot not found.</p>

  const item = a.item as { title: string; artist: string | null; image_url: string | null }
  const isOwner = user?.role === 'SELLER'
  const canBid =
    user?.role === 'BIDDER' &&
    a.display_status === 'LIVE' &&
    position !== 'LEADING'

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted">
        Lot {String(a.display_no).padStart(3, '0')}
      </p>
      <h1 className="text-2xl font-semibold">{item.title}</h1>
      <p className="text-muted">{item.artist ?? 'Not stated'}</p>
      {isOwner && <Banner variant="info">You own this lot</Banner>}
      {a.confirmation_pending && <Banner variant="warning">Confirmation pending</Banner>}
      <div className="grid gap-4 md:grid-cols-2">
        <div className="flex min-h-64 items-center justify-center rounded-xl bg-brand-soft p-4">
          {item.image_url ? (
            <img src={item.image_url} alt="" className="max-h-80 w-full object-contain" />
          ) : (
            <span className="text-muted">No image</span>
          )}
        </div>
        <Card className="space-y-3">
          <p>
            Status: <strong>{a.display_status}</strong>
          </p>
          <Clock
            endsAt={a.ends_at}
            serverTime={a.server_time}
            displayStatus={a.display_status}
            onElapsed={() => qc.invalidateQueries({ queryKey: ['auction', id] })}
          />
          <p>
            Current bid:{' '}
            <Money value={(a.current_bid as { cents: number; currency: 'USD' }) ?? a.opening_bid} />
          </p>
          <p className="text-sm text-muted">
            Minimum increment: <Money value={a.minimum_increment as { cents: number; currency: 'USD' }} />
          </p>
          {position === 'NOT_PARTICIPATING' && user?.role === 'BIDDER' && (
            <Banner variant="info">Place your first bid</Banner>
          )}
          {position === 'OUTBID' && <Banner variant="warning">You have been outbid</Banner>}
          {position === 'LEADING' && (
            <button type="button" disabled className="w-full rounded-lg border px-4 py-2 opacity-70">
              You are already leading
            </button>
          )}
          {canBid && (
            <form onSubmit={onBid} className="space-y-2">
              <input
                className="w-full rounded-lg border border-control-border px-3 py-2"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="Bid amount (USD)"
                disabled={pending}
              />
              {error && <Banner variant="danger">{error}</Banner>}
              <button
                type="submit"
                disabled={pending}
                className="w-full rounded-lg bg-action py-2 text-on-action disabled:opacity-50"
              >
                Place bid
              </button>
            </form>
          )}
          {isOwner && a.display_status !== 'CANCELLED' && (
            <div>
              {!showCancel ? (
                <button
                  type="button"
                  className="text-sm text-danger hover:underline"
                  onClick={() => setShowCancel(true)}
                >
                  Cancel lot
                </button>
              ) : (
                <div className="space-y-2 border-t border-border pt-3">
                  <label className="block text-sm">
                    Public cancellation reason (optional)
                    <textarea
                      className="mt-1 w-full rounded-lg border border-control-border px-3 py-2"
                      value={cancelReason}
                      onChange={(e) => setCancelReason(e.target.value)}
                    />
                  </label>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      className="rounded-lg border px-3 py-2"
                      onClick={() => setShowCancel(false)}
                    >
                      Keep auction
                    </button>
                    <button
                      type="button"
                      className="rounded-lg bg-danger px-3 py-2 text-on-action"
                      onClick={onCancel}
                    >
                      Confirm cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
          <Link to={`/lots/${id}/audit`} className="text-sm text-brand hover:underline">
            View public audit
          </Link>
        </Card>
      </div>
      <section>
        <h2 className="mb-2 font-medium">Bid history</h2>
        <ul className="space-y-1 text-sm">
          {bidsQ.data?.items.map((b) => (
            <li key={b.sequence}>
              #{b.sequence} {b.bidder_alias} — <Money value={{ cents: b.amount_cents, currency: 'USD' }} />
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
