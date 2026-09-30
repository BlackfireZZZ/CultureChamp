import { useQuery } from "@tanstack/react-query"

import { getMaterial, getMaterials } from "../../api/materials"

export function useMaterials() {
  return useQuery({ queryKey: ["materials", "approved"], queryFn: ({ signal }) => getMaterials(signal), retry: false })
}

export function useMaterial(revisionId: string | null) {
  return useQuery({
    queryKey: ["materials", "revision", revisionId],
    queryFn: ({ signal }) => getMaterial(revisionId!, signal),
    enabled: revisionId !== null,
    retry: false,
  })
}
