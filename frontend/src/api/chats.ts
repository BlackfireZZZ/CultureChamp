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

export async function deleteChat(chatId: string, csrfToken: string): Promise<void> {
  const response = await fetch(`/api/v1/chats/${encodeURIComponent(chatId)}`, {
    method: "DELETE", credentials: "same-origin", headers: { "x-csrf-token": csrfToken },
  })
  if (!response.ok) throw new ApiError(response.status)
}
