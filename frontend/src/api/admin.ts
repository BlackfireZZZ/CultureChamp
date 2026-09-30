import { ApiError } from "./auth"
import type { components, operations } from "./schema.generated"

export type AdminSource = components["schemas"]["AdminSourceView"]
export type AdminRevision = components["schemas"]["AdminRevisionView"]
export type AdminFilters = NonNullable<operations["admin_sources_api_v1_admin_sources_get"]["parameters"]["query"]>

export async function getAdminSources(filters: AdminFilters, signal?: AbortSignal): Promise<readonly AdminSource[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set("status", filters.status)
  if (filters.decision) params.set("decision", filters.decision)
  if (filters.limit) params.set("limit", String(filters.limit))
  const suffix = params.size ? `?${params.toString()}` : ""
  const response = await fetch(`/api/v1/admin/sources${suffix}`, { credentials: "same-origin", signal })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as readonly AdminSource[]
}

export async function getAdminRevision(revisionId: string, signal?: AbortSignal): Promise<AdminRevision> {
  const response = await fetch(`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}`, { credentials: "same-origin", signal })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as AdminRevision
}
