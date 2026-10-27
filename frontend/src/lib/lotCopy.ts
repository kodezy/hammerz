import { formatMoney } from './money'
import type { Money } from './types'

export function lotListingTitle(displayNo: number, title: string): string {
  return `Lot ${String(displayNo).padStart(3, '0')} · ${title}`
}

export function lotArtworkLine(
  displayNo: number,
  artist: string | null | undefined,
  year?: string | number | null,
): string {
  const who = artist?.trim() || 'Artist not stated'
  const y = year != null && String(year).trim() ? String(year).trim() : null
  return y
    ? `Lot ${String(displayNo).padStart(3, '0')} · ${who} · ${y}`
    : `Lot ${String(displayNo).padStart(3, '0')} · ${who}`
}

export function receiptCatalogLine(meta: {
  artist?: string | null
  object_begin_date?: string | number | null
  external_id?: string | null
}): string {
  const artist = meta.artist?.trim() || 'Artist not stated'
  const year =
    meta.object_begin_date != null && String(meta.object_begin_date).trim()
      ? String(meta.object_begin_date)
      : null
  const objectId = meta.external_id?.trim()
  const parts = [artist, year, 'The Met', objectId ? `Object ${objectId}` : null].filter(
    Boolean,
  ) as string[]
  return parts.join(' · ')
}

export function acceptedBidsLine(amount: Money | null | undefined, count: number): string {
  if (!amount || count <= 0) return 'No accepted bids yet'
  return `${formatMoney(amount)} · ${count} accepted bid${count === 1 ? '' : 's'}`
}

export function leaderLine(alias: string | null | undefined, count: number): string {
  if (!alias) return 'No leader yet'
  return `Leader ${alias} · ${count} accepted bid${count === 1 ? '' : 's'}`
}

export function minimumBidLine(nextMin: Money, increment: Money): string {
  return `Minimum ${formatMoney(nextMin)} · Increment ${formatMoney(increment)}`
}
