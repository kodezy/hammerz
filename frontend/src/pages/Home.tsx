import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { AuctionListRow } from '../components/AuctionListRow'
import { MarketingHero } from '../components/MarketingHero'
import { TabNav } from '../components/TabNav'
import { TextField } from '../components/TextField'
import { listAuctions } from '../features/lots'

const tabs: { key: 'LIVE' | 'SCHEDULED' | 'ENDED'; label: string }[] = [
  { key: 'LIVE', label: 'Live' },
  { key: 'SCHEDULED', label: 'Upcoming' },
  { key: 'ENDED', label: 'Ended' },
]

export function Home() {
  const [tab, setTab] = useState<'LIVE' | 'SCHEDULED' | 'ENDED'>('LIVE')
  const [filter, setFilter] = useState('')
  const q = useQuery({
    queryKey: ['auctions', tab],
    queryFn: () => listAuctions(tab),
  })

  const counts = q.data?.counts
  const tabLabels = tabs.map((t) => {
    const n =
      t.key === 'LIVE'
        ? counts?.live
        : t.key === 'SCHEDULED'
          ? counts?.scheduled
          : counts?.ended
    return {
      key: t.key,
      label: n !== undefined ? `${t.label} (${n})` : t.label,
    }
  })

  const needle = filter.trim().toLowerCase()
  const visibleItems = useMemo(() => {
    const items = q.data?.items ?? []
    if (!needle) return items
    return items.filter((a) => a.item.title.toLowerCase().includes(needle))
  }, [q.data?.items, needle])

  return (
    <div className="space-y-10">
      <MarketingHero />
      <section className="space-y-8">
        <TextField
          label="Search lots on this tab"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter by title"
        />
        <TabNav tabs={tabLabels} active={tab} onChange={setTab} />
        {q.isLoading && <p className="text-muted">Loading…</p>}
        {q.isError && <p className="text-danger">Could not load auctions.</p>}
        {!q.isLoading && !q.isError && visibleItems.length === 0 && (
          <p className="text-muted">
            {needle ? 'No lots match your search on this tab.' : 'No lots in this tab yet.'}
          </p>
        )}
        <ul className="flex flex-col gap-4">
          {visibleItems.map((a) => {
            const amount = a.current_bid ?? a.opening_bid
            const count = a.bid_count ?? 0
            return (
              <AuctionListRow
                key={a.id}
                ctaTo={`/lots/${a.id}`}
                displayStatus={a.display_status}
                displayNo={a.display_no}
                title={a.item.title}
                imageUrl={a.item.image_url}
                amount={amount}
                bidCount={count}
              />
            )
          })}
        </ul>
      </section>
    </div>
  )
}
