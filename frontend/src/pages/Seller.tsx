import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { useSession } from '../app/session'
import { Banner } from '../components/Banner'
import { Card } from '../components/Card'
import { Money } from '../components/Money'
import { searchCatalog } from '../features/catalog'
import { createLot, sellerAuctions } from '../features/lots'
import type { CatalogItem } from '../features/catalog'
import { HttpError } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'

export function Seller() {
  const { user } = useSession()
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [search, setSearch] = useState('')
  const catalog = useQuery({
    queryKey: ['catalog', search],
    queryFn: () => searchCatalog(search),
    enabled: !!user && user.role === 'SELLER' && search.length > 0,
  })
  const lots = useQuery({
    queryKey: ['seller-lots'],
    queryFn: () => sellerAuctions('ALL'),
    enabled: !!user && user.role === 'SELLER',
  })
  const [opening, setOpening] = useState('100')
  const [increment, setIncrement] = useState('10')
  const [selected, setSelected] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  if (!user || user.role !== 'SELLER') {
    return <p className="text-muted">Seller dashboard requires a seller account.</p>
  }

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
    try {
      await createLot({
        external_id: selected,
        opening_bid_cents: openCents,
        minimum_increment_cents: incCents,
        starts_at: starts.toISOString(),
        ends_at: ends.toISOString(),
      })
      setSelected(null)
      await qc.invalidateQueries({ queryKey: ['seller-lots'] })
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'Create failed')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Seller dashboard</h1>
      {lots.data && (
        <p className="text-muted">
          Total received:{' '}
          <Money value={{ cents: lots.data.total_received_cents, currency: 'USD' }} />
        </p>
      )}
      <Card>
        <h2 className="mb-2 font-medium">Catalog search</h2>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            setSearch(q)
          }}
          className="flex gap-2"
        >
          <input
            className="flex-1 rounded-lg border border-control-border px-3 py-2"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search Met collection"
          />
          <button type="submit" className="rounded-lg bg-action px-4 py-2 text-on-action">
            Search
          </button>
        </form>
        {catalog.isLoading && <p className="mt-2 text-sm">Loading…</p>}
        <ul className="mt-3 space-y-2">
          {catalog.data?.items.map((item: CatalogItem) => (
            <li key={item.external_id}>
              <button
                type="button"
                onClick={() => setSelected(item.external_id)}
                className={`w-full rounded-lg border px-3 py-2 text-left ${
                  selected === item.external_id ? 'border-brand bg-brand-soft' : 'border-border'
                }`}
              >
                {item.title} — {item.artist ?? 'Not stated'}
              </button>
            </li>
          ))}
        </ul>
        {selected && (
          <form onSubmit={onCreate} className="mt-4 space-y-2 border-t border-border pt-4">
            <label className="block text-sm">
              Opening bid (USD)
              <input
                className="mt-1 w-full rounded-lg border border-control-border px-3 py-2"
                value={opening}
                onChange={(e) => setOpening(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              Minimum increment (USD)
              <input
                className="mt-1 w-full rounded-lg border border-control-border px-3 py-2"
                value={increment}
                onChange={(e) => setIncrement(e.target.value)}
              />
            </label>
            {error && <Banner variant="danger">{error}</Banner>}
            <button type="submit" className="rounded-lg bg-action px-4 py-2 text-on-action">
              Create lot
            </button>
          </form>
        )}
      </Card>
      <section>
        <h2 className="mb-2 font-medium">Your lots</h2>
        <ul className="space-y-2">
          {lots.data?.items.map((row) => (
            <li key={String(row.id)}>
              <Link to={`/lots/${row.id}`} className="text-brand hover:underline">
                Lot {String(row.display_no).padStart(3, '0')} — {String((row.item as { title: string })?.title)}
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}
