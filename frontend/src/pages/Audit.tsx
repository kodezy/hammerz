import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useToast } from '../app/toast'
import { Banner } from '../components/Banner'
import { Button } from '../components/Button'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { PageHeading } from '../components/PageHeading'
import { getAudit, getAuction, type AuditEventRow } from '../features/lots'
import { auditEventLabel, integrityBanner, lotStatusLabel } from '../lib/display'
import { HttpError } from '../lib/http'
import { lotListingTitle } from '../lib/lotCopy'
import { formatBidTimestamp } from '../lib/time'

function cancelReasonFromEvents(events: AuditEventRow[]): string | null {
  for (const ev of events) {
    if (ev.type !== 'AUCTION_CANCELLED') continue
    const p = ev.payload
    const reason = p.reason
    if (typeof reason === 'string' && reason.trim()) return reason.trim()
  }
  return null
}

function eventOccurredAt(payload: Record<string, unknown>): string | null {
  const at = payload.occurred_at
  return typeof at === 'string' ? at : null
}

export function Audit() {
  const { id = '' } = useParams()
  const { showToast } = useToast()
  const [older, setOlder] = useState<AuditEventRow[]>([])
  const [loadingOlder, setLoadingOlder] = useState(false)
  const [canLoadEarlier, setCanLoadEarlier] = useState(false)

  const auditQ = useQuery({
    queryKey: ['audit', id],
    queryFn: () => getAudit(id),
  })
  const auctionQ = useQuery({
    queryKey: ['auction', id],
    queryFn: () => getAuction(id),
    retry: false,
  })

  useEffect(() => {
    setOlder([])
    setCanLoadEarlier(false)
  }, [id])

  useEffect(() => {
    const n = auditQ.data?.items.length ?? 0
    setCanLoadEarlier(n >= 20)
  }, [id, auditQ.data?.items.length])

  const verification = auditQ.data?.verification
  const a = auctionQ.data
  const baseItems = auditQ.data?.items ?? []
  const eventItems = [...baseItems, ...older]
  const oldest =
    eventItems.length > 0 ? Math.min(...eventItems.map((e) => e.sequence)) : undefined
  const bidCount = auditQ.data?.bid_count ?? 0

  const cancelReason =
    (typeof a?.cancel_reason === 'string' && a.cancel_reason) ||
    cancelReasonFromEvents(eventItems)

  async function loadEarlier() {
    if (!oldest || loadingOlder) return
    setLoadingOlder(true)
    try {
      const page = await getAudit(id, oldest)
      const have = new Set(eventItems.map((e) => e.sequence))
      const newItems = page.items.filter((e) => !have.has(e.sequence))
      if (newItems.length === 0 || page.items.length < 20) {
        setCanLoadEarlier(false)
      }
      setOlder((prev) => [...prev, ...newItems])
    } catch {
      showToast('Could not load earlier events', 'danger')
    } finally {
      setLoadingOlder(false)
    }
  }

  if (auditQ.isLoading) return <p className="text-muted">Loading…</p>
  if (auditQ.isError) {
    if (auditQ.error instanceof HttpError && auditQ.error.status === 404) {
      return <p className="text-danger">Lot not found.</p>
    }
    return <p className="text-danger">Could not load audit.</p>
  }
  if (!verification) return <p className="text-danger">Could not load audit.</p>

  const banner = integrityBanner(verification.status)
  const subtitle =
    a != null
      ? lotListingTitle(a.display_no, a.item.title)
      : `Lot ${id.slice(0, 8)}…`

  return (
    <div className="space-y-6">
      <PageHeading title="Public audit" subtitle={subtitle} />
      <Link to={`/lots/${id}`} className="text-sm text-brand hover:underline">
        Back to lot
      </Link>
      <Banner variant={banner.variant}>
        <span className="font-medium">{banner.title}</span>
        <p className="mt-1 text-xs opacity-90">{banner.body}</p>
      </Banner>
      {verification.reason_codes.length > 0 && (
        <p className="text-sm text-muted">
          Reason codes: {verification.reason_codes.join(', ')}
        </p>
      )}
      {verification.checked_at && (
        <p className="text-sm text-muted">
          Checked {formatBidTimestamp(verification.checked_at)}
          {a != null ? ` · Auction status: ${lotStatusLabel(a.display_status)}` : null}
        </p>
      )}
      {verification.status === 'VERIFIED' && bidCount > 0 && (
        <p className="text-sm text-muted">
          {bidCount} accepted bid{bidCount === 1 ? '' : 's'} checked against the journal.
        </p>
      )}
      {cancelReason && (
        <Banner variant="warning">
          <span className="font-medium">Cancellation record</span>
          <p className="mt-1 text-xs opacity-90">{cancelReason}</p>
        </Banner>
      )}
      <Card>
        <h2 className="mb-4 font-semibold text-text">Audit events</h2>
        <ul className="divide-y divide-border">
          {eventItems.map((ev) => {
            const at = eventOccurredAt(ev.payload)
            const alias =
              typeof ev.payload.actor_alias === 'string' ? ev.payload.actor_alias : null
            const cents = ev.payload.amount_cents
            return (
              <li
                key={ev.sequence}
                className="grid grid-cols-1 gap-1 py-3 text-sm sm:grid-cols-[auto_1fr_auto] sm:items-center sm:gap-4"
              >
                <span className="font-medium text-muted">#{ev.sequence}</span>
                <span>
                  {auditEventLabel(ev.type)}
                  {alias ? ` · ${alias}` : ''}
                  {typeof cents === 'number' ? (
                    <>
                      {' · '}
                      <Money value={{ cents, currency: 'USD' }} />
                    </>
                  ) : null}
                </span>
                <span className="text-muted sm:text-right">
                  {at ? formatBidTimestamp(at) : '—'}
                </span>
              </li>
            )
          })}
        </ul>
        {eventItems.length === 0 && <p className="text-sm text-muted">No audit events yet.</p>}
        {canLoadEarlier && (
          <Button
            type="button"
            variant="secondary"
            className="mt-4 w-full"
            onClick={loadEarlier}
            disabled={loadingOlder}
          >
            {loadingOlder ? 'Loading…' : 'Load earlier events'}
          </Button>
        )}
      </Card>
      <p className="text-sm text-muted">Participants appear by public alias only.</p>
    </div>
  )
}
