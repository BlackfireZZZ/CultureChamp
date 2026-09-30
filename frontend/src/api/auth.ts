import type { components } from "./schema.generated"

export type AuthUser = components["schemas"]["AccountView"]
export type AuthSession = components["schemas"]["AuthView"]

export class ApiError extends Error {
  constructor(readonly status: number) {
    super(`API request failed (${status})`)
  }
}

async function readAuth(response: Response): Promise<AuthSession> {
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as AuthSession
}

export async function getSession(signal?: AbortSignal): Promise<AuthSession> {
  const response = await fetch("/api/v1/auth/me", { credentials: "same-origin", signal })
  return readAuth(response)
}

export async function login(username: string, password: string): Promise<AuthSession> {
  const response = await fetch("/api/v1/auth/login", {
    method: "POST",
    credentials: "same-origin",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  return readAuth(response)
}

export async function logout(csrfToken: string): Promise<void> {
  const response = await fetch("/api/v1/auth/logout", {
    method: "POST",
    credentials: "same-origin",
    headers: { "x-csrf-token": csrfToken },
  })
  if (!response.ok) throw new ApiError(response.status)
}
