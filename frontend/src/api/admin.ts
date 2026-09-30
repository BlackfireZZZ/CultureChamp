import { ApiError } from "./auth"
import type { components, operations } from "./schema.generated"

export type AdminSource = components["schemas"]["AdminSourceView"]
export type AdminRevision = components["schemas"]["AdminRevisionView"]
export type MetadataInput = components["schemas"]["MetadataInput"]
export type MetadataEvent = components["schemas"]["MetadataEventView"]
export type AdminFilters = NonNullable<operations["admin_sources_api_v1_admin_sources_get"]["parameters"]["query"]>

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as T
}

export async function getAdminSources(filters: AdminFilters, signal?: AbortSignal): Promise<readonly AdminSource[]> {
  const params = new URLSearchParams()
  if (filters.status) params.set("status", filters.status)
  if (filters.decision) params.set("decision", filters.decision)
  if (filters.q) params.set("q", filters.q)
  if (filters.media_type) params.set("media_type", filters.media_type)
  if (filters.tag_kind) params.set("tag_kind", filters.tag_kind)
  if (filters.tag_value) params.set("tag_value", filters.tag_value)
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

export async function getAdminMetadataHistory(revisionId: string, signal?: AbortSignal): Promise<readonly MetadataEvent[]> {
  const response = await fetch(`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}/metadata-history`, { credentials: "same-origin", signal })
  return readJson(response)
}

export async function amendAdminMetadata(revisionId: string, data: MetadataInput, csrfToken: string): Promise<AdminRevision> {
  return readJson(await fetch(`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}/metadata`, {
    method: "PATCH", credentials: "same-origin",
    headers: { "content-type": "application/json", "x-csrf-token": csrfToken },
    body: JSON.stringify(data),
  }))
}

export async function uploadAdminSource(form: FormData, csrfToken: string): Promise<components["schemas"]["IntakeView"]> {
  return readJson(await fetch("/api/v1/admin/sources", {
    method: "POST", credentials: "same-origin", headers: { "x-csrf-token": csrfToken }, body: form,
  }))
}

export async function approveAdminRevision(revisionId: string, data: components["schemas"]["DecisionInput"], csrfToken: string): Promise<AdminRevision> {
  return readJson(await fetch(`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}/approve`, {
    method: "POST", credentials: "same-origin",
    headers: { "content-type": "application/json", "x-csrf-token": csrfToken },
    body: JSON.stringify(data),
  }))
}

export async function revokeAdminRevision(revisionId: string, reason: string, csrfToken: string): Promise<AdminRevision> {
  return readJson(await fetch(`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}/revoke`, {
    method: "POST", credentials: "same-origin",
    headers: { "content-type": "application/json", "x-csrf-token": csrfToken },
    body: JSON.stringify({ reason }),
  }))
}

export async function retryAdminRevision(revisionId: string, csrfToken: string): Promise<AdminRevision> {
  return readJson(await fetch(`/api/v1/admin/revisions/${encodeURIComponent(revisionId)}/retry`, {
    method: "POST", credentials: "same-origin", headers: { "x-csrf-token": csrfToken },
  }))
}
