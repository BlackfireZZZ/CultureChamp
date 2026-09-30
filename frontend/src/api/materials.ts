import { ApiError } from "./auth"
import type { components } from "./schema.generated"

export type MaterialSummary = components["schemas"]["MaterialView"]
export type MaterialDetail = components["schemas"]["MaterialDetail"]

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as T
}

export async function getMaterials(signal?: AbortSignal): Promise<readonly MaterialSummary[]> {
  const response = await fetch("/api/v1/materials", { credentials: "same-origin", signal })
  return readJson<readonly MaterialSummary[]>(response)
}

export async function getMaterial(revisionId: string, signal?: AbortSignal): Promise<MaterialDetail> {
  const response = await fetch(`/api/v1/materials/${encodeURIComponent(revisionId)}`, { credentials: "same-origin", signal })
  return readJson<MaterialDetail>(response)
}

export function pageUrl(originUrl: string | null, page: number): string | null {
  if (!originUrl || !Number.isSafeInteger(page) || page < 1) return null
  try {
    const url = new URL(originUrl)
    if (url.protocol !== "https:" && url.protocol !== "http:") return null
    url.hash = `page=${page}`
    return url.toString()
  } catch { return null }
}
