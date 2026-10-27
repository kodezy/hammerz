import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useRef, useState, type FormEvent } from 'react'
import { useSession } from '../app/session'
import { useToast } from '../app/toast'
import { AuctionListRow } from '../components/AuctionListRow'
import { Banner } from '../components/Banner'
import { Button, ButtonLink } from '../components/Button'
import { Card } from '../components/Card'
import { MarketingHero } from '../components/MarketingHero'
import { PageHeading } from '../components/PageHeading'
import { TabNav } from '../components/TabNav'
import { TextField } from '../components/TextField'
import { Money } from '../components/Money'
import { searchCatalog, type CatalogItem } from '../features/catalog'
import { createLot, sellerAuctions } from '../features/lots'
import { HttpError } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'
import type { DisplayStatus, Money as MoneyType } from '../lib/types'

type SellerTab = 'LIVE' | 'SCHEDULED' | 'ENDED'

type SellerRow = {
  id: string
  display_no: number
  display_status: DisplayStatus
  item: { title: string; image_url: string | null }
  current_bid: MoneyType | null
  opening_bid: MoneyType
  bid_count?: number
  receipt_id?: string
  cancel_reason?: string
}

const sellerTabs: { key: SellerTab; label: string }[] = [
  { key: 'LIVE', label: 'Live' },
  { key: 'SCHEDULED', label: 'Upcoming' },
  { key: 'ENDED', label: 'Ended' },
]

export function Seller() {
  const { user } = useSession()
  const { showToast } = useToast()
  const qc = useQueryClient()
  const catalogRef = useRef<HTMLDivElement>(null)
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
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)

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
          : counts?.ended
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
      showToast('Invalid amounts', 'danger')
      return
    }
    const starts = new Date()
    starts.setMinutes(starts.getMinutes() + 5)
    const ends = new Date(starts)
    ends.setHours(ends.getHours() + 2)
    setPublishing(true)
    try {
      await createLot({
        external_id: selected,
        opening_bid_cents: openCents,
        minimum_increment_cents: incCents,
        starts_at: starts.toISOString(),
        ends_at: ends.toISOString(),
      })
      setSelected(null)
      setError(null)
      setLotTab('SCHEDULED')
      showToast('Lot published. It goes live in about 5 minutes.')
      await qc.invalidateQueries({ queryKey: ['seller-lots'] })
    } catch (err) {
      const message = err instanceof HttpError ? err.message : 'Create failed'
      setError(message)
      showToast(message, 'danger')
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="space-y-10">
      <MarketingHero />
      <section className="space-y-8">
        <PageHeading
          title="Seller dashboard"
          subtitle="Manage your lots and follow every result."
          action={
            <Button type="button" onClick={() => catalogRef.current?.scrollIntoView({ behavior: 'smooth' })}>
              Create a lot
            </Button>
          }
        />
        {lots.data && (
          <Banner variant="info">
            Total received ·{' '}
            <Money value={{ cents: lots.data.total_received_cents, currency: 'USD' }} />
          </Banner>
        )}
        <TabNav tabs={tabLabels} active={lotTab} onChange={setLotTab} />
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
                    {r.cancel_reason ? (
                      <ButtonLink to={`/lots/${r.id}`} className="w-full">
                        View reason
                      </ButtonLink>
                    ) : null}
                  </>
                }
              />
            )
          })}
        </ul>
        {lots.data?.items.length === 0 && <p className="text-muted">No lots in this tab.</p>}
      </section>
      <div ref={catalogRef}>
        <Card>
          <h2 className="mb-4 font-semibold text-text">Catalog search</h2>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              setSearch(q)
            }}
            className="flex flex-col gap-3 sm:flex-row sm:items-end"
          >
            <div className="min-w-0 flex-1">
              <TextField
                label="Search Met collection"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Artist or title"
              />
            </div>
            <Button type="submit" className="shrink-0 sm:w-[244px]">Search</Button>
          </form>
          {catalog.isLoading && <p className="mt-4 text-sm text-muted">Loading…</p>}
          {catalog.isError && <p className="mt-4 text-sm text-danger">Could not search the catalog.</p>}
          {catalog.isSuccess && catalog.data.items.length === 0 && (
            <p className="mt-4 text-sm text-muted">No matching works. Try another artist or title.</p>
          )}
          <ul className="mt-4 space-y-2">
            {catalog.data?.items.map((item: CatalogItem) => (
              <li key={item.external_id}>
                <button
                  type="button"
                  onClick={() => setSelected(item.external_id)}
                  className={`w-full rounded-lg border px-3 py-2.5 text-left text-sm ${
                    selected === item.external_id ? 'border-brand bg-brand-soft' : 'border-border'
                  }`}
                >
                  {item.title} — {item.artist ?? 'Not stated'}
                </button>
              </li>
            ))}
          </ul>
          {selected && (
            <form onSubmit={onCreate} className="mt-6 space-y-4 border-t border-border pt-6">
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
      </div>
    </div>
  )
}
