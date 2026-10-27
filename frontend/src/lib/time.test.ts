import assert from 'node:assert/strict'
import { clockSkewMs, remainingMs } from './time.ts'

const endsAt = '2026-01-01T00:01:00.000Z'
const serverTime = '2026-01-01T00:00:00.000Z'
const t0 = Date.parse(serverTime) + 100
const skew = clockSkewMs(t0, serverTime)

assert.equal(remainingMs(endsAt, t0, skew), 60_000)

const later = t0 + 3_000
assert.equal(
  remainingMs(endsAt, later, skew),
  57_000,
  'stable skew must let the countdown tick with local time',
)

const recomputedSkew = clockSkewMs(later, serverTime)
assert.equal(
  remainingMs(endsAt, later, recomputedSkew),
  60_000,
  'recomputing skew every tick freezes remaining time',
)

console.log('ok')
