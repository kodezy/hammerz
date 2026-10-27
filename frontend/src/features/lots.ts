import { api } from '../lib/http'
import type { DisplayStatus, Money, Position } from '../lib/types'

export type AuctionSummary = {
  id: string
  display_no: number
  display_status: DisplayStatus
  bid_count?: number
  leader_alias?: string | null
  cancel_reason?: string | null
  receipt_id?: string | null
  item: {
    title: string
    artist: string | null
    image_url: string | null
    description?: string | null
    attribution?: string | null
    object_url?: string | null
    external_id?: string | number
    object_begin_date?: string | number | null
  }
  current_bid: Money | null
  opening_bid: Money
  minimum_increment: Money
  ends_at: string
  starts_at: string
  version: number
  server_time: string
  confirmation_pending?: boolean
  viewer_is_owner?: boolean
}

export type BidRow = {
  sequence: number
  amount_cents: number
  bidder_alias: string
  accepted_at: string
}

export async function listAuctions(status: 'LIVE' | 'SCHEDULED' | 'ENDED', offset = 0) {
  return api<{
    items: AuctionSummary[]
    counts: { scheduled: number; live: number; ended: number }
    total: number
  }>(`/auctions?status=${status}&offset=${offset}&limit=20`)
}

export async function getAuction(id: string) {
  return api<AuctionSummary & Record<string, unknown>>(`/auctions/${id}`)
}

export async function listBids(auctionId: string, beforeSequence?: number) {
  const qs = new URLSearchParams({ limit: '20' })
  if (beforeSequence !== undefined) qs.set('before_sequence', String(beforeSequence))
  return api<{ items: BidRow[] }>(`/auctions/${auctionId}/bids?${qs}`)
}

export async function participantStatus(auctionId: string) {
  return api<{ position: Position; reserved_cents?: number | null }>(
    `/me/auctions/${auctionId}/status`,
  )
}

export async function placeBid(auctionId: string, amountCents: number, idempotencyKey: string) {
  return api(`/auctions/${auctionId}/bids`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    json: { amount_cents: amountCents },
  })
}

export async function cancelLot(auctionId: string, reason: string | null, idempotencyKey: string) {
  return api(`/auctions/${auctionId}/cancel`, {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    json: { reason },
  })
}

export async function createLot(body: {
  external_id: string
  opening_bid_cents: number
  minimum_increment_cents: number
  starts_at: string
  ends_at: string
}) {
  return api('/auctions', { method: 'POST', json: body })
}

export async function sellerAuctions(status = 'ALL') {
  return api<{
    items: Record<string, unknown>[]
    total_received_cents: number
    counts?: { live: number; scheduled: number; cancelled: number; ended: number }
  }>(`/seller/auctions?status=${status}&limit=20`)
}
