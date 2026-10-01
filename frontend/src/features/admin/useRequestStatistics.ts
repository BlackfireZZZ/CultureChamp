import { useQuery } from "@tanstack/react-query"

import { getRequestStatistics } from "../../api/statistics"

export function useRequestStatistics(enabled: boolean) {
  return useQuery({ queryKey: ["admin", "request-statistics", 30], queryFn: ({ signal }) => getRequestStatistics(signal), enabled, retry: false })
}
