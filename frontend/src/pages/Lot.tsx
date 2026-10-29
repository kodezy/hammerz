import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { useSession } from '../app/session'
import { useToast } from '../app/toast'
import { Banner } from '../components/Banner'
import { Button, ButtonLink } from '../components/Button'
import { TextAreaField, TextField } from '../components/TextField'
import { Card } from '../components/Card'
import { Clock } from '../components/Clock'
import { StatusBadge } from '../components/StatusBadge'
import { Money } from '../components/Money'
import {
  cancelLot,
  getAuction,
  listBids,
  participantStatus,
  placeBid,
  type AuctionSummary,
  type BidRow,
} from '../features/lots'
import { getWallet } from '../features/wallet'
import {
  leaderLine,
  lotArtworkLine,
  minimumBidLine,
} from '../lib/lotCopy'
import { sellerCanCancel } from '../lib/display'
import { httpErrorMessage } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'
import { clearPending, listPending, savePending } from '../lib/pending'
import { formatBidTimestamp, formatEndsLine } from '../lib/time'
import { connectLotSocket } from '../lib/ws'

export function Lot() {
  const { id = '' } = useParams()
  const { user } = useSession()
  const { showToast } = useToast()
  const qc = useQueryClient()
  const auctionQ = useQuery({
    queryKey: ['auction', id],
    queryFn: () => getAuction(id),
  })
  const walletQ = useQuery({
    queryKey: ['wallet'],
    queryFn: getWallet,
    enabled: !!user && user.role === 'BIDDER',
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
  const [olderBids, setOlderBids] = useState<BidRow[]>([])
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  const [cancelPending, setCancelPending] = useState(false)
  const [cancelReason, setCancelReason] = useState('')
  const [showCancel, setShowCancel] = useState(false)
  const [wsConnected, setWsConnected] = useState(true)

  const refreshLot = useCallback(() => {
    qc.invalidateQueries({ queryKey: ['auction', id] })
    qc.invalidateQueries({ queryKey: ['bids', id] })
    if (user?.role === 'BIDDER') {
      qc.invalidateQueries({ queryKey: ['position', id] })
      qc.invalidateQueries({ queryKey: ['wallet'] })
    }
  }, [id, qc, user?.role])

  useEffect(() => {
    if (!id) return
    const sock = connectLotSocket(
      id,
      () => refreshLot(),
      () => refreshLot(),
      (connected) => setWsConnected(connected),
    )
    return () => sock.close()
  }, [id, refreshLot])

  useEffect(() => {
    if (!id) return
    const onVisible = () => {
      if (document.visibilityState !== 'visible') return
      refreshLot()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => document.removeEventListener('visibilitychange', onVisible)
  }, [id, refreshLot])

  useEffect(() => {
    if (!user) return
    const records = listPending(user.id).filter((r) => r.path.includes(`/auctions/${id}/`))
    if (records.length === 0) return

    if (user.role === 'BIDDER') {
      const rec = records.find((r) => r.method === 'POST' && r.path.endsWith('/bids'))
      if (rec?.body && typeof rec.body === 'object') {
        const body = rec.body as { amount_cents?: number }
        if (body.amount_cents) {
          setPending(true)
          placeBid(id, body.amount_cents, rec.key)
            .then(() => {
              clearPending(user.id, rec.key)
              refreshLot()
            })
            .catch((err) => {
              setError(httpErrorMessage(err, 'Bid failed'))
            })
            .finally(() => setPending(false))
        }
      }
    }

    if (user.role === 'SELLER') {
      const rec = records.find((r) => r.method === 'POST' && r.path.endsWith('/cancel'))
      if (rec) {
        const body =
          rec.body && typeof rec.body === 'object'
            ? (rec.body as { reason?: string | null })
            : { reason: null }
        setCancelPending(true)
        cancelLot(id, body.reason ?? null, rec.key)
          .then(() => {
            clearPending(user.id, rec.key)
            setShowCancel(false)
            refreshLot()
          })
          .catch((err) => {
            setError(httpErrorMessage(err, 'Cancel failed'))
          })
          .finally(() => setCancelPending(false))
      }
    }
  }, [id, user, refreshLot])

  const a = auctionQ.data
  const position = posQ.data?.position
  const bidItems = [...(bidsQ.data?.items ?? []), ...olderBids]
  const oldestSequence =
    bidItems.length > 0 ? Math.min(...bidItems.map((b) => b.sequence)) : undefined

  async function onBid(e: FormEvent) {
    e.preventDefault()
    if (!user || user.role !== 'BIDDER' || !wsConnected) return
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
      refreshLot()
    } catch (err) {
      setError(httpErrorMessage(err, 'Bid failed'))
    } finally {
      setPending(false)
    }
  }

  async function loadEarlier() {
    if (!oldestSequence || loadingOlder) return
    setLoadingOlder(true)
    try {
      const page = await listBids(id, oldestSequence)
      const existing = new Set(bidItems.map((b) => b.sequence))
      setOlderBids((prev) => [...prev, ...page.items.filter((b) => !existing.has(b.sequence))])
    } catch {
      showToast('Could not load earlier bids', 'danger')
    } finally {
      setLoadingOlder(false)
    }
  }

  async function onCancel() {
    if (!user || user.role !== 'SELLER') return
    const bidCount = Number(auctionQ.data?.bid_count ?? 0)
    if (bidCount > 0 && cancelReason.trim().length < 10) {
      setError('Cancellation reason required (at least 10 characters)')
      return
    }
    const key = crypto.randomUUID()
    const reason = cancelReason || null
    savePending(user.id, {
      key,
      method: 'POST',
      path: `/auctions/${id}/cancel`,
      body: { reason },
      actorId: user.id,
      createdAt: new Date().toISOString(),
    })
    setCancelPending(true)
    try {
      await cancelLot(id, reason, key)
      clearPending(user.id, key)
      setShowCancel(false)
      refreshLot()
    } catch (err) {
      setError(httpErrorMessage(err, 'Cancel failed'))
    } finally {
      setCancelPending(false)
    }
  }

  if (auctionQ.isLoading) return <p className="text-muted">Loading…</p>
  if (auctionQ.isError) return <p className="text-danger">Could not load lot.</p>
  if (!a) return <p className="text-danger">Lot not found.</p>

  const item = a.item as AuctionSummary['item']
  const isOwner = Boolean(a.viewer_is_owner)
  const displayStatus = String(a.display_status)
  const cancelled = displayStatus === 'CANCELLED'
  const live = displayStatus === 'LIVE'
  const canCancel = isOwner && sellerCanCancel(displayStatus)
  const currentMoney =
    a.current_bid ?? a.opening_bid
  const increment = a.minimum_increment
  const nextMinCents = currentMoney.cents + increment.cents
  const bidCount = a.bid_count ?? bidItems.length
  const hasBids = bidCount > 0
  const canBid =
    user?.role === 'BIDDER' &&
    live &&
    wsConnected &&
    !a.confirmation_pending &&
    position !== 'LEADING' &&
    position !== 'WON' &&
    position !== 'LOST' &&
    position !== 'CANCELLED'

  return (
    <div className="space-y-6">
      {!wsConnected && (
        <Banner variant="warning">
          Connection lost. Reconnecting… Latest bids may be outdated.
        </Banner>
      )}
      <div>
        <StatusBadge status={displayStatus} variant="pill" />
        <h1 className="mt-2 font-display text-4xl font-normal md:text-[40px]">{item.title}</h1>
        <p className="mt-1 text-muted">
          {lotArtworkLine(a.display_no, item.artist, item.object_begin_date)}
        </p>
      </div>
      {isOwner && <Banner variant="info">You own this lot</Banner>}
      {a.confirmation_pending && <Banner variant="warning">Confirmation pending</Banner>}
      {cancelled && typeof a.cancel_reason === 'string' && a.cancel_reason.length > 0 ? (
        <Banner variant="warning">Cancelled: {a.cancel_reason}</Banner>
      ) : null}
      {position === 'WON' && <Banner variant="success">You won this lot</Banner>}
      {position === 'LOST' && (
        <Banner variant="info">This lot ended without your winning bid</Banner>
      )}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-4">
          <div className="flex min-h-72 items-center justify-center rounded-xl bg-brand-soft p-4">
            {item.image_url ? (
              <img src={item.image_url} alt="" className="max-h-96 w-full object-contain" />
            ) : (
              <span className="text-muted">No image</span>
            )}
          </div>
          <section>
            <h2 className="mb-2 font-semibold text-text">About the artwork</h2>
            <p className="text-sm whitespace-pre-line text-muted">
              {item.description?.trim() ||
                item.attribution?.trim() ||
                'Details from the catalog will appear here when available.'}
            </p>
            {item.object_url && (
              <a
                href={item.object_url}
                target="_blank"
                rel="noreferrer"
                className="mt-2 inline-block text-sm text-brand hover:underline"
              >
                View artwork at The Met →
              </a>
            )}
          </section>
        </div>
        <Card className="space-y-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">
            Current bid · USD
          </p>
          <p className="font-display text-4xl text-text">
            <Money value={currentMoney} />
          </p>
          {!hasBids && (
            <p className="text-sm text-muted">{leaderLine(a.leader_alias, bidCount)}</p>
          )}
          <hr className="border-border" />
          <Clock
            endsAt={a.ends_at}
            serverTime={a.server_time}
            displayStatus={displayStatus}
            onElapsed={() => refreshLot()}
          />
          <p className="text-sm text-muted">{formatEndsLine(a.ends_at)}</p>
          {live && (
            <Banner variant="warning">
              <span className="font-medium">Extra time for a fair finish</span>
              <p className="mt-1 text-xs opacity-90">
                A bid accepted in the final 2 minutes adds 2 minutes to the current deadline.
              </p>
            </Banner>
          )}
          {position === 'OUTBID' && (
            <Banner variant="warning">
              <span className="font-medium">You have been outbid</span>
              <p className="mt-1 text-xs opacity-90">
                Your previous reservation was released. Place a new bid to take the lead.
              </p>
            </Banner>
          )}
          {position === 'LEADING' && (
            <Banner variant="success">
              <span className="font-medium">You are leading</span>
              <p className="mt-1 text-xs opacity-90">
                <Money value={{ cents: posQ.data?.reserved_cents ?? currentMoney.cents, currency: 'USD' }} />{' '}
                reserved for this lot. You cannot cover your own leading bid.
              </p>
            </Banner>
          )}
          {!user && live && (
            <ButtonLink
              to={`/login?returnTo=${encodeURIComponent(`/lots/${id}`)}`}
              variant="primary"
              className="w-full"
            >
              Sign in to place a bid
            </ButtonLink>
          )}
          {canBid && (
            <form onSubmit={onBid} className="space-y-3">
              <p className="text-sm text-muted">
                {minimumBidLine({ cents: nextMinCents, currency: 'USD' }, increment)}
              </p>
              <TextField
                label="Your bid (USD)"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={pending}
              />
              {error && <Banner variant="danger">{error}</Banner>}
              <Button type="submit" disabled={pending} className="w-full">
                Place bid
              </Button>
              {user?.role === 'BIDDER' && walletQ.data && (
                <p className="text-center text-sm text-muted">
                  Available to bid: <Money value={walletQ.data.available} />
                </p>
              )}
            </form>
          )}
          {error && !canBid && <Banner variant="danger">{error}</Banner>}
          {canCancel && (
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
                  <TextAreaField
                    label={
                      <>
                        Public cancellation reason
                        {hasBids ? ' (required when the lot has bids)' : ' (optional)'}
                      </>
                    }
                    value={cancelReason}
                    onChange={(e) => setCancelReason(e.target.value)}
                    required={hasBids}
                  />
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Button
                      type="button"
                      variant="secondary"
                      className="flex-1"
                      onClick={() => setShowCancel(false)}
                    >
                      Keep auction live
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      className="flex-1"
                      onClick={onCancel}
                      disabled={cancelPending}
                    >
                      {cancelPending ? 'Cancelling…' : 'Cancel lot'}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
          <div className="space-y-2 border-t border-border pt-3">
            <ButtonLink to={`/lots/${id}/audit`} className="w-full">
              View public audit
            </ButtonLink>
            {typeof a.receipt_id === 'string' && (
              <ButtonLink to={`/receipts/${a.receipt_id}`} variant="secondary" className="w-full">
                View receipt
              </ButtonLink>
            )}
          </div>
        </Card>
      </div>
      {!cancelled && (bidsQ.isLoading || bidsQ.isError || bidItems.length > 0) && (
        <Card>
          <h2 className="mb-4 font-semibold text-text">Latest bids</h2>
          {bidsQ.isLoading && <p className="text-sm text-muted">Loading…</p>}
          {bidsQ.isError && <p className="mb-2 text-sm text-danger">Could not load bids.</p>}
          {bidItems.length > 0 && (
            <ul className="divide-y divide-border">
              {bidItems.map((b) => (
                <li
                  key={b.sequence}
                  className="grid grid-cols-1 gap-1 py-3 text-sm sm:grid-cols-[auto_1fr_auto] sm:items-center sm:gap-4"
                >
                  <span className="font-medium text-muted">#{b.sequence}</span>
                  <span>
                    {b.bidder_alias}
                    {' · '}
                    <Money value={{ cents: b.amount_cents, currency: 'USD' }} />
                  </span>
                  <span className="text-muted sm:text-right">
                    {formatBidTimestamp(b.accepted_at)}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {bidItems.length >= 20 && (
            <Button
              type="button"
              variant="secondary"
              className="mt-4 w-full"
              onClick={loadEarlier}
              disabled={loadingOlder}
            >
              {loadingOlder ? 'Loading…' : 'Load earlier bids'}
            </Button>
          )}
        </Card>
      )}
    </div>
  )
}
