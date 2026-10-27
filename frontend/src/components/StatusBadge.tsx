import { lotStatusLabel } from '../lib/display'
import type { DisplayStatus } from '../lib/types'

const listStyles: Record<string, string> = {
  LIVE: 'bg-brand-soft text-brand',
  SCHEDULED: 'bg-brand-soft text-brand',
  FINALIZING: 'bg-warning-soft text-warning',
  CLOSED: 'bg-muted/15 text-muted',
  CANCELLED: 'bg-danger-soft text-danger',
}

const pillStyles: Record<string, string> = {
  LIVE: 'bg-success-soft text-success',
  SCHEDULED: 'bg-brand-soft text-brand',
  FINALIZING: 'bg-warning-soft text-warning',
  CLOSED: 'bg-muted/15 text-muted',
  CANCELLED: 'bg-danger-soft text-danger',
  SETTLED: 'bg-success-soft text-success',
  VERIFIED: 'bg-success-soft text-success',
}

export function StatusBadge({
  status,
  variant = 'pill',
}: {
  status: DisplayStatus | string
  variant?: 'pill' | 'list'
}) {
  const label = lotStatusLabel(status)
  const styles = variant === 'list' ? listStyles : pillStyles
  const cls = styles[status] ?? 'bg-brand-soft text-brand'
  return (
    <span
      className={`inline-flex h-7 items-center rounded-full px-3 text-xs font-semibold ${cls}`}
    >
      {label}
    </span>
  )
}
