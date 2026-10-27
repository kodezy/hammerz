import type { Position } from '../lib/types'

const styles: Record<string, string> = {
  LEADING: 'bg-success-soft text-success',
  OUTBID: 'bg-warning-soft text-warning',
}

const labels: Record<string, string> = {
  LEADING: 'Leading',
  OUTBID: 'Outbid',
}

export function PositionBadge({ position }: { position: Position }) {
  const label = labels[position]
  if (!label) return null
  const cls = styles[position] ?? 'bg-brand-soft text-brand'
  return (
    <span className={`inline-flex h-7 items-center rounded-full px-3 text-xs font-semibold ${cls}`}>
      {label}
    </span>
  )
}
