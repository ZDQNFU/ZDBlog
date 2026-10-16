import test from 'node:test'
import assert from 'node:assert/strict'
import { streamChat, deleteChatConversation } from './index.js'

globalThis.localStorage = { getItem: () => 'test-token' }

function streamingResponse(parts) {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream({
      start(controller) {
        for (const part of parts)
          controller.enqueue(typeof part === 'string' ? encoder.encode(part) : part)
        controller.close()
      },
    }),
    { headers: { 'Content-Type': 'text/event-stream' } },
  )
}

test('streams split UTF-8 and SSE frames, preserves Markdown whitespace and passes conversation ID', async () => {
  const bytes = new TextEncoder().encode(
    'data: {"token":"你好"}\n\ndata: {"token":"\\n\\n"}\n\ndata: {"done":true}\n\n',
  )
  let payload
  globalThis.fetch = async (url, options) => {
    payload = options
    assert.equal(url, '/api/chat-robot/stream/')
    return streamingResponse([bytes.slice(0, 18), bytes.slice(18, 25), bytes.slice(25)])
  }
  let text = ''
  await streamChat('conversation-a', '问题', (token) => {
    text += token
  })
  assert.equal(text, '你好\n\n')
  assert.deepEqual(JSON.parse(payload.body), { conversation_id: 'conversation-a', message: '问题' })
  assert.equal(payload.headers.Authorization, 'Bearer test-token')
})

test('provider errors reject instead of leaving the composer busy', async () => {
  globalThis.fetch = async () => streamingResponse(['data: {"error":"回复失败"}\n\n'])
  await assert.rejects(
    streamChat('a', 'question', () => {}),
    /回复失败/,
  )
})

test('unexpected EOF is reported', async () => {
  globalThis.fetch = async () => streamingResponse(['data: {"token":"partial"}\n\n'])
  await assert.rejects(
    streamChat('a', 'question', () => {}),
    /连接已中断/,
  )
})

test('HTTP and network failures reject', async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: '权限不足' }), { status: 403 })
  await assert.rejects(
    streamChat('a', 'question', () => {}),
    /权限不足/,
  )
  globalThis.fetch = async () => {
    throw new Error('Network unavailable')
  }
  await assert.rejects(
    streamChat('a', 'question', () => {}),
    /Network unavailable/,
  )
})

test('abort signal is forwarded and rejects on cancellation', async () => {
  const controller = new AbortController()
  controller.abort()
  globalThis.fetch = async (url, options) => {
    assert.equal(options.signal, controller.signal)
    options.signal.throwIfAborted()
  }
  await assert.rejects(
    streamChat('a', 'question', () => {}, { signal: controller.signal }),
    { name: 'AbortError' },
  )
})

test('delete accepts an empty 204 response', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/chat-robot/conversations/a/')
    assert.equal(options.method, 'DELETE')
    return new Response(null, { status: 204 })
  }
  assert.equal(await deleteChatConversation('a'), null)
})
