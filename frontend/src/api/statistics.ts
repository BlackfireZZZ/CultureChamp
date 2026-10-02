import { ApiError } from "./auth"

export type RequestStatisticsResponse = {
  period_start: string
  period_end: string
  daily_requests: readonly { date: string; count: number }[]
  starter_requests: readonly { starter_id: string; count: number }[]
  rated_up: number
  rated_down: number
  feedback: readonly { request_id: string; rated_at: string; rating: "up" | "down"; comment: string | null; evidence_status: string | null; starter_id: string | null }[]
}

export async function getRequestStatistics(days: number, signal?: AbortSignal): Promise<RequestStatisticsResponse> {
  const response = await fetch(`/api/v1/admin/request-statistics?days=${days}`, { credentials: "same-origin", signal })
  if (!response.ok) throw new ApiError(response.status)
  return (await response.json()) as RequestStatisticsResponse
}
