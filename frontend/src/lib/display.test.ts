import assert from 'node:assert/strict'
import { sellerCanCancel } from './display.ts'

assert.equal(sellerCanCancel('LIVE'), true)
assert.equal(sellerCanCancel('SCHEDULED'), true)
assert.equal(sellerCanCancel('CLOSED'), false)
assert.equal(sellerCanCancel('FINALIZING'), false)
assert.equal(sellerCanCancel('CANCELLED'), false)

console.log('ok')
