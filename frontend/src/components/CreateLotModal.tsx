import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState, type FormEvent } from 'react'
import { Banner } from './Banner'
import { Button } from './Button'
import { Modal } from './Modal'
import { TextField } from './TextField'
import { searchCatalog, type CatalogItem } from '../features/catalog'
import { createLot } from '../features/lots'
import { httpErrorMessage } from '../lib/http'
import { parseDollarsToCents } from '../lib/money'

function CatalogImage({
  src,
  objectFit,
  wrapperClassName,
  imgClassName = '',
}: {
  src: string
  objectFit: 'cover' | 'contain'
  wrapperClassName: string
  imgClassName?: string
}) {
  const [ready, setReady] = useState(false)

  return (
    <div className={`relative overflow-hidden bg-border/40 ${wrapperClassName}`}>
      {!ready ? (
        <div className="absolute inset-0 animate-pulse bg-brand-soft" aria-hidden />
      ) : null}
      <img
        src={src}
        alt=""
        loading="eager"
        decoding="async"
        onLoad={() => setReady(true)}
        onError={() => setReady(true)}
        className={`h-full w-full transition-opacity duration-200 ${objectFit === 'cover' ? 'object-cover' : 'object-contain'} ${ready ? 'opacity-100' : 'opacity-0'} ${imgClassName}`}
      />
    </div>
  )
}

export function CreateLotModal({
  onClose,
  onPublished,
}: {
  onClose: () => void
  onPublished: () => void
}) {
  const qc = useQueryClient()
  const [q, setQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [opening, setOpening] = useState('100')
  const [increment, setIncrement] = useState('10')
  const [selected, setSelected] = useState<CatalogItem | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [publishing, setPublishing] = useState(false)

  useEffect(() => {
    const id = window.setTimeout(() => setDebouncedQ(q.trim()), 500)
    return () => window.clearTimeout(id)
  }, [q])

  const catalog = useQuery({
    queryKey: ['catalog', debouncedQ],
    queryFn: ({ signal }) => searchCatalog(debouncedQ, 0, 10, signal),
    enabled: debouncedQ.length > 0,
    retry: false,
    staleTime: 60_000,
    refetchOnWindowFocus: false,
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
      await qc.invalidateQueries({ queryKey: ['seller-lots'] })
      qc.removeQueries({ queryKey: ['catalog'] })
      onPublished()
      onClose()
    } catch (err) {
      setError(httpErrorMessage(err, 'Create failed'))
      setPublishing(false)
    }
  }

  const catalogItems = catalog.data?.items ?? []

  return (
    <Modal open onClose={onClose} title="Create a lot">
      <p className="mt-1 mb-4 text-sm text-muted">
        Search the Met collection, select a work, then set the opening bid. New lots start in about
        5 minutes and appear under Upcoming.
      </p>
      <TextField
        label="Search Met collection"
        value={q}
        onChange={(e) => {
          setQ(e.target.value)
          setSelected(null)
          setError(null)
        }}
        placeholder="Artist or title"
        autoComplete="off"
      />
      {debouncedQ.length > 0 && catalog.isFetching && catalogItems.length === 0 && (
        <p className="mt-4 text-sm text-muted">Searching…</p>
      )}
      {debouncedQ.length > 0 && catalog.isError && !catalog.isFetching && (
        <p className="mt-4 text-sm text-danger">Could not search the catalog.</p>
      )}
      {debouncedQ.length > 0 &&
        catalog.isSuccess &&
        !catalog.isFetching &&
        catalogItems.length === 0 && (
          <p className="mt-4 text-sm text-muted">No matching works. Try another artist or title.</p>
        )}
      {debouncedQ.length > 0 && catalogItems.length > 0 && (
        <ul className="mt-4 max-h-48 space-y-2 overflow-y-auto">
          {catalogItems.map((item) => (
            <li key={item.external_id}>
              <button
                type="button"
                onClick={() => {
                  setSelected(item)
                  setError(null)
                }}
                className={`flex w-full gap-3 rounded-lg border px-3 py-2.5 text-left text-sm ${
                  selected?.external_id === item.external_id
                    ? 'border-brand bg-brand-soft'
                    : 'border-border'
                }`}
              >
                {item.image_url ? (
                  <CatalogImage
                    key={item.image_url}
                    src={item.image_url}
                    objectFit="cover"
                    wrapperClassName="h-12 w-12 shrink-0 rounded-lg"
                  />
                ) : (
                  <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-bg px-0.5 text-center text-[10px] leading-tight text-muted">
                    No image
                  </div>
                )}
                <span className="min-w-0 self-center">
                  {item.title} — {item.artist ?? 'Not stated'}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {selected && (
        <form onSubmit={onCreate} className="mt-6 space-y-4 border-t border-border pt-6">
          {selected.image_url ? (
            <CatalogImage
              key={selected.image_url}
              src={selected.image_url}
              objectFit="contain"
              wrapperClassName="flex max-h-[200px] w-full items-center justify-center rounded-lg"
              imgClassName="max-h-[200px] w-full"
            />
          ) : (
            <div className="flex h-24 items-center justify-center rounded-lg bg-bg text-sm text-muted">
              No image
            </div>
          )}
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
          <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button type="button" variant="secondary" onClick={onClose} disabled={publishing}>
              Cancel
            </Button>
            <Button type="submit" disabled={publishing}>
              {publishing ? 'Publishing…' : 'Publish lot'}
            </Button>
          </div>
        </form>
      )}
    </Modal>
  )
}
