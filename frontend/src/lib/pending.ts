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

export function clearPending(actorId: string, key: string): void {
  try {
    localStorage.removeItem(storageKey(actorId, key))
  } catch {
    /* ignore */
  }
}

export function listPending(actorId: string): PendingRecord[] {
  const prefix = storageKey(actorId, '')
  const out: PendingRecord[] = []
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)
      if (!k?.startsWith(prefix)) continue
      const raw = localStorage.getItem(k)
      if (!raw) continue
      out.push(JSON.parse(raw) as PendingRecord)
    }
  } catch {
    /* ignore */
  }
  return out
}
