import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { AuctionListRow } from '../components/AuctionListRow'
import { EmptyState } from '../components/EmptyState'
import { MarketingHero } from '../components/MarketingHero'
import { TabNav } from '../components/TabNav'
import { TextField } from '../components/TextField'
import { listAuctions } from '../features/lots'

type HomeTab = 'LIVE' | 'SCHEDULED' | 'ENDED'

const tabs: { key: HomeTab; label: string }[] = [
  { key: 'LIVE', label: 'Live' },
  { key: 'SCHEDULED', label: 'Upcoming' },
  { key: 'ENDED', label: 'Ended' },
]

function emptyCopy(tab: HomeTab): { title: string; body: string } {
  switch (tab) {
    case 'LIVE':
      return {
        title: 'No live auctions',
        body: 'Nothing is open for bidding right now. Upcoming lots appear before they go live.',
      }
    case 'SCHEDULED':
      return {
        title: 'Nothing upcoming',
        body: 'Scheduled lots show up here before they open for bids.',
      }
    case 'ENDED':
      return {
        title: 'No ended auctions',
        body: 'Settled lots will appear here after they close.',
      }
  }
}

export function Home() {
  const [tab, setTab] = useState<HomeTab>('LIVE')
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
  const empty = needle
    ? { title: 'No matching lots', body: 'Nothing on this tab matches that title.' }
    : emptyCopy(tab)
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
          <EmptyState title={empty.title}>{empty.body}</EmptyState>
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
