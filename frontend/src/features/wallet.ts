import { api } from '../lib/http'
import type { Money } from '../lib/types'

export type WalletCommitment = {
  auction_id: string
  display_no: number
  title: string
  reserved: Money
}

export type WalletSnapshot = {
  total: Money
  committed: Money
  available: Money
  commitments?: WalletCommitment[]
  confirmation_pending?: boolean
}

export async function getWallet() {
  return api<WalletSnapshot>('/wallet')
}

export async function deposit(amountCents: number, idempotencyKey: string) {
  return api('/wallet/deposits', {
    method: 'POST',
    headers: { 'Idempotency-Key': idempotencyKey },
    json: { amount_cents: amountCents },
  })
}
