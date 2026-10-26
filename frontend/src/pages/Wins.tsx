import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useSession } from '../app/session'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { api } from '../lib/http'

type Tab = 'ACTIVE' | 'WON' | 'PAST'

export function Wins() {
  const { user } = useSession()
  const [tab, setTab] = useState<Tab>('ACTIVE')
  const q = useQuery({
    queryKey: ['wins', tab],
    queryFn: () =>
      api<{
        items: Record<string, unknown>[]
        counts: { active: number; won: number; past: number }
      }>(`/me/bids-and-wins?tab=${tab}&limit=20`),
    enabled: !!user && user.role === 'BIDDER',
  })

  if (!user || user.role !== 'BIDDER') {
    return <p className="text-muted">Sign in as a bidder to view participations.</p>
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: 'ACTIVE', label: 'Active bids' },
    { key: 'WON', label: 'Won' },
    { key: 'PAST', label: 'Past auctions' },
  ]

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">My Bids &amp; Wins</h1>
      <div className="mb-4 flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`rounded-lg px-3 py-2 text-sm ${
              tab === t.key ? 'bg-action text-on-action' : 'border border-border'
            }`}
          >
            {t.label}
            {q.data?.counts && (
              <span className="ml-1">
                (
                {t.key === 'ACTIVE'
                  ? q.data.counts.active
                  : t.key === 'WON'
                    ? q.data.counts.won
                    : q.data.counts.past}
                )
              </span>
            )}
          </button>
        ))}
      </div>
      {q.isLoading && <p>Loading…</p>}
      {q.data?.items.length === 0 && <p className="text-muted">No items in this tab.</p>}
      <ul className="space-y-3">
        {q.data?.items.map((row) => {
          const id = String(row.id)
          const displayNo = row.display_no as number
          const title = (row.item as { title: string })?.title
          return (
            <li key={id}>
              <Card>
                <Link to={`/lots/${id}`} className="font-medium text-brand hover:underline">
                  Lot {String(displayNo).padStart(3, '0')}: {title}
                </Link>
                <p className="text-sm text-muted">Position: {String(row.position)}</p>
                {'current_bid' in row && row.current_bid != null ? (
                  <p className="text-sm">
                    Current <Money value={row.current_bid as { cents: number; currency: 'USD' }} />
                  </p>
                ) : null}
                {row.receipt_id ? (
                  <Link to={`/receipts/${String(row.receipt_id)}`} className="text-sm text-brand">
                    View receipt
                  </Link>
                ) : null}
              </Card>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
