import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { listAuctions } from '../features/lots'
import type { DisplayStatus } from '../lib/types'

const tabs: { key: 'LIVE' | 'SCHEDULED' | 'ENDED'; label: string }[] = [
  { key: 'LIVE', label: 'Live' },
  { key: 'SCHEDULED', label: 'Upcoming' },
  { key: 'ENDED', label: 'Ended' },
]

function tabLabel(status: DisplayStatus): string {
  if (status === 'SCHEDULED') return 'Upcoming'
  if (status === 'LIVE') return 'Live'
  if (status === 'FINALIZING') return 'Ended'
  if (status === 'CLOSED') return 'Ended'
  return status
}

export function Home() {
  const [tab, setTab] = useState<'LIVE' | 'SCHEDULED' | 'ENDED'>('LIVE')
  const q = useQuery({
    queryKey: ['auctions', tab],
    queryFn: () => listAuctions(tab),
  })

  return (
    <div>
      <h1 className="mb-4 text-2xl font-semibold">Auctions</h1>
      <div className="mb-4 flex gap-2">
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
              <span className="ml-1 opacity-80">
                (
                {t.key === 'LIVE'
                  ? q.data.counts.live
                  : t.key === 'SCHEDULED'
                    ? q.data.counts.scheduled
                    : q.data.counts.ended}
                )
              </span>
            )}
          </button>
        ))}
      </div>
      {q.isLoading && <p className="text-muted">Loading…</p>}
      {q.isError && <p className="text-danger">Could not load auctions.</p>}
      {q.data?.items.length === 0 && <p className="text-muted">No lots in this tab.</p>}
      <ul className="grid gap-4 sm:grid-cols-2">
        {q.data?.items.map((a) => (
          <li key={a.id}>
            <Link to={`/lots/${a.id}`}>
              <Card className="hover:border-brand transition-colors">
                <div className="flex gap-3">
                  <div className="h-24 w-24 shrink-0 overflow-hidden rounded-lg bg-brand-soft">
                    {a.item.image_url ? (
                      <img
                        src={a.item.image_url}
                        alt=""
                        className="h-full w-full object-cover"
                      />
                    ) : null}
                  </div>
                  <div>
                    <p className="text-xs text-muted">
                      Lot {String(a.display_no).padStart(3, '0')} · {tabLabel(a.display_status)}
                    </p>
                    <p className="font-medium">{a.item.title}</p>
                    <p className="text-sm text-muted">{a.item.artist ?? 'Not stated'}</p>
                    <p className="mt-1 text-sm">
                      {a.current_bid ? (
                        <>Current <Money value={a.current_bid} /></>
                      ) : (
                        <>Opening <Money value={a.opening_bid} /></>
                      )}
                    </p>
                  </div>
                </div>
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
