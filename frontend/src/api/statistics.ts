import { ApiError } from "./auth"

export type RequestStatisticsResponse = {
  period_start: string
  period_end: string
  daily_requests: readonly { date: string; count: number }[]
  starter_requests: readonly { starter_id: string; count: number }[]
}

export async function getRequestStatistics(signal?: AbortSignal): Promise<RequestStatisticsResponse> {
  const response = await fetch("/api/v1/admin/request-statistics?days=30", { credentials: "same-origin", signal })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as RequestStatisticsResponse
}
