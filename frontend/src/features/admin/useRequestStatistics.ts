import { useQuery } from "@tanstack/react-query"

import { getRequestStatistics } from "../../api/statistics"

export function useRequestStatistics(enabled: boolean, days: number) {
  return useQuery({ queryKey: ["admin", "request-statistics", days], queryFn: ({ signal }) => getRequestStatistics(days, signal), enabled, retry: false })
}
