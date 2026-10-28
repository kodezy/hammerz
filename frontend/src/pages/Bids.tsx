import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useSession } from '../app/session'
import { AuctionListRow } from '../components/AuctionListRow'
import { ButtonLink } from '../components/Button'
import { Money } from '../components/Money'
import { PageHeading } from '../components/PageHeading'
import { PositionBadge } from '../components/PositionBadge'
import { StatusBadge } from '../components/StatusBadge'
import { TabNav } from '../components/TabNav'
import { listMyBids, type MyBidRow, type MyBidsTab } from '../features/bids'

function bidMeta(tab: MyBidsTab, row: MyBidRow) {
  if ((tab === 'ACTIVE' && row.position === 'OUTBID' && row.user_last_bid) || (tab === 'PAST' && row.user_last_bid)) {
    return (
      <p className="text-[13px] text-muted">
        Your last bid: <Money value={row.user_last_bid} />
      </p>
    )
  }
  return null
}

export function Bids() {
  const { user } = useSession()
  const [tab, setTab] = useState<MyBidsTab>('ACTIVE')
  const q = useQuery({
    queryKey: ['my-bids', tab],
    queryFn: () => listMyBids(tab),
    enabled: !!user && user.role === 'BIDDER',
  })

  if (!user || user.role !== 'BIDDER') {
    return <p className="text-muted">Sign in as a bidder to view your bids.</p>
  }

  const counts = q.data?.counts
  const tabs: { key: MyBidsTab; label: string }[] = [
    { key: 'ACTIVE', label: `Active${counts ? ` (${counts.active})` : ''}` },
    { key: 'WON', label: `Won${counts ? ` (${counts.won})` : ''}` },
    { key: 'PAST', label: `Past${counts ? ` (${counts.past})` : ''}` },
  ]

  return (
    <div className="space-y-8">
      <PageHeading title="Bids" subtitle="Follow active lots, won auctions, and past results." />
      <TabNav tabs={tabs} active={tab} onChange={setTab} />
      {q.isLoading && <p className="text-muted">Loading…</p>}
      {q.isError && <p className="text-danger">Could not load bids.</p>}
      <ul className="flex flex-col gap-4">
        {q.data?.items.map((row) => {
          const amount = row.current_bid ?? row.opening_bid
          const count = row.bid_count ?? 0
          const receiptId = row.receipt_id
          return (
            <AuctionListRow
              key={row.id}
              displayStatus={row.display_status}
              displayNo={row.display_no}
              title={row.item.title}
              imageUrl={row.item.image_url}
              amount={amount}
              bidCount={count}
              badges={
                <>
                  <StatusBadge status={row.display_status} variant="list" />
                  <PositionBadge position={row.position} />
                </>
              }
              meta={bidMeta(tab, row)}
              actions={
                <>
                  <ButtonLink to={`/lots/${row.id}`} className="w-full">
                    View auction
                  </ButtonLink>
                  {receiptId ? (
                    <ButtonLink to={`/receipts/${receiptId}`} className="w-full">
                      View receipt
                    </ButtonLink>
                  ) : null}
                </>
              }
            />
          )
        })}
      </ul>
    </div>
  )
}
