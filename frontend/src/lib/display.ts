import type { AuditStatus, DisplayStatus } from './types'

export function parseAuditStatus(value: unknown): AuditStatus | null {
  if (value === 'VERIFIED' || value === 'TAMPERED' || value === 'UNVERIFIABLE') return value
  return null
}

export function integrityBanner(status: AuditStatus): {
  variant: 'success' | 'warning' | 'danger'
  title: string
  body: string
} {
  if (status === 'VERIFIED') {
    return {
      variant: 'success',
      title: 'History verified',
      body: "This lot's recorded events match the independent journal.",
    }
  }
  if (status === 'TAMPERED') {
    return {
      variant: 'danger',
      title: 'History does not match',
      body: 'Do not treat this as a verified sale. The public record diverges from the independent journal.',
    }
  }
  return {
    variant: 'warning',
    title: 'Integrity cannot be confirmed',
    body: 'Audit evidence is unavailable or incomplete. This is not a successful verification.',
  }
}

export function auditEventLabel(type: string): string {
  switch (type) {
    case 'AUCTION_CREATED':
      return 'Lot created'
    case 'BID_ACCEPTED':
      return 'Bid accepted'
    case 'AUCTION_CANCELLED':
      return 'Lot cancelled'
    case 'AUCTION_CLOSED':
      return 'Lot closed'
    default:
      return type
  }
}

export function sellerCanCancel(status: DisplayStatus | string): boolean {
  return status === 'LIVE' || status === 'SCHEDULED'
}

export function lotStatusLabel(status: DisplayStatus | string): string {
  switch (status) {
    case 'SCHEDULED':
      return 'Upcoming'
    case 'LIVE':
      return 'Live'
    case 'FINALIZING':
      return 'Finalizing'
    case 'CLOSED':
      return 'Ended'
    case 'CANCELLED':
      return 'Cancelled'
    case 'SETTLED':
      return 'Settled'
    default:
      return String(status)
  }
}
