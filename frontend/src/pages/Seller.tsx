import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState, type FormEvent } from 'react'
import { useSession } from '../app/session'
import { useToast } from '../app/toast'
import { AuctionListRow } from '../components/AuctionListRow'
import { Banner } from '../components/Banner'
import { Button, ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { PageHeading } from '../components/PageHeading'
import { TabNav } from '../components/TabNav'
import { TextField } from '../components/TextField'
import { searchCatalog, type CatalogItem } from '../features/catalog'
import { createLot, sellerAuctions } from '../features/lots'
import { httpErrorMessage } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'
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

const CATALOG_INPUT_ID = 'seller-catalog-q'

export function Seller() {
  const { user } = useSession()
  const { showToast } = useToast()
  const qc = useQueryClient()
  const [lotTab, setLotTab] = useState<SellerTab>('LIVE')
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')
  const catalog = useQuery({
    queryKey: ['catalog', search],
    queryFn: () => searchCatalog(search),
    enabled: !!user && user.role === 'SELLER' && search.length > 0,
  })
  const lots = useQuery({
    queryKey: ['seller-lots', lotTab],
    queryFn: () => sellerAuctions(lotTab),
    enabled: !!user && user.role === 'SELLER',
  })
  const [opening, setOpening] = useState('100')
  const [increment, setIncrement] = useState('10')
  const [selected, setSelected] = useState<CatalogItem | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)

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
    return <p className="text-muted">Seller dashboard requires a seller account.</p>
  }

  const counts = lots.data?.counts

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

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    if (!selected) return
    const openCents = parseDollarsToCents(opening)
    const incCents = parseDollarsToCents(increment)
    if (!openCents || !incCents) {
      setError('Invalid amounts')
      return
    }
    const starts = new Date()
    starts.setMinutes(starts.getMinutes() + 5)
    const ends = new Date(starts)
    ends.setHours(ends.getHours() + 2)
    setPublishing(true)
    try {
      await createLot({
        external_id: selected.external_id,
        opening_bid_cents: openCents,
        minimum_increment_cents: incCents,
        starts_at: starts.toISOString(),
        ends_at: ends.toISOString(),
      })
      setSelected(null)
      setQ('')
      setSearch('')
      setError(null)
      setLotTab('SCHEDULED')
      showToast('Lot published. It goes live in about 5 minutes and appears under Upcoming.')
      await qc.invalidateQueries({ queryKey: ['seller-lots'] })
      qc.removeQueries({ queryKey: ['catalog'] })
    } catch (err) {
      setError(httpErrorMessage(err, 'Create failed'))
    } finally {
      setPublishing(false)
    }
  }

  const catalogItems = catalog.data?.items ?? []
  const searched = search.length > 0

  return (
    <div className="space-y-8">
      <PageHeading
        title="Seller dashboard"
        subtitle="Manage lots, proceeds, and new listings."
      />

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
        <ul className="flex flex-col gap-4">
          {lots.data?.items.map((row) => {
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

      <section>
        <Card>
          <h2 className="font-semibold text-text">Create a lot</h2>
          <p className="mt-1 mb-4 text-sm text-muted">
            Search the Met collection, select a work, then set the opening bid. New lots start in
            about 5 minutes and appear under Upcoming.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const needle = q.trim()
              if (!needle) return
              setError(null)
              setSelected(null)
              setSearch(needle)
            }}
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
          >
            <div className="min-w-0 flex-1">
              <TextField
                id={CATALOG_INPUT_ID}
                label="Search Met collection"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Artist or title"
                autoComplete="off"
                required
              />
            </div>
            <Button type="submit" className="shrink-0 sm:w-[244px]" disabled={catalog.isFetching}>
              Search
            </Button>
          </form>
          {searched && catalog.isFetching && catalogItems.length === 0 && (
            <p className="mt-4 text-sm text-muted">Searching…</p>
          )}
          {searched && catalog.isError && (
            <p className="mt-4 text-sm text-danger">Could not search the catalog.</p>
          )}
          {searched && catalog.isSuccess && !catalog.isFetching && catalogItems.length === 0 && (
            <p className="mt-4 text-sm text-muted">
              No matching works. Try another artist or title.
            </p>
          )}
          {searched && catalogItems.length > 0 && (
            <ul className="mt-4 space-y-2">
              {catalogItems.map((item) => (
                <li key={item.external_id}>
                  <button
                    type="button"
                    onClick={() => {
                      setSelected(item)
                      setError(null)
                    }}
                    className={`w-full rounded-lg border px-3 py-2.5 text-left text-sm ${
                      selected?.external_id === item.external_id
                        ? 'border-brand bg-brand-soft'
                        : 'border-border'
                    }`}
                  >
                    {item.title} — {item.artist ?? 'Not stated'}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {selected && (
            <form onSubmit={onCreate} className="mt-6 space-y-4 border-t border-border pt-6">
              <p className="text-sm text-text">
                Selected · {selected.title}
                {selected.artist ? ` — ${selected.artist}` : ''}
              </p>
              <TextField
                label="Opening bid (USD)"
                value={opening}
                onChange={(e) => setOpening(e.target.value)}
              />
              <TextField
                label="Minimum increment (USD)"
                value={increment}
                onChange={(e) => setIncrement(e.target.value)}
              />
              {error && <Banner variant="danger">{error}</Banner>}
              <Button type="submit" disabled={publishing}>
                {publishing ? 'Publishing…' : 'Publish lot'}
              </Button>
            </form>
          )}
        </Card>
      </section>
    </div>
  )
}
