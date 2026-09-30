import { useQuery } from "@tanstack/react-query"

import { getMaterial, getMaterials } from "../../api/materials"
import type { MaterialFilters } from "../../api/materials"

export function useMaterials(filters: MaterialFilters = {}) {
  return useQuery({ queryKey: ["materials", "approved", filters], queryFn: ({ signal }) => getMaterials(filters, signal), retry: false })
}

export function useMaterial(revisionId: string | null) {
  return useQuery({
    queryKey: ["materials", "revision", revisionId],
    queryFn: ({ signal }) => getMaterial(revisionId!, signal),
    enabled: revisionId !== null,
    retry: false,
  })
}
