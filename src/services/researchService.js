import { getApiJson } from "./apiClient";

export const researchService = {
  getAreas: (landCover = false) => getApiJson(`/research/areas?land_cover=${landCover}`, { timeoutMs: landCover ? 30000 : 15000 }),
  getOccurrences: () => getApiJson("/research/occurrences?limit=500", { timeoutMs: 30000 })
};
