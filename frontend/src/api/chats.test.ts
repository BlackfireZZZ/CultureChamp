import { afterEach, expect, test, vi } from "vitest"

import { streamChatMessage } from "./chats"

afterEach(() => vi.unstubAllGlobals())

function streamedResponse(chunks: Uint8Array[], status = 200) {
  let index = 0
  return {
    ok: status === 200,
    status,
    headers: new Headers({ "content-type": "text/event-stream; charset=utf-8" }),
    body: { getReader: () => ({
      read: () => Promise.resolve(index < chunks.length ? { done: false, value: chunks[index++] } : { done: true, value: undefined }),
      cancel: () => Promise.resolve(),
      releaseLock: () => {},
    }) },
  } as unknown as Response
}

test("decodes fragmented Cyrillic SSE deltas and returns the final turn", async () => {
  const turn = { request_id: "r1", assistant_text: "Ответ", status: "complete", citations: [{ segment_id: "s1" }] }
  const bytes = new TextEncoder().encode(`: keepalive\n\nevent: delta\r\ndata: {"text":"От"}\r\n\r\nevent: delta\ndata: {"text":"вет"}\n\nevent: complete\ndata: {"turn":${JSON.stringify(turn)}}\n\n`)
  const fetchMock = vi.fn().mockResolvedValue(streamedResponse([bytes.slice(0, 34), bytes.slice(34, 38), bytes.slice(38, 66), bytes.slice(66)]))
  vi.stubGlobal("fetch", fetchMock)
  const deltas: string[] = []
  const result = await streamChatMessage("chat-1", "Вопрос", "r1", "csrf", (delta) => deltas.push(delta))
  expect(deltas).toEqual(["От", "вет"])
  expect(result).toEqual(turn)
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/chats/chat-1/messages/stream", expect.objectContaining({ method: "POST", body: JSON.stringify({ request_id: "r1", text: "Вопрос", starter_id: null }) }))
})

test("rejects a broken stream instead of treating provisional text as a saved answer", async () => {
  const bytes = new TextEncoder().encode('event: delta\ndata: {"text":"Начало"}\n\n')
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamedResponse([bytes])))
  await expect(streamChatMessage("chat-1", "Вопрос", "r1", "csrf", vi.fn())).rejects.toThrow("before completion")
})

test("surfaces a server generation error", async () => {
  const bytes = new TextEncoder().encode('event: error\ndata: {"message":"Generation unavailable"}\n\n')
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(streamedResponse([bytes])))
  await expect(streamChatMessage("chat-1", "Вопрос", "r1", "csrf", vi.fn())).rejects.toThrow("Generation unavailable")
})
