import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { createChat, deleteChat, getChat, listChats, rateChatMessage, renameChat, sendChatMessage, streamChatMessage } from "../../api/chats"

export function useChats(enabled: boolean) {
  return useQuery({ queryKey: ["chats"], queryFn: ({ signal }) => listChats(signal), enabled, retry: false })
}

export function useChat(chatId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: ["chats", chatId],
    queryFn: ({ signal }) => getChat(chatId!, signal),
    enabled: enabled && chatId !== null,
    retry: false,
  })
}

export function useChatActions(csrfToken: string) {
  const client = useQueryClient()
  const refresh = async (chatId?: string) => {
    await client.invalidateQueries({ queryKey: ["chats"] })
    if (chatId) await client.invalidateQueries({ queryKey: ["chats", chatId] })
  }
  const create = useMutation({ mutationFn: () => createChat(csrfToken), onSuccess: async () => refresh() })
  const send = useMutation({
    mutationFn: ({ chatId, text, requestId, starterId }: { chatId: string; text: string; requestId: string; starterId?: string }) => sendChatMessage(chatId, text, requestId, csrfToken, starterId),
    onSuccess: async (_turn, variables) => refresh(variables.chatId),
  })
  const stream = useMutation({
    mutationFn: ({ chatId, text, requestId, starterId, onDelta }: { chatId: string; text: string; requestId: string; starterId?: string; onDelta: (text: string) => void }) => streamChatMessage(chatId, text, requestId, csrfToken, onDelta, starterId),
    onSuccess: async (_turn, variables) => refresh(variables.chatId),
  })
  const remove = useMutation({ mutationFn: (chatId: string) => deleteChat(chatId, csrfToken), onSuccess: async () => refresh() })
  const rename = useMutation({
    mutationFn: ({ chatId, title }: { chatId: string; title: string }) => renameChat(chatId, title, csrfToken),
    onSuccess: async (_summary, variables) => refresh(variables.chatId),
  })
  const rate = useMutation({
    mutationFn: ({ chatId, requestId, rating, comment }: { chatId: string; requestId: string; rating: "up" | "down" | null; comment: string | null }) => rateChatMessage(chatId, requestId, rating, comment, csrfToken),
    onSuccess: async (_turn, variables) => refresh(variables.chatId),
  })
  return { create, send, stream, remove, rename, rate }
}
