import { ApiError } from "./auth"
import type { components } from "./schema.generated"

export type ChatSummary = components["schemas"]["ChatSummaryView"]
export type ChatDetail = components["schemas"]["ChatDetailView"]
export type ChatTurn = components["schemas"]["ChatTurnView"]
export type ChatCitation = components["schemas"]["ChatCitationView"]

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as T
}

export async function listChats(signal?: AbortSignal): Promise<readonly ChatSummary[]> {
  return readJson<readonly ChatSummary[]>(await fetch("/api/v1/chats", { credentials: "same-origin", signal }))
}

export async function getChat(chatId: string, signal?: AbortSignal): Promise<ChatDetail> {
  return readJson<ChatDetail>(await fetch(`/api/v1/chats/${encodeURIComponent(chatId)}`, { credentials: "same-origin", signal }))
}

export async function createChat(csrfToken: string): Promise<ChatSummary> {
  return readJson<ChatSummary>(await fetch("/api/v1/chats", {
    method: "POST", credentials: "same-origin", headers: { "x-csrf-token": csrfToken },
  }))
}

export async function sendChatMessage(chatId: string, text: string, requestId: string, csrfToken: string, starterId?: string): Promise<ChatTurn> {
  return readJson<ChatTurn>(await fetch(`/api/v1/chats/${encodeURIComponent(chatId)}/messages`, {
    method: "POST", credentials: "same-origin",
    headers: { "content-type": "application/json", "x-csrf-token": csrfToken },
    body: JSON.stringify({ request_id: requestId, text, starter_id: starterId ?? null }),
  }))
}

export async function streamChatMessage(chatId: string, text: string, requestId: string, csrfToken: string, onDelta: (text: string) => void, starterId?: string): Promise<ChatTurn> {
  const response = await fetch(`/api/v1/chats/${encodeURIComponent(chatId)}/messages/stream`, {
    method: "POST", credentials: "same-origin",
    headers: { "content-type": "application/json", "accept": "text/event-stream", "x-csrf-token": csrfToken },
    body: JSON.stringify({ request_id: requestId, text, starter_id: starterId ?? null }),
  })
  if (!response.ok) throw new ApiError(response.status)
  if (!response.body || !response.headers.get("content-type")?.startsWith("text/event-stream")) throw new Error("Invalid response stream")

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ""
  let eventName = ""
  let dataLines: string[] = []
  let complete: ChatTurn | undefined

  function dispatch() {
    if (dataLines.length === 0) { eventName = ""; return }
    const payload = JSON.parse(dataLines.join("\n")) as Record<string, unknown>
    if (eventName === "delta") {
      if (typeof payload.text !== "string") throw new Error("Invalid response delta")
      onDelta(payload.text)
    } else if (eventName === "complete") {
      if (!payload.turn || typeof payload.turn !== "object") throw new Error("Invalid completed response")
      complete = payload.turn as ChatTurn
    } else if (eventName === "error") {
      throw new Error(typeof payload.message === "string" ? payload.message : "Response generation failed")
    }
    eventName = ""
    dataLines = []
  }

  try {
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let end = buffer.indexOf("\n")
      while (end !== -1) {
        const line = buffer.slice(0, end).replace(/\r$/, "")
        buffer = buffer.slice(end + 1)
        if (!line) dispatch()
        else if (!line.startsWith(":")) {
          const separator = line.indexOf(":")
          const field = separator === -1 ? line : line.slice(0, separator)
          const rawValue = separator === -1 ? "" : line.slice(separator + 1)
          const fieldValue = rawValue.startsWith(" ") ? rawValue.slice(1) : rawValue
          if (field === "event") eventName = fieldValue
          if (field === "data") dataLines.push(fieldValue)
        }
        end = buffer.indexOf("\n")
      }
    }
  } catch (error) {
    await reader.cancel().catch(() => undefined)
    throw error
  } finally {
    reader.releaseLock()
  }
  if (!complete) throw new Error("Response stream ended before completion")
  return complete
}

export async function deleteChat(chatId: string, csrfToken: string): Promise<void> {
  const response = await fetch(`/api/v1/chats/${encodeURIComponent(chatId)}`, {
    method: "DELETE", credentials: "same-origin", headers: { "x-csrf-token": csrfToken },
  })
  if (!response.ok) throw new ApiError(response.status)
}

export async function renameChat(chatId: string, title: string, csrfToken: string): Promise<ChatSummary> {
  return readJson<ChatSummary>(await fetch(`/api/v1/chats/${encodeURIComponent(chatId)}`, {
    method: "PATCH", credentials: "same-origin",
    headers: { "content-type": "application/json", "x-csrf-token": csrfToken },
    body: JSON.stringify({ title }),
  }))
}

export async function rateChatMessage(chatId: string, requestId: string, rating: "up" | "down" | null, comment: string | null, csrfToken: string): Promise<ChatTurn> {
  return readJson<ChatTurn>(await fetch(`/api/v1/chats/${encodeURIComponent(chatId)}/messages/${encodeURIComponent(requestId)}/feedback`, {
    method: "PUT", credentials: "same-origin",
    headers: { "content-type": "application/json", "x-csrf-token": csrfToken },
    body: JSON.stringify({ rating, comment }),
  }))
}
