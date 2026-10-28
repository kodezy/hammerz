import type { ReactNode } from 'react'
import { StatusBadge } from './StatusBadge'
import { ButtonLink } from './Button'
import { acceptedBidsLine } from '../lib/lotCopy'
import type { DisplayStatus, Money } from '../lib/types'

export function AuctionListRow({
  displayStatus,
  displayNo,
  title,
  imageUrl,
  amount,
  bidCount,
  ctaTo,
  ctaLabel = 'View auction',
  badges,
  meta,
  actions,
}: {
  displayStatus: DisplayStatus | string
  displayNo: number
  title: string
  imageUrl: string | null
  amount: Money
  bidCount: number
  ctaTo?: string
  ctaLabel?: string
  badges?: ReactNode
  meta?: ReactNode
  actions?: ReactNode
}) {
  const right =
    actions ??
    (ctaTo ? (
      <ButtonLink to={ctaTo} className="w-full shrink-0 sm:w-[200px]">
        {ctaLabel}
      </ButtonLink>
    ) : null)

  return (
    <li
      className="flex min-h-[180px] flex-col gap-4 rounded-xl border border-border bg-surface p-[15px] sm:flex-row sm:items-center"
    >
      <div className="relative h-[148px] w-full shrink-0 overflow-hidden rounded-[10px] bg-bg sm:w-[170px]">
        {imageUrl ? (
          <img src={imageUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <span className="flex h-full items-center justify-center text-sm text-muted">No image</span>
        )}
      </div>
      <div className="min-w-0 flex-1 space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          {badges ?? <StatusBadge status={displayStatus} variant="list" />}
        </div>
        <h3 className="font-display text-[25px] leading-tight text-text">{title}</h3>
        <p className="text-[13px] text-muted">{acceptedBidsLine(amount, bidCount)}</p>
        {meta}
        <p className="font-display text-[13px] text-muted">
          Lot {String(displayNo).padStart(3, '0')}
        </p>
      </div>
      <div className="flex w-full shrink-0 flex-col gap-2 sm:w-[200px]">{right}</div>
    </li>
  )
}
