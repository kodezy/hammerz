import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { AuctionListRow } from '../components/AuctionListRow'
import { MarketingHero } from '../components/MarketingHero'
import { TabNav } from '../components/TabNav'
import { listAuctions } from '../features/lots'

const tabs: { key: 'LIVE' | 'SCHEDULED' | 'ENDED'; label: string }[] = [
  { key: 'LIVE', label: 'Live' },
  { key: 'SCHEDULED', label: 'Upcoming' },
  { key: 'ENDED', label: 'Ended' },
]

export function Home() {
  const [tab, setTab] = useState<'LIVE' | 'SCHEDULED' | 'ENDED'>('LIVE')
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

  return (
    <div className="space-y-10">
      <MarketingHero />
      <section className="space-y-8">
        <TabNav tabs={tabLabels} active={tab} onChange={setTab} />
        {q.isLoading && <p className="text-muted">Loading…</p>}
        {q.isError && <p className="text-danger">Could not load auctions.</p>}
        {q.data?.items.length === 0 && <p className="text-muted">No lots in this tab.</p>}
        <ul className="flex flex-col gap-4">
          {q.data?.items.map((a) => {
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
