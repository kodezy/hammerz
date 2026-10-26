export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function msUntil(iso: string, serverNow: Date): number {
  return new Date(iso).getTime() - serverNow.getTime()
}
