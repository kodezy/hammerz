import { api } from '../lib/http'

export async function getReceipt(id: string) {
  return api<Record<string, unknown>>(`/receipts/${id}`)
}
