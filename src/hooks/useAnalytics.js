import { analyticsService } from "../services/analyticsService";
import { useAsyncData } from "./useAsyncData";
const useAnalytics = (filters = {}) => useAsyncData(
  () => analyticsService.getAnalytics(filters),
  [filters.start, filters.end, filters.species]
);
export {
  useAnalytics
};
