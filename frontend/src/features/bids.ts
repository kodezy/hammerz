import { api } from '../lib/http'
import type { DisplayStatus, Money, Position } from '../lib/types'

export type MyBidsTab = 'ACTIVE' | 'WON' | 'PAST'

export type MyBidRow = {
  id: string
  display_no: number
  display_status: DisplayStatus
  position: Position
  item: { title: string; image_url: string | null }
  current_bid: Money | null
  opening_bid: Money
  bid_count?: number
  user_last_bid?: Money
  receipt_id?: string
}

export type MyBidsResponse = {
  items: MyBidRow[]
  counts: { active: number; won: number; past: number }
}

export async function listMyBids(tab: MyBidsTab, limit = 20): Promise<MyBidsResponse> {
  return api<MyBidsResponse>(`/me/bids?tab=${tab}&limit=${limit}`)
}
