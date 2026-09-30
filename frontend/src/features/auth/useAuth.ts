import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { getSession, login, logout } from "../../api/auth"
import type { AuthSession } from "../../api/auth"

export const authQueryKey = ["auth", "me"] as const

export function useAuth() {
  const queryClient = useQueryClient()
  const session = useQuery<AuthSession | null>({
    queryKey: authQueryKey,
    queryFn: ({ signal }) => getSession(signal),
    retry: false,
    staleTime: 60_000,
  })
  const signIn = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) => login(username, password),
    onSuccess: (value) => queryClient.setQueryData<AuthSession | null>(authQueryKey, value),
  })
  const signOut = useMutation({
    mutationFn: (csrfToken: string) => logout(csrfToken),
    onSuccess: () => { queryClient.removeQueries({ queryKey: ["materials"] }); queryClient.removeQueries({ queryKey: ["admin"] }); queryClient.removeQueries({ queryKey: ["chats"] }); queryClient.setQueryData(authQueryKey, null) },
  })
  return { session, signIn, signOut }
}
