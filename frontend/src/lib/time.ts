export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function formatEndsLine(iso: string): string {
  const d = new Date(iso)
  const date = d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  })
  return `Ends ${date}`
}

export function formatClockDigits(ms: number): string {
  if (ms <= 0) return '00 : 00 : 00'
  const totalSec = Math.floor(ms / 1000)
  const h = Math.floor(totalSec / 3600)
  const m = Math.floor((totalSec % 3600) / 60)
  const s = totalSec % 60
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(h)} : ${pad(m)} : ${pad(s)}`
}

export function clockSkewMs(clientNow: number, serverTimeIso: string): number {
  return clientNow - new Date(serverTimeIso).getTime()
}

export function remainingMs(endsAt: string, clientNow: number, skewMs: number): number {
  return new Date(endsAt).getTime() - (clientNow - skewMs)
}

export function formatBidTimestamp(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    timeZoneName: 'short',
  })
}
