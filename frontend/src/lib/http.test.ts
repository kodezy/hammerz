import assert from 'node:assert/strict'
import { HttpError, apiErrorBody, httpErrorMessage, isOperationPending, isPendingApiResponse } from './http.ts'

assert.equal(isPendingApiResponse(202, { code: 'OPERATION_PENDING', message: 'Operation pending' }), true)
assert.equal(isPendingApiResponse(200, { code: 'OPERATION_PENDING', message: 'x' }), true)
assert.equal(isPendingApiResponse(409, { code: 'BID_TOO_LOW', message: 'Bid too low' }), false)
assert.equal(isPendingApiResponse(200, { token: 'x' }), false)

const res202 = new Response(null, { status: 202, statusText: 'Accepted' })
assert.deepEqual(apiErrorBody(null, res202), {
  code: 'OPERATION_PENDING',
  message: 'Accepted',
})
assert.deepEqual(
  apiErrorBody({ code: 'OPERATION_PENDING', message: 'Deposit still pending' }, res202),
  { code: 'OPERATION_PENDING', message: 'Deposit still pending' },
)

const pendingErr = new HttpError(202, { code: 'OPERATION_PENDING', message: 'Operation pending' })
assert.equal(isOperationPending(pendingErr), true)
assert.equal(httpErrorMessage(pendingErr, 'x'), 'Confirmation pending')
assert.equal(isOperationPending(new HttpError(409, { code: 'BID_TOO_LOW', message: 'x' })), false)
assert.equal(isOperationPending(new Error('other')), false)

console.log('ok')
