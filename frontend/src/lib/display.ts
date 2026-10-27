import type { DisplayStatus } from './types'

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

export function integrityLabel(status: string): string {
  if (status === 'VERIFIED') return 'Verified'
  if (status === 'TAMPERED') return 'Changes detected'
  return 'Unable to verify'
}
