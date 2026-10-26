export type PendingRecord = {
  key: string
  method: string
  path: string
  body: unknown
  actorId: string
  createdAt: string
  operationId?: string
}

function storageKey(actorId: string, key: string): string {
  return `hammerz:pending:${actorId}:${key}`
}

export function savePending(actorId: string, record: PendingRecord): void {
  try {
    localStorage.setItem(storageKey(actorId, record.key), JSON.stringify(record))
  } catch {
    /* ignore */
  }
}

export function loadPending(actorId: string, key: string): PendingRecord | null {
  try {
    const raw = localStorage.getItem(storageKey(actorId, key))
    if (!raw) return null
    return JSON.parse(raw) as PendingRecord
  } catch {
    return null
  }
}

export function clearPending(actorId: string, key: string): void {
  try {
    localStorage.removeItem(storageKey(actorId, key))
  } catch {
    /* ignore */
  }
}
