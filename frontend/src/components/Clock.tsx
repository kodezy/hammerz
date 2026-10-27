import { useEffect, useMemo, useRef, useState } from 'react'
import { clockSkewMs, formatClockDigits, remainingMs } from '../lib/time'

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
  const skewMs = useMemo(() => clockSkewMs(Date.now(), serverTime), [serverTime])
  const [now, setNow] = useState(() => Date.now())
  const elapsedNotified = useRef(false)

  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 250)
    return () => window.clearInterval(id)
  }, [])

  const ms = remainingMs(endsAt, now, skewMs)

  useEffect(() => {
    elapsedNotified.current = false
  }, [endsAt])

  useEffect(() => {
    if (displayStatus !== 'LIVE') return
    if (ms > 0 || elapsedNotified.current) return
    elapsedNotified.current = true
    onElapsed?.()
  }, [displayStatus, ms, onElapsed])

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
