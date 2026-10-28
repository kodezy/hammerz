export type Role = 'SELLER' | 'BIDDER'
export type DisplayStatus =
  | 'SCHEDULED'
  | 'LIVE'
  | 'FINALIZING'
  | 'CLOSED'
  | 'CANCELLED'
export type Position =
  | 'NOT_PARTICIPATING'
  | 'LEADING'
  | 'OUTBID'
  | 'WON'
  | 'LOST'
  | 'CANCELLED'
export type Money = { cents: number; currency: 'USD' }

export type AuditStatus = 'VERIFIED' | 'TAMPERED' | 'UNVERIFIABLE'

export type User = { id: string; email: string; role: Role }

export type ApiError = { code: string; message: string; request_id?: string }
