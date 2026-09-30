import { ApiError } from "./auth"
import type { components } from "./schema.generated"

export type MaterialSummary = components["schemas"]["MaterialView"]
export type MaterialDetail = components["schemas"]["MaterialDetail"]
export type MaterialFilters = {
  q?: string
  region?: string
  people?: string
  period?: string
  media_type?: "application/pdf" | "text/csv"
}

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as T
}

export async function getMaterials(filters: MaterialFilters = {}, signal?: AbortSignal): Promise<readonly MaterialSummary[]> {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) if (value) params.set(key, value)
  const suffix = params.size ? `?${params.toString()}` : ""
  const response = await fetch(`/api/v1/materials${suffix}`, { credentials: "same-origin", signal })
  return readJson<readonly MaterialSummary[]>(response)
}

export async function getMaterial(revisionId: string, signal?: AbortSignal): Promise<MaterialDetail> {
  const response = await fetch(`/api/v1/materials/${encodeURIComponent(revisionId)}`, { credentials: "same-origin", signal })
  return readJson<MaterialDetail>(response)
}

export function approvedPageUrl(revisionId: string, page: number, originalAvailable: boolean): string | null {
  if (!originalAvailable || !revisionId || !Number.isSafeInteger(page) || page < 1) return null
  return `/api/v1/materials/${encodeURIComponent(revisionId)}/original#page=${page}`
}
