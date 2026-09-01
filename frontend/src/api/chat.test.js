import test from 'node:test'
import assert from 'node:assert/strict'

import { ChatStreamError, processChatStream } from './chat.js'


function responseWithSse(text) {
  return new Response(text, {
    headers: { 'Content-Type': 'text/event-stream' }
  })
}


test('server error events are propagated instead of swallowed as parse errors', async () => {
  const response = responseWithSse(
    'data: {"type":"session","thread_id":"thread-1"}\n\n' +
    'data: {"type":"error","code":"SANDBOX_UNAVAILABLE","message":"沙箱恢复中","retryable":true,"thread_id":"thread-1"}\n\n'
  )

  await assert.rejects(
    processChatStream(response, null, {}, '', [], []),
    error => {
      assert.ok(error instanceof ChatStreamError)
      assert.equal(error.code, 'SANDBOX_UNAVAILABLE')
      assert.equal(error.retryable, true)
      assert.equal(error.threadId, 'thread-1')
      return true
    }
  )
})


test('a stream ending without done is reported as incomplete', async () => {
  const response = responseWithSse(
    'data: {"type":"session","thread_id":"thread-2"}\n\n' +
    'data: {"type":"token","content":"partial","source":"main"}\n\n'
  )

  await assert.rejects(
    processChatStream(response, null, {}, '', [], []),
    error => {
      assert.equal(error.code, 'STREAM_INCOMPLETE')
      assert.equal(error.retryable, false)
      assert.equal(error.partialContent, 'partial')
      assert.equal(error.threadId, 'thread-2')
      return true
    }
  )
})


test('malformed events are skipped without hiding a later done event', async () => {
  const response = responseWithSse(
    'data: not-json\n\n' +
    'data: {"type":"done","thread_id":"thread-3","content":"ok"}\n\n'
  )

  const result = await processChatStream(response, null, {}, '', [], [])
  assert.equal(result.thread_id, 'thread-3')
  assert.equal(result.content, 'ok')
})
