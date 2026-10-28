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
import { api } from '../lib/http'
import type { DisplayStatus, Money as MoneyType, Position } from '../lib/types'

type Tab = 'ACTIVE' | 'WON' | 'PAST'

type WinRow = {
  id: string
  display_no: number
  display_status: DisplayStatus
  position: Position
  item: { title: string; image_url: string | null }
  current_bid: MoneyType | null
  opening_bid: MoneyType
  bid_count?: number
  user_last_bid?: MoneyType
  receipt_id?: string
}

function participationMeta(tab: Tab, row: WinRow) {
  if ((tab === 'ACTIVE' && row.position === 'OUTBID' && row.user_last_bid) || (tab === 'PAST' && row.user_last_bid)) {
    return (
      <p className="text-[13px] text-muted">
        Your last bid: <Money value={row.user_last_bid} />
      </p>
    )
  }
  return null
}

export function Wins() {
  const { user } = useSession()
  const [tab, setTab] = useState<Tab>('ACTIVE')
  const q = useQuery({
    queryKey: ['wins', tab],
    queryFn: () =>
      api<{
        items: WinRow[]
        counts: { active: number; won: number; past: number }
      }>(`/me/bids-and-wins?tab=${tab}&limit=20`),
    enabled: !!user && user.role === 'BIDDER',
  })

  if (!user || user.role !== 'BIDDER') {
    return <p className="text-muted">Sign in as a bidder to view participations.</p>
  }

  const counts = q.data?.counts
  const tabs: { key: Tab; label: string }[] = [
    { key: 'ACTIVE', label: `Active bids${counts ? ` (${counts.active})` : ''}` },
    { key: 'WON', label: `Won${counts ? ` (${counts.won})` : ''}` },
    { key: 'PAST', label: `Past${counts ? ` (${counts.past})` : ''}` },
  ]

  return (
    <div className="space-y-8">
      <PageHeading
        title="My Bids & Wins"
        subtitle="Follow your bids, revisit results and collect receipts."
      />
      <TabNav tabs={tabs} active={tab} onChange={setTab} />
      {q.isLoading && <p className="text-muted">Loading…</p>}
      {q.isError && <p className="text-danger">Could not load bids and wins.</p>}
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
              meta={participationMeta(tab, row)}
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
