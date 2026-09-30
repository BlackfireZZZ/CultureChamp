import { ApiError } from "./auth"
import type { components } from "./schema.generated"

export type AdminSource = components["schemas"]["AdminSourceView"]
export type AdminRevision = components["schemas"]["AdminRevisionView"]

export async function getAdminSources(signal?: AbortSignal): Promise<readonly AdminSource[]> {
  const response = await fetch("/api/v1/admin/sources", { credentials: "same-origin", signal })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as readonly AdminSource[]
}

export async function getAdminRevision(revisionId: string, signal?: AbortSignal): Promise<AdminRevision> {
  const response = await fetch(`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}`, { credentials: "same-origin", signal })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as AdminRevision
}
