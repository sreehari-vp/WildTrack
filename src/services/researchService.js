import { getApiJson } from "./apiClient";

export const researchService = {
  // Render's free API can cold start, and the sourced land-cover polygons are
  // substantially larger than ordinary API responses.
  getAreas: (landCover = false) => getApiJson(`/research/areas?land_cover=${landCover}`, { timeoutMs: 60000 }),
  getOccurrences: () => getApiJson("/research/occurrences?limit=500", { timeoutMs: 60000 })
};
