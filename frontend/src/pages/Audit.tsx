import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Banner } from '../components/Banner'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { PageHeading } from '../components/PageHeading'
import { fetchAudit, getAuction, listBids, type BidRow } from '../features/lots'
import { integrityLabel, lotStatusLabel } from '../lib/display'
import { lotListingTitle } from '../lib/lotCopy'
import { formatBidTimestamp } from '../lib/time'

export function Audit() {
  const { id = '' } = useParams()
  const [older, setOlder] = useState<BidRow[]>([])
  const [loadingOlder, setLoadingOlder] = useState(false)
  const auctionQ = useQuery({ queryKey: ['auction', id], queryFn: () => getAuction(id) })
  const auditQ = useQuery({
    queryKey: ['audit', id],
    queryFn: () => fetchAudit(id),
  })
  const bidsQ = useQuery({
    queryKey: ['audit-bids', id],
    queryFn: () => listBids(id),
  })

  const verification = auditQ.data?.verification
  const a = auctionQ.data
  const bidItems = [...(bidsQ.data?.items ?? []), ...older]
  const bidCount = auditQ.data?.bid_count ?? bidItems.length
  const oldest = bidItems.length > 0 ? Math.min(...bidItems.map((b) => b.sequence)) : undefined

  async function loadEarlier() {
    if (!oldest || loadingOlder) return
    setLoadingOlder(true)
    try {
      const page = await listBids(id, oldest)
      const have = new Set(bidItems.map((b) => b.sequence))
      setOlder((prev) => [...prev, ...page.items.filter((b) => !have.has(b.sequence))])
    } finally {
      setLoadingOlder(false)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeading
        title="Public audit"
        subtitle={a ? lotListingTitle(a.display_no, a.item.title) : undefined}
      />
      {auditQ.isLoading && <p className="text-muted">Loading…</p>}
      {verification && (
        <Banner
          variant={
            verification.status === 'VERIFIED'
              ? 'success'
              : verification.status === 'TAMPERED'
                ? 'danger'
                : 'warning'
          }
        >
          <span className="font-medium">{integrityLabel(verification.status ?? '')}</span>
          {verification.status === 'VERIFIED' && bidCount > 0 && (
            <p className="mt-1 text-xs opacity-90">
              All {bidCount} accepted bids and lifecycle events match the independent audit
              evidence.
            </p>
          )}
        </Banner>
      )}
      {a && verification?.checked_at && (
        <p className="text-sm text-muted">
          Auction status: {lotStatusLabel(a.display_status)} · Checked{' '}
          {formatBidTimestamp(verification.checked_at)}
        </p>
      )}
      {a?.cancel_reason && typeof a.cancel_reason === 'string' && (
        <Banner variant="warning">
          <span className="font-medium">Cancellation record</span>
          <p className="mt-1 text-xs opacity-90">{a.cancel_reason}</p>
        </Banner>
      )}
      <Card>
        <h2 className="mb-4 font-semibold text-text">Complete bid history</h2>
        <ul className="divide-y divide-border">
          {bidItems.map((b) => (
            <li
              key={b.sequence}
              className="grid grid-cols-1 gap-1 py-3 text-sm sm:grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] sm:items-center sm:gap-4"
            >
              <span className="font-medium">{b.bidder_alias}</span>
              <Money value={{ cents: b.amount_cents, currency: 'USD' }} />
              <span className="text-muted sm:text-right">
                #{b.sequence} · {formatBidTimestamp(b.accepted_at)}
              </span>
            </li>
          ))}
        </ul>
        {bidItems.length === 0 && !bidsQ.isLoading && (
          <p className="text-sm text-muted">No accepted bids yet.</p>
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
        {bidCount > 0 && (
          <p className="mt-3 text-xs text-muted">All {bidCount} accepted bids shown.</p>
        )}
      </Card>
      <p className="text-sm text-muted">
        Public aliases protect bidder identities. No names or emails are included.
      </p>
    </div>
  )
}
