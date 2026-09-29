export type HealthResponse = { status: "alive" }

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/v1/health/live", { signal })
  if (!response.ok) throw new Error("API is unavailable")
  return (await response.json()) as HealthResponse
}
