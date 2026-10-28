import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { useToast } from '../app/toast'
import { Banner } from '../components/Banner'
import { Button, ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { StatusBadge } from '../components/StatusBadge'
import { Money } from '../components/Money'
import { getReceipt } from '../features/receipts'
import { integrityBanner, parseAuditStatus } from '../lib/display'
import { receiptCatalogLine } from '../lib/lotCopy'
import { formatBidTimestamp } from '../lib/time'

export function Receipt() {
  const { id = '' } = useParams()
  const { showToast } = useToast()
  const q = useQuery({
    queryKey: ['receipt', id],
    queryFn: () => getReceipt(id),
  })
  const r = q.data
  const displayNo = r?.display_no as number | undefined
  const publicCode = r?.public_code as string | undefined
  const auctionId = r?.auction_id as string | undefined
  const integrity = r?.integrity as { status?: unknown; reason_codes?: string[] } | undefined
  const auditStatus = parseAuditStatus(integrity?.status)
  const verified = auditStatus === 'VERIFIED' || auditStatus === null

  async function share() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      showToast('Share link copied')
    } catch {
      showToast('Could not copy the link', 'danger')
    }
  }

  if (q.isLoading) return <p className="text-muted">Loading…</p>
  if (q.isError) return <p className="text-danger">Could not load receipt.</p>
  if (!r) return <p className="text-danger">Receipt not found.</p>

  const amount = (r.amount as { cents: number; currency: 'USD' }) ?? {
    cents: r.amount_cents as number,
    currency: 'USD' as const,
  }
  const lotLabel = displayNo != null ? `Lot ${String(displayNo).padStart(3, '0')}` : 'Lot'
  const code =
    publicCode ??
    (displayNo != null ? `HZ-2026-${String(displayNo).padStart(4, '0')}` : 'HZ-2026')
  const banner = auditStatus ? integrityBanner(auditStatus) : null

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {verified ? <StatusBadge status="SETTLED" /> : null}
      <p className="text-lg text-muted">
        {verified ? 'A discovery, now yours.' : 'This receipt is shown with an integrity warning.'}
      </p>
      <h1 className="font-display text-4xl font-normal leading-tight text-text">
        Auction receipt · {code} · {lotLabel}
      </h1>
      {banner && (
        <Banner variant={banner.variant}>
          <span className="font-medium">{banner.title}</span>
          <p className="mt-1 text-xs opacity-90">{banner.body}</p>
          {integrity?.reason_codes && integrity.reason_codes.length > 0 && (
            <p className="mt-2 text-xs opacity-90">
              Reason codes: {integrity.reason_codes.join(', ')}
            </p>
          )}
        </Banner>
      )}
      <Card className="space-y-3">
        <p className="font-display text-2xl text-text">{String(r.title)}</p>
        <p className="text-sm text-muted">
          {receiptCatalogLine({
            artist: r.artist as string | null,
            object_begin_date: r.object_begin_date as string | number | null,
            external_id: r.external_id as string | null,
          })}
        </p>
        <p className="text-sm">
          Winning bidder · <span className="font-semibold">{String(r.winner_alias)}</span>
        </p>
        <p className="text-sm">
          Winning amount · USD <Money value={amount} />
        </p>
        {r.settled_at ? (
          <p className="text-sm text-muted">Settled {formatBidTimestamp(String(r.settled_at))}</p>
        ) : null}
      </Card>
      {auctionId && (
        <ButtonLink to={`/lots/${auctionId}/audit`} className="w-full">
          View public audit
        </ButtonLink>
      )}
      <div className="space-y-2">
        <Button type="button" onClick={share} className="w-full">
          Copy share link
        </Button>
      </div>
    </div>
  )
}
