import assert from 'node:assert/strict'
import { auditEventLabel, integrityBanner, parseAuditStatus, sellerCanCancel } from './display.ts'

assert.equal(sellerCanCancel('LIVE'), true)
assert.equal(sellerCanCancel('SCHEDULED'), true)
assert.equal(sellerCanCancel('CLOSED'), false)
assert.equal(sellerCanCancel('FINALIZING'), false)
assert.equal(sellerCanCancel('CANCELLED'), false)

assert.equal(parseAuditStatus('VERIFIED'), 'VERIFIED')
assert.equal(parseAuditStatus('nope'), null)
assert.equal(integrityBanner('VERIFIED').variant, 'success')
assert.equal(integrityBanner('TAMPERED').variant, 'danger')
assert.equal(integrityBanner('UNVERIFIABLE').variant, 'warning')
assert.ok(integrityBanner('TAMPERED').body.includes('not treat this as a verified sale'))
assert.equal(auditEventLabel('BID_ACCEPTED'), 'Bid accepted')
assert.equal(auditEventLabel('AUCTION_CREATED'), 'Lot created')
assert.equal(auditEventLabel('AUCTION_CANCELLED'), 'Lot cancelled')
assert.equal(auditEventLabel('AUCTION_CLOSED'), 'Lot closed')

console.log('ok')
