import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { Banner } from '../components/Banner'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { getReceipt } from '../features/audit'
import { formatDateTime } from '../lib/time'

function integrityLabel(status: string): string {
  if (status === 'VERIFIED') return 'Verified'
  if (status === 'TAMPERED') return 'Changes detected'
  return 'Unable to verify'
}

export function Receipt() {
  const { id = '' } = useParams()
  const q = useQuery({
    queryKey: ['receipt', id],
    queryFn: () => getReceipt(id),
  })
  const r = q.data
  const integrity = r?.integrity as { status?: string; checked_at?: string } | undefined
  const auctionId = r?.auction_id as string | undefined

  async function share() {
    const url = window.location.href
    try {
      await navigator.clipboard.writeText(url)
    } catch {
      /* fallback below */
    }
  }

  if (q.isLoading) return <p>Loading…</p>
  if (!r) return <p>Receipt not found.</p>

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Receipt</h1>
      {integrity && (
        <Banner
          variant={
            integrity.status === 'VERIFIED'
              ? 'success'
              : integrity.status === 'TAMPERED'
                ? 'danger'
                : 'warning'
          }
        >
          {integrityLabel(integrity.status ?? '')}
        </Banner>
      )}
      <Card className="space-y-2">
        <p className="font-medium">{String(r.title)}</p>
        <p className="text-muted">{String(r.artist ?? 'Not stated')}</p>
        <p>Winner: {String(r.winner_alias)}</p>
        <p>
          Amount: <Money value={r.amount as { cents: number; currency: 'USD' }} />
        </p>
        <p>Financial status: Settled</p>
        {r.settled_at ? <p>Settled: {formatDateTime(String(r.settled_at))}</p> : null}
      </Card>
      {auctionId && (
        <Link to={`/lots/${auctionId}/audit`} className="text-brand hover:underline">
          View public audit
        </Link>
      )}
      <div>
        <button type="button" onClick={share} className="rounded-lg bg-action px-4 py-2 text-on-action">
          Copy receipt link
        </button>
        <p className="mt-2 break-all text-sm text-muted select-all">{window.location.href}</p>
      </div>
    </div>
  )
}
