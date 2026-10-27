import { useEffect, useState } from 'react'
import { formatClockDigits, msUntil } from '../lib/time'

export function Clock({
  endsAt,
  serverTime,
  displayStatus,
  onElapsed,
}: {
  endsAt: string
  serverTime: string
  displayStatus: string
  onElapsed?: () => void
}) {
  const offset = Date.now() - new Date(serverTime).getTime()
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(id)
  }, [])

  const serverNow = new Date(now - offset)
  const ms = msUntil(endsAt, serverNow)

  useEffect(() => {
    if (ms <= 0) onElapsed?.()
  }, [ms, onElapsed])

  if (displayStatus === 'FINALIZING') {
    return <span className="font-medium text-warning">Finalizing</span>
  }
  if (displayStatus !== 'LIVE') {
    return null
  }
  if (ms <= 0) {
    return <span className="font-medium text-warning">Finalizing</span>
  }
  return (
    <span className="font-display text-4xl tabular-nums tracking-wide text-text">
      {formatClockDigits(ms)}
    </span>
  )
}
