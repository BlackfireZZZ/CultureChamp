import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { createChat, deleteChat, getChat, listChats, sendChatMessage } from "../../api/chats"

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
  const remove = useMutation({ mutationFn: (chatId: string) => deleteChat(chatId, csrfToken), onSuccess: async () => refresh() })
  return { create, send, remove }
}
