import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useSession } from '../app/session'
import { useToast } from '../app/toast'
import { AuctionListRow } from '../components/AuctionListRow'
import { Banner } from '../components/Banner'
import { Button, ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { CreateLotModal } from '../components/CreateLotModal'
import { Money } from '../components/Money'
import { PageHeading } from '../components/PageHeading'
import { TabNav } from '../components/TabNav'
import { sellerAuctions } from '../features/lots'
import type { DisplayStatus, Money as MoneyType } from '../lib/types'

type SellerTab = 'LIVE' | 'SCHEDULED' | 'ENDED' | 'CANCELLED'

type SellerRow = {
  id: string
  display_no: number
  display_status: DisplayStatus
  item: { title: string; image_url: string | null }
  current_bid: MoneyType | null
  opening_bid: MoneyType
  bid_count?: number
  receipt_id?: string
}

const sellerTabs: { key: SellerTab; label: string }[] = [
  { key: 'LIVE', label: 'Live' },
  { key: 'SCHEDULED', label: 'Upcoming' },
  { key: 'ENDED', label: 'Ended' },
  { key: 'CANCELLED', label: 'Cancelled' },
]

function emptyTabMessage(tab: SellerTab): string {
  switch (tab) {
    case 'LIVE':
      return 'No live lots right now. Check Upcoming or Ended for your listings.'
    case 'SCHEDULED':
      return 'No upcoming lots.'
    case 'ENDED':
      return 'No ended lots on this tab.'
    case 'CANCELLED':
      return 'No cancelled lots on this tab.'
  }
}

export function Seller() {
  const { user } = useSession()
  const { showToast } = useToast()
  const [lotTab, setLotTab] = useState<SellerTab>('LIVE')
  const [createOpen, setCreateOpen] = useState(false)
  const lots = useQuery({
    queryKey: ['seller-lots', lotTab],
    queryFn: () => sellerAuctions(lotTab),
    enabled: !!user && user.role === 'SELLER',
  })

  const { chartRows, chartMax } = useMemo(() => {
    if (lotTab !== 'ENDED') return { chartRows: [], chartMax: 0 }
    const endedRows = (lots.data?.items ?? []) as SellerRow[]
    const rows = endedRows
      .filter((r) => r.display_status === 'CLOSED')
      .map((r) => {
        const money = r.current_bid ?? r.opening_bid
        return { id: r.id, title: r.item.title, cents: money.cents }
      })
    const max = rows.reduce((m, row) => Math.max(m, row.cents), 0)
    return { chartRows: rows, chartMax: max }
  }, [lotTab, lots.data?.items])

  if (!user || user.role !== 'SELLER') {
    return <p className="text-muted">Dashboard requires a seller account.</p>
  }

  const counts = lots.data?.counts
  const items = lots.data?.items ?? []
  const showEmpty = !lots.isLoading && !lots.isError && items.length === 0

  const tabLabels = sellerTabs.map((t) => {
    const n =
      t.key === 'LIVE'
        ? counts?.live
        : t.key === 'SCHEDULED'
          ? counts?.scheduled
          : t.key === 'ENDED'
            ? counts?.ended
            : counts?.cancelled
    return {
      key: t.key,
      label: n !== undefined ? `${t.label} (${n})` : t.label,
    }
  })

  return (
    <div className="space-y-8">
      <PageHeading
        title="Dashboard"
        subtitle="Manage lots, proceeds, and new listings."
        action={
          <Button variant="secondary" onClick={() => setCreateOpen(true)}>
            New lot
          </Button>
        }
      />

      {createOpen ? (
        <CreateLotModal
          onClose={() => setCreateOpen(false)}
          onPublished={() => {
            setLotTab('SCHEDULED')
            showToast('Lot published. It goes live in about 5 minutes and appears under Upcoming.')
          }}
        />
      ) : null}

      <section className="space-y-8">
        {lots.data && (
          <Banner variant="info">
            Total received ·{' '}
            <Money value={{ cents: lots.data.total_received_cents, currency: 'USD' }} />
          </Banner>
        )}
        <TabNav tabs={tabLabels} active={lotTab} onChange={setLotTab} />
        {lotTab === 'ENDED' && chartRows.length > 0 && chartMax > 0 && (
          <Card className="space-y-3">
            <h3 className="font-semibold text-text">Proceeds by lot</h3>
            <ul className="space-y-3">
              {chartRows.map((row) => (
                <li key={row.id} className="space-y-1">
                  <div className="flex items-center justify-between gap-2 text-sm">
                    <span className="truncate text-text">{row.title}</span>
                    <Money value={{ cents: row.cents, currency: 'USD' }} />
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-brand-soft">
                    <div
                      className="h-full rounded-full bg-brand"
                      style={{ width: `${Math.round((row.cents / chartMax) * 100)}%` }}
                    />
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        )}
        {lots.isLoading && <p className="text-muted">Loading…</p>}
        {lots.isError && <p className="text-danger">Could not load your lots.</p>}
        {showEmpty && <p className="text-muted">{emptyTabMessage(lotTab)}</p>}
        <ul className="flex flex-col gap-4">
          {items.map((row) => {
            const r = row as SellerRow
            const amount = r.current_bid ?? r.opening_bid
            const count = r.bid_count ?? 0
            const receiptId = r.receipt_id
            return (
              <AuctionListRow
                key={r.id}
                displayStatus={r.display_status}
                displayNo={r.display_no}
                title={r.item.title}
                imageUrl={r.item.image_url}
                amount={amount}
                bidCount={count}
                actions={
                  <>
                    <ButtonLink to={`/lots/${r.id}`} variant="primary" className="w-full">
                      Manage lot
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
      </section>
    </div>
  )
}
